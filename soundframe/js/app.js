/* ============================================
   SOUNDFRAME — app logic
   ============================================ */

(() => {
  'use strict';

  // ---------- State ----------
  let tracks = [];           // {id, name, artist, duration, addedAt, blob(loaded lazily), objectUrl}
  let playlists = [];        // {id, name, trackIds: []}
  let queue = [];            // array of track ids, current playback order
  let queueIndex = -1;
  let currentPlaylistView = null;
  let shuffleOn = false;
  let repeatMode = 0;        // 0 off, 1 all, 2 one
  let audioCtx = null, analyser = null, sourceNode = null;
  let rafId = null;
  let isSeeking = false;

  // ---------- DOM ----------
  const $ = (id) => document.getElementById(id);
  const audioEl = $('audioEl');
  const fileInput = $('fileInput');

  const els = {
    navBtns: document.querySelectorAll('.navbtn'),
    views: document.querySelectorAll('.view'),
    trackTitle: $('trackTitle'),
    trackArtist: $('trackArtist'),
    metaIndex: $('metaIndex'),
    playBtn: $('playBtn'),
    playIcon: $('playIcon'),
    pauseIcon: $('pauseIcon'),
    prevBtn: $('prevBtn'),
    nextBtn: $('nextBtn'),
    shuffleBtn: $('shuffleBtn'),
    repeatBtn: $('repeatBtn'),
    scrubTrack: $('scrubTrack'),
    scrubFill: $('scrubFill'),
    scrubHandle: $('scrubHandle'),
    timeCurrent: $('timeCurrent'),
    timeTotal: $('timeTotal'),
    volumeSlider: $('volumeSlider'),
    formatTag: $('formatTag'),
    visualizer: $('visualizer'),
    visualizerEmpty: $('visualizerEmpty'),
    libraryEmpty: $('libraryEmpty'),
    trackTable: $('trackTable'),
    trackTableBody: $('trackTableBody'),
    libraryCount: $('libraryCount'),
    playlistGrid: $('playlistGrid'),
    playlistsEmpty: $('playlistsEmpty'),
    playlistDetail: $('playlistDetail'),
    playlistDetailName: $('playlistDetailName'),
    playlistDetailCount: $('playlistDetailCount'),
    playlistTrackTableBody: $('playlistTrackTableBody'),
    queueDrawer: $('queueDrawer'),
    queueList: $('queueList'),
    toast: $('toast'),
    lyricsBody: $('lyricsBody'),
    lyricsInput: $('lyricsInput'),
    lyricsActions: $('lyricsActions'),
    lyricsTrackName: $('lyricsTrackName'),
  };

  const canvasCtx = els.visualizer.getContext('2d');

  // ---------- Utils ----------
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }

  function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function showToast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add('show');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => els.toast.classList.remove('show'), 2200);
  }

  function parseFilename(name) {
    let base = name.replace(/\.[^/.]+$/, '');
    let artist = 'Unknown Artist';
    let title = base;
    const parts = base.split(' - ');
    if (parts.length >= 2) {
      artist = parts[0].trim();
      title = parts.slice(1).join(' - ').trim();
    }
    return { title, artist };
  }

  function getExt(name) {
    const m = name.match(/\.([^.]+)$/);
    return m ? m[1].toUpperCase() : '—';
  }

  // ---------- View routing ----------
  function setView(view) {
    els.navBtns.forEach(b => b.classList.toggle('active', b.dataset.view === view));
    els.views.forEach(v => v.classList.toggle('active', v.id === `view-${view}`));
    if (view === 'lyrics') renderLyricsView();
  }
  els.navBtns.forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));

  // ---------- Library load / persistence ----------
  async function loadLibrary() {
    const stored = await dbGetAll('tracks');
    stored.sort((a, b) => a.addedAt - b.addedAt);
    tracks = stored.map(t => ({ ...t, objectUrl: null }));
    playlists = await dbGetAll('playlists');
    renderLibrary();
    renderPlaylists();
    if (tracks.length && queue.length === 0) {
      queue = tracks.map(t => t.id);
    }
    renderQueue();
  }

  async function addFiles(fileList) {
    const files = Array.from(fileList).filter(f => f.type.startsWith('audio/') || /\.(mp3|wav|ogg|flac|m4a|aac)$/i.test(f.name));
    if (!files.length) { showToast('No audio files found'); return; }

    let added = 0;
    for (const file of files) {
      const { title, artist } = parseFilename(file.name);
      const id = uid();
      const duration = await probeDuration(file).catch(() => 0);
      const record = {
        id, name: file.name, title, artist,
        duration, addedAt: Date.now(),
        ext: getExt(file.name),
        blob: file,
      };
      await dbAdd('tracks', record);
      tracks.push({ ...record, objectUrl: null });
      queue.push(id);
      added++;
    }
    renderLibrary();
    renderQueue();
    showToast(`${added} track${added !== 1 ? 's' : ''} added`);

    if (!audioEl.src && tracks.length) {
      loadTrack(tracks[tracks.length - added].id, false);
    }
  }

  function probeDuration(file) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(file);
      const a = new Audio();
      a.preload = 'metadata';
      a.src = url;
      a.onloadedmetadata = () => { resolve(a.duration); URL.revokeObjectURL(url); };
      a.onerror = () => { resolve(0); URL.revokeObjectURL(url); };
    });
  }

  // ---------- Rendering: Library table ----------
  function renderLibrary() {
    els.libraryCount.textContent = `${tracks.length} TRACK${tracks.length !== 1 ? 'S' : ''}`;
    if (!tracks.length) {
      els.libraryEmpty.style.display = 'flex';
      els.trackTable.style.display = 'none';
      return;
    }
    els.libraryEmpty.style.display = 'none';
    els.trackTable.style.display = 'table';
    els.trackTableBody.innerHTML = tracks.map((t, i) => rowHtml(t, i + 1)).join('');
    attachRowHandlers(els.trackTableBody, tracks);
  }

  function rowHtml(t, idx) {
    const playing = currentTrack() && currentTrack().id === t.id;
    return `<tr data-id="${t.id}" class="${playing ? 'playing' : ''}">
      <td class="t-idx">${idx}</td>
      <td class="t-title">${escapeHtml(t.title)}</td>
      <td class="t-artist">${escapeHtml(t.artist)}</td>
      <td class="t-dur">${fmtTime(t.duration)}</td>
      <td><button class="t-add-btn" data-add="${t.id}" title="Add to playlist">
        <svg viewBox="0 0 24 24" fill="none"><path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      </button></td>
    </tr>`;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function attachRowHandlers(tbody, list) {
    tbody.querySelectorAll('tr').forEach(row => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('.t-add-btn')) return;
        const id = row.dataset.id;
        queue = list.map(t => t.id);
        loadTrack(id, true);
      });
    });
    tbody.querySelectorAll('.t-add-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openAddToPlaylistMenu(btn.dataset.add, btn);
      });
    });
  }

  // simple add-to-playlist via prompt-free menu: cycle a tiny inline chooser
  function openAddToPlaylistMenu(trackId, anchorBtn) {
    if (!playlists.length) {
      showToast('Create a playlist first');
      setView('playlists');
      return;
    }
    const names = playlists.map((p, i) => `${i + 1}. ${p.name}`).join('\n');
    const choice = prompt(`Add to playlist:\n${names}\n\nEnter number:`);
    const idx = parseInt(choice, 10) - 1;
    if (playlists[idx]) {
      addTrackToPlaylist(playlists[idx].id, trackId);
    }
  }

  // ---------- Playlists ----------
  function renderPlaylists() {
    if (!playlists.length) {
      els.playlistsEmpty.style.display = 'flex';
      els.playlistGrid.style.display = 'none';
    } else {
      els.playlistsEmpty.style.display = 'none';
      els.playlistGrid.style.display = 'grid';
      els.playlistGrid.innerHTML = playlists.map(p => `
        <div class="playlist-card" data-id="${p.id}">
          <div class="playlist-card-name">${escapeHtml(p.name)}</div>
          <div class="playlist-card-count">${p.trackIds.length} TRACK${p.trackIds.length !== 1 ? 'S' : ''}</div>
        </div>`).join('');
      els.playlistGrid.querySelectorAll('.playlist-card').forEach(card => {
        card.addEventListener('click', () => openPlaylistDetail(card.dataset.id));
      });
    }
  }

  function openPlaylistDetail(id) {
    const pl = playlists.find(p => p.id === id);
    if (!pl) return;
    currentPlaylistView = id;
    els.playlistGrid.style.display = 'none';
    els.playlistsEmpty.style.display = 'none';
    els.playlistDetail.style.display = 'block';
    els.playlistDetailName.textContent = pl.name;
    const plTracks = pl.trackIds.map(tid => tracks.find(t => t.id === tid)).filter(Boolean);
    els.playlistDetailCount.textContent = `${plTracks.length} TRACK${plTracks.length !== 1 ? 'S' : ''}`;
    els.playlistTrackTableBody.innerHTML = plTracks.map((t, i) => rowHtml(t, i + 1)).join('');
    attachRowHandlers(els.playlistTrackTableBody, plTracks);
  }

  $('playlistBackBtn').addEventListener('click', () => {
    currentPlaylistView = null;
    els.playlistDetail.style.display = 'none';
    renderPlaylists();
  });

  async function addTrackToPlaylist(playlistId, trackId) {
    const pl = playlists.find(p => p.id === playlistId);
    if (!pl) return;
    if (!pl.trackIds.includes(trackId)) {
      pl.trackIds.push(trackId);
      await dbAdd('playlists', pl);
      showToast(`Added to "${pl.name}"`);
      renderPlaylists();
    } else {
      showToast('Already in playlist');
    }
  }

  async function createPlaylist(name) {
    const pl = { id: uid(), name: name.trim(), trackIds: [] };
    await dbAdd('playlists', pl);
    playlists.push(pl);
    renderPlaylists();
  }

  // Modal wiring
  const plModal = $('playlistModalBackdrop');
  const plNameInput = $('playlistNameInput');
  function openPlaylistModal() {
    plModal.style.display = 'flex';
    plNameInput.value = '';
    setTimeout(() => plNameInput.focus(), 50);
  }
  function closePlaylistModal() { plModal.style.display = 'none'; }
  $('newPlaylistBtn').addEventListener('click', openPlaylistModal);
  $('emptyNewPlaylistBtn').addEventListener('click', openPlaylistModal);
  $('playlistModalCancel').addEventListener('click', closePlaylistModal);
  $('playlistModalBackdrop').addEventListener('click', (e) => { if (e.target === plModal) closePlaylistModal(); });
  $('playlistModalCreate').addEventListener('click', async () => {
    if (!plNameInput.value.trim()) { plNameInput.focus(); return; }
    await createPlaylist(plNameInput.value);
    closePlaylistModal();
  });
  plNameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') $('playlistModalCreate').click(); });

  // ---------- Queue drawer ----------
  function renderQueue() {
    if (!queue.length) {
      els.queueList.innerHTML = `<div class="empty-state" style="padding:40px 10px;"><p>Queue is empty</p></div>`;
      return;
    }
    els.queueList.innerHTML = queue.map((id, i) => {
      const t = tracks.find(tt => tt.id === id);
      if (!t) return '';
      const playing = i === queueIndex;
      return `<div class="queue-item ${playing ? 'playing' : ''}" data-idx="${i}">
        <span class="q-num">${i + 1}</span>
        <div class="q-meta">
          <div class="q-title">${escapeHtml(t.title)}</div>
          <div class="q-artist">${escapeHtml(t.artist)}</div>
        </div>
        <span class="t-dur" style="font-size:11px">${fmtTime(t.duration)}</span>
      </div>`;
    }).join('');
    els.queueList.querySelectorAll('.queue-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.idx, 10);
        queueIndex = idx;
        playQueueIndex(idx);
      });
    });
  }

  $('queueToggleBtn').addEventListener('click', () => els.queueDrawer.classList.toggle('open'));
  $('closeQueueBtn').addEventListener('click', () => els.queueDrawer.classList.remove('open'));

  // ---------- Playback core ----------
  function currentTrack() {
    if (queueIndex < 0 || queueIndex >= queue.length) return null;
    return tracks.find(t => t.id === queue[queueIndex]);
  }

  function loadTrack(id, autoplay) {
    const idx = queue.indexOf(id);
    queueIndex = idx >= 0 ? idx : 0;
    const t = tracks.find(tt => tt.id === id);
    if (!t) return;

    if (t.objectUrl) URL.revokeObjectURL(t.objectUrl);
    const url = URL.createObjectURL(t.blob);
    t.objectUrl = url;
    audioEl.src = url;
    audioEl.volume = els.volumeSlider.value / 100;

    els.trackTitle.textContent = t.title;
    els.trackArtist.textContent = t.artist;
    els.metaIndex.textContent = `${queueIndex + 1} / ${queue.length}`;
    els.formatTag.textContent = t.ext || '—';
    document.title = `${t.title} — Soundframe`;

    if (autoplay) audioEl.play().catch(() => {});
    updatePlayIcon();
    renderLibrary();
    renderQueue();
    if (document.getElementById('view-lyrics').classList.contains('active')) renderLyricsView();
    ensureAudioGraph();
  }

  function playQueueIndex(idx) {
    if (idx < 0 || idx >= queue.length) return;
    loadTrack(queue[idx], true);
  }

  function togglePlay() {
    if (!audioEl.src) {
      if (tracks.length) { queue = tracks.map(t => t.id); loadTrack(tracks[0].id, true); }
      return;
    }
    if (audioEl.paused) { audioEl.play(); } else { audioEl.pause(); }
  }

  function updatePlayIcon() {
    const playing = !audioEl.paused && audioEl.src;
    els.playIcon.style.display = playing ? 'none' : 'block';
    els.pauseIcon.style.display = playing ? 'block' : 'none';
    els.playBtn.title = playing ? 'Pause' : 'Play';
  }

  function nextTrack(userInitiated = true) {
    if (!queue.length) return;
    if (shuffleOn) {
      let next;
      if (queue.length === 1) next = 0;
      else { do { next = Math.floor(Math.random() * queue.length); } while (next === queueIndex); }
      queueIndex = next;
    } else {
      queueIndex++;
      if (queueIndex >= queue.length) {
        if (repeatMode === 1) queueIndex = 0;
        else { queueIndex = queue.length - 1; if (userInitiated) return; audioEl.pause(); updatePlayIcon(); return; }
      }
    }
    loadTrack(queue[queueIndex], true);
  }

  function prevTrack() {
    if (!queue.length) return;
    if (audioEl.currentTime > 3) { audioEl.currentTime = 0; return; }
    queueIndex = queueIndex <= 0 ? (repeatMode === 1 ? queue.length - 1 : 0) : queueIndex - 1;
    loadTrack(queue[queueIndex], true);
  }

  els.playBtn.addEventListener('click', togglePlay);
  els.nextBtn.addEventListener('click', () => nextTrack(true));
  els.prevBtn.addEventListener('click', prevTrack);

  els.shuffleBtn.addEventListener('click', () => {
    shuffleOn = !shuffleOn;
    els.shuffleBtn.classList.toggle('on', shuffleOn);
    showToast(shuffleOn ? 'Shuffle on' : 'Shuffle off');
  });

  els.repeatBtn.addEventListener('click', () => {
    repeatMode = (repeatMode + 1) % 3;
    els.repeatBtn.classList.toggle('on', repeatMode !== 0);
    audioEl.loop = repeatMode === 2;
    showToast(['Repeat off', 'Repeat all', 'Repeat one'][repeatMode]);
  });

  audioEl.addEventListener('play', updatePlayIcon);
  audioEl.addEventListener('pause', updatePlayIcon);
  audioEl.addEventListener('ended', () => {
    if (repeatMode === 2) return; // handled by loop
    nextTrack(false);
  });

  audioEl.addEventListener('loadedmetadata', () => {
    els.timeTotal.textContent = fmtTime(audioEl.duration);
  });

  audioEl.addEventListener('timeupdate', () => {
    if (isSeeking) return;
    const pct = audioEl.duration ? (audioEl.currentTime / audioEl.duration) * 100 : 0;
    els.scrubFill.style.width = pct + '%';
    els.scrubHandle.style.left = pct + '%';
    els.timeCurrent.textContent = fmtTime(audioEl.currentTime);
  });

  // ---------- Scrubbing ----------
  function seekFromEvent(clientX) {
    const rect = els.scrubTrack.getBoundingClientRect();
    let pct = (clientX - rect.left) / rect.width;
    pct = Math.max(0, Math.min(1, pct));
    els.scrubFill.style.width = (pct * 100) + '%';
    els.scrubHandle.style.left = (pct * 100) + '%';
    if (audioEl.duration) audioEl.currentTime = pct * audioEl.duration;
  }
  els.scrubTrack.addEventListener('pointerdown', (e) => {
    isSeeking = true;
    seekFromEvent(e.clientX);
    const move = (ev) => seekFromEvent(ev.clientX);
    const up = () => { isSeeking = false; window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  });

  els.volumeSlider.addEventListener('input', () => { audioEl.volume = els.volumeSlider.value / 100; });

  // ---------- File input ----------
  $('addFilesBtn').addEventListener('click', () => fileInput.click());
  $('emptyAddBtn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => { if (e.target.files.length) addFiles(e.target.files); fileInput.value = ''; });

  // Drag & drop
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  });

  // ---------- Visualizer ----------
  function ensureAudioGraph() {
    if (audioCtx) return;
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      sourceNode = audioCtx.createMediaElementSource(audioEl);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      sourceNode.connect(analyser);
      analyser.connect(audioCtx.destination);
      startVisualizer();
    } catch (err) { /* graph already connected or unsupported */ }
  }

  function resizeCanvas() {
    const rect = els.visualizer.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    els.visualizer.width = rect.width * dpr;
    els.visualizer.height = rect.height * dpr;
    canvasCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resizeCanvas);

  function startVisualizer() {
    els.visualizerEmpty.style.display = 'none';
    resizeCanvas();
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      rafId = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);
      const w = els.visualizer.clientWidth;
      const h = els.visualizer.clientHeight;
      canvasCtx.clearRect(0, 0, w, h);

      const barCount = 48;
      const barWidth = w / barCount;
      const step = Math.floor(bufferLength / barCount);
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();

      for (let i = 0; i < barCount; i++) {
        let sum = 0;
        for (let j = 0; j < step; j++) sum += dataArray[i * step + j] || 0;
        const avg = sum / step;
        const barH = Math.max(2, (avg / 255) * h * 0.85);
        const x = i * barWidth + barWidth * 0.2;
        const bw = barWidth * 0.6;
        canvasCtx.fillStyle = audioEl.paused ? '#D2D2CD' : accent;
        const y = (h - barH) / 2;
        roundRect(canvasCtx, x, y, bw, barH, 1.5);
        canvasCtx.fill();
      }
    }
    cancelAnimationFrame(rafId);
    draw();
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // ---------- Lyrics ----------
  async function renderLyricsView() {
    const t = currentTrack();
    if (!t) {
      els.lyricsTrackName.textContent = 'NO TRACK';
      els.lyricsBody.innerHTML = `<div class="empty-state"><p>Play a track to add lyrics</p></div>`;
      els.lyricsInput.style.display = 'none';
      els.lyricsActions.style.display = 'none';
      return;
    }
    els.lyricsTrackName.textContent = `${t.title.toUpperCase()}`;
    const rec = await dbGet('lyrics', t.id);
    const text = rec ? rec.text : '';
    if (text) {
      els.lyricsBody.style.display = 'block';
      els.lyricsBody.textContent = text;
      els.lyricsInput.style.display = 'none';
      els.lyricsActions.style.display = 'flex';
      $('editLyricsBtn').style.display = 'inline-block';
      $('saveLyricsBtn').style.display = 'none';
    } else {
      els.lyricsBody.style.display = 'none';
      els.lyricsInput.style.display = 'block';
      els.lyricsInput.value = '';
      els.lyricsActions.style.display = 'flex';
      $('editLyricsBtn').style.display = 'none';
      $('saveLyricsBtn').style.display = 'inline-block';
    }
  }

  $('saveLyricsBtn').addEventListener('click', async () => {
    const t = currentTrack();
    if (!t) return;
    await dbAdd('lyrics', { trackId: t.id, text: els.lyricsInput.value });
    showToast('Lyrics saved');
    renderLyricsView();
  });

  $('editLyricsBtn').addEventListener('click', async () => {
    const t = currentTrack();
    if (!t) return;
    const rec = await dbGet('lyrics', t.id);
    els.lyricsBody.style.display = 'none';
    els.lyricsInput.style.display = 'block';
    els.lyricsInput.value = rec ? rec.text : '';
    $('editLyricsBtn').style.display = 'none';
    $('saveLyricsBtn').style.display = 'inline-block';
  });

  // ---------- Keyboard shortcuts ----------
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
    else if (e.code === 'ArrowRight' && e.shiftKey) nextTrack(true);
    else if (e.code === 'ArrowLeft' && e.shiftKey) prevTrack();
  });

  // ---------- Media Session (lock screen / notification controls) ----------
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => audioEl.play());
    navigator.mediaSession.setActionHandler('pause', () => audioEl.pause());
    navigator.mediaSession.setActionHandler('previoustrack', prevTrack);
    navigator.mediaSession.setActionHandler('nexttrack', () => nextTrack(true));
    audioEl.addEventListener('play', () => {
      const t = currentTrack();
      if (t && 'MediaMetadata' in window) {
        navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: t.artist, album: 'Soundframe' });
      }
    });
  }

  // ---------- Service worker ----------
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    });
  }

  // ---------- Init ----------
  loadLibrary();
  resizeCanvas();
})();
