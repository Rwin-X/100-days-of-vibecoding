import React, { useState, useRef, useCallback, useEffect } from "react";
import { Plus, X, Link2, Trash2, Download, Search, Filter } from "lucide-react";

// ---- constants ----
const TAGS = [
  { id: "offsec", label: "OFFSEC", color: "#39ff8f" },
  { id: "auto", label: "AUTOMATION", color: "#00d4ff" },
  { id: "osint", label: "OSINT", color: "#c792ea" },
  { id: "tool", label: "TOOL", color: "#ffb454" },
  { id: "learn", label: "LEARN", color: "#7a8a99" },
];

const STORAGE_KEY = "ideacanvas:nodes:v1";
const LINKS_KEY = "ideacanvas:links:v1";

const uid = () => Math.random().toString(36).slice(2, 10);

const STATUS = ["SEED", "ACTIVE", "SHIPPED", "DORMANT"];
const STATUS_COLOR = {
  SEED: "#7a8a99",
  ACTIVE: "#39ff8f",
  SHIPPED: "#00d4ff",
  DORMANT: "#ff4d4d",
};

export default function IdeaCanvas() {
  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [dragId, setDragId] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [linking, setLinking] = useState(null); // node id currently drawing a link from
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState(null);
  const [filterTag, setFilterTag] = useState(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const canvasRef = useRef(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [panning, setPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });

  // ---- persistence ----
  useEffect(() => {
    (async () => {
      try {
        const n = await window.storage.get(STORAGE_KEY);
        if (n?.value) setNodes(JSON.parse(n.value));
      } catch (e) {}
      try {
        const l = await window.storage.get(LINKS_KEY);
        if (l?.value) setLinks(JSON.parse(l.value));
      } catch (e) {}
      setLoaded(true);
    })();
  }, []);

  useEffect(() => {
    if (!loaded) return;
    window.storage.set(STORAGE_KEY, JSON.stringify(nodes)).catch(() => {});
  }, [nodes, loaded]);

  useEffect(() => {
    if (!loaded) return;
    window.storage.set(LINKS_KEY, JSON.stringify(links)).catch(() => {});
  }, [links, loaded]);

  // seed a first node on empty vault
  useEffect(() => {
    if (loaded && nodes.length === 0) {
      setNodes([
        {
          id: uid(),
          x: 420,
          y: 260,
          title: "New capture",
          body: "Double-click any node to edit. Drag from the dot to link ideas.",
          tag: "learn",
          status: "SEED",
        },
      ]);
    }
    // eslint-disable-next-line
  }, [loaded]);

  // ---- node ops ----
  const addNode = () => {
    const rect = canvasRef.current?.getBoundingClientRect();
    const cx = rect ? rect.width / 2 - pan.x : 300;
    const cy = rect ? rect.height / 2 - pan.y : 200;
    const id = uid();
    setNodes((prev) => [
      ...prev,
      {
        id,
        x: cx + (Math.random() * 80 - 40),
        y: cy + (Math.random() * 80 - 40),
        title: "Untitled signal",
        body: "",
        tag: "learn",
        status: "SEED",
      },
    ]);
    setEditing(id);
  };

  const updateNode = (id, patch) =>
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch } : n)));

  const deleteNode = (id) => {
    setNodes((prev) => prev.filter((n) => n.id !== id));
    setLinks((prev) => prev.filter((l) => l.from !== id && l.to !== id));
    if (selected === id) setSelected(null);
    if (editing === id) setEditing(null);
  };

  // ---- drag node ----
  const onNodePointerDown = (e, id) => {
    if (e.target.closest(".no-drag")) return;
    e.stopPropagation();
    const rect = canvasRef.current.getBoundingClientRect();
    const node = nodes.find((n) => n.id === id);
    setDragId(id);
    setSelected(id);
    setDragOffset({
      x: e.clientX - rect.left - pan.x - node.x,
      y: e.clientY - rect.top - pan.y - node.y,
    });
  };

  const onCanvasPointerMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - pan.x;
    const y = e.clientY - rect.top - pan.y;
    setCursor({ x, y });
    if (dragId) {
      updateNode(dragId, { x: x - dragOffset.x, y: y - dragOffset.y });
    }
    if (panning) {
      setPan((p) => ({
        x: p.x + (e.clientX - panStart.current.x),
        y: p.y + (e.clientY - panStart.current.y),
      }));
      panStart.current = { x: e.clientX, y: e.clientY };
    }
  };

  const onCanvasPointerUp = () => {
    setDragId(null);
    setPanning(false);
  };

  const onCanvasPointerDown = (e) => {
    if (e.target !== canvasRef.current && e.target.id !== "bg-grid") return;
    setSelected(null);
    setLinking(null);
    setPanning(true);
    panStart.current = { x: e.clientX, y: e.clientY };
  };

  // ---- linking ----
  const startLink = (e, id) => {
    e.stopPropagation();
    setLinking(id);
  };

  const finishLink = (e, id) => {
    e.stopPropagation();
    if (linking && linking !== id) {
      setLinks((prev) => {
        const exists = prev.some(
          (l) =>
            (l.from === linking && l.to === id) ||
            (l.from === id && l.to === linking)
        );
        if (exists) return prev;
        return [...prev, { id: uid(), from: linking, to: id }];
      });
    }
    setLinking(null);
  };

  const removeLink = (id) => setLinks((prev) => prev.filter((l) => l.id !== id));

  // ---- filtering ----
  const visibleIds = new Set(
    nodes
      .filter((n) => {
        if (filterTag && n.tag !== filterTag) return false;
        if (
          query &&
          !`${n.title} ${n.body}`.toLowerCase().includes(query.toLowerCase())
        )
          return false;
        return true;
      })
      .map((n) => n.id)
  );

  const exportJSON = () => {
    const data = JSON.stringify({ nodes, links }, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "idea-canvas-export.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const nodeById = (id) => nodes.find((n) => n.id === id);

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        minHeight: 600,
        background: "#05070a",
        fontFamily: "'JetBrains Mono', monospace",
        position: "relative",
        overflow: "hidden",
        color: "#d6dde3",
        userSelect: dragId || panning ? "none" : "auto",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
        .idc-scroll::-webkit-scrollbar { width: 6px; }
        .idc-scroll::-webkit-scrollbar-thumb { background: #1a2530; border-radius: 4px; }
        @keyframes pulse-dot {
          0%, 100% { box-shadow: 0 0 0 0 rgba(57,255,143,0.55); }
          50% { box-shadow: 0 0 0 6px rgba(57,255,143,0); }
        }
        @keyframes flow {
          to { stroke-dashoffset: -24; }
        }
        .idc-node-enter {
          animation: nodeIn 0.25s ease-out;
        }
        @keyframes nodeIn {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        .idc-btn {
          transition: all 0.15s ease;
        }
        .idc-btn:hover {
          filter: brightness(1.3);
          transform: translateY(-1px);
        }
        textarea.idc-input, input.idc-input {
          font-family: 'Space Grotesk', sans-serif;
        }
      `}</style>

      {/* background grid */}
      <div
        id="bg-grid"
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(#0d151c 1px, transparent 1px), linear-gradient(90deg, #0d151c 1px, transparent 1px)",
          backgroundSize: "36px 36px",
          backgroundPosition: `${pan.x % 36}px ${pan.y % 36}px`,
          opacity: 0.6,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 20% 15%, rgba(57,255,143,0.06), transparent 40%), radial-gradient(circle at 85% 80%, rgba(0,212,255,0.05), transparent 45%)",
        }}
      />

      {/* HUD top bar */}
      <div
        style={{
          position: "absolute",
          top: 16,
          left: 16,
          right: 16,
          zIndex: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            pointerEvents: "auto",
            background: "rgba(10,15,20,0.85)",
            border: "1px solid #1a2530",
            borderRadius: 8,
            padding: "8px 14px",
            backdropFilter: "blur(8px)",
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#39ff8f",
              animation: "pulse-dot 2s infinite",
            }}
          />
          <span
            style={{
              fontSize: 12,
              letterSpacing: "0.12em",
              color: "#39ff8f",
              fontWeight: 700,
            }}
          >
            IDEA_CANVAS
          </span>
          <span style={{ fontSize: 11, color: "#4a5a68" }}>
            // {nodes.length} signals · {links.length} traces
          </span>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            pointerEvents: "auto",
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(10,15,20,0.85)",
              border: "1px solid #1a2530",
              borderRadius: 8,
              padding: "6px 10px",
              backdropFilter: "blur(8px)",
            }}
          >
            <Search size={13} color="#4a5a68" />
            <input
              className="idc-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search signals"
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                color: "#d6dde3",
                fontSize: 12,
                width: 130,
              }}
            />
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              background: "rgba(10,15,20,0.85)",
              border: "1px solid #1a2530",
              borderRadius: 8,
              padding: "4px 6px",
              backdropFilter: "blur(8px)",
            }}
          >
            <Filter size={12} color="#4a5a68" style={{ marginLeft: 4 }} />
            {TAGS.map((t) => (
              <button
                key={t.id}
                onClick={() =>
                  setFilterTag((f) => (f === t.id ? null : t.id))
                }
                className="idc-btn"
                style={{
                  fontSize: 9,
                  letterSpacing: "0.06em",
                  padding: "5px 8px",
                  borderRadius: 5,
                  border: `1px solid ${
                    filterTag === t.id ? t.color : "#1a2530"
                  }`,
                  background:
                    filterTag === t.id ? `${t.color}22` : "transparent",
                  color: filterTag === t.id ? t.color : "#5a6a78",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                {t.label}
              </button>
            ))}
          </div>

          <button
            onClick={exportJSON}
            className="idc-btn no-drag"
            title="Export vault"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(10,15,20,0.85)",
              border: "1px solid #1a2530",
              borderRadius: 8,
              padding: "8px 12px",
              color: "#7a8a99",
              cursor: "pointer",
              fontSize: 11,
              backdropFilter: "blur(8px)",
            }}
          >
            <Download size={13} />
          </button>

          <button
            onClick={addNode}
            className="idc-btn no-drag"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#39ff8f",
              border: "1px solid #39ff8f",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#05070a",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: "0.04em",
            }}
          >
            <Plus size={14} strokeWidth={3} /> CAPTURE
          </button>
        </div>
      </div>

      {/* canvas */}
      <div
        ref={canvasRef}
        onPointerMove={onCanvasPointerMove}
        onPointerUp={onCanvasPointerUp}
        onPointerLeave={onCanvasPointerUp}
        onPointerDown={onCanvasPointerDown}
        style={{
          position: "absolute",
          inset: 0,
          cursor: panning ? "grabbing" : "grab",
        }}
      >
        <svg
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        >
          <g transform={`translate(${pan.x}, ${pan.y})`}>
            {links.map((l) => {
              const a = nodeById(l.from);
              const b = nodeById(l.to);
              if (!a || !b) return null;
              const fade =
                filterTag &&
                (!visibleIds.has(a.id) || !visibleIds.has(b.id));
              const mx = (a.x + b.x) / 2;
              const my = (a.y + b.y) / 2;
              return (
                <g key={l.id} style={{ pointerEvents: "auto" }}>
                  <path
                    d={`M ${a.x + 100} ${a.y + 34} Q ${mx} ${my - 30}, ${
                      b.x + 100
                    } ${b.y + 34}`}
                    fill="none"
                    stroke="#39ff8f"
                    strokeOpacity={fade ? 0.06 : 0.35}
                    strokeWidth={1.5}
                    strokeDasharray="4 6"
                    style={{ animation: "flow 1.2s linear infinite" }}
                  />
                  <circle
                    cx={mx}
                    cy={my - 15}
                    r={7}
                    fill="#05070a"
                    stroke="#ff4d4d"
                    strokeOpacity={fade ? 0 : 0.6}
                    strokeWidth={1}
                    className="no-drag"
                    style={{
                      cursor: fade ? "default" : "pointer",
                      pointerEvents: fade ? "none" : "auto",
                    }}
                    onClick={() => removeLink(l.id)}
                  />
                </g>
              );
            })}
            {linking && (
              <line
                x1={nodeById(linking).x + 100}
                y1={nodeById(linking).y + 34}
                x2={cursor.x}
                y2={cursor.y}
                stroke="#00d4ff"
                strokeWidth={1.5}
                strokeDasharray="3 5"
              />
            )}
          </g>
        </svg>

        <div
          style={{
            position: "absolute",
            inset: 0,
            transform: `translate(${pan.x}px, ${pan.y}px)`,
          }}
        >
          {nodes.map((n) => {
            const tag = TAGS.find((t) => t.id === n.tag) || TAGS[0];
            const dim = filterTag || query ? !visibleIds.has(n.id) : false;
            const isEditing = editing === n.id;
            return (
              <div
                key={n.id}
                className="idc-node-enter no-drag"
                onPointerDown={(e) => onNodePointerDown(e, n.id)}
                onDoubleClick={() => setEditing(n.id)}
                style={{
                  position: "absolute",
                  left: n.x,
                  top: n.y,
                  width: 200,
                  background: "#0a0f14",
                  border: `1px solid ${
                    selected === n.id ? tag.color : "#1a2530"
                  }`,
                  borderRadius: 10,
                  boxShadow:
                    selected === n.id
                      ? `0 0 0 1px ${tag.color}55, 0 8px 24px rgba(0,0,0,0.5)`
                      : "0 4px 16px rgba(0,0,0,0.4)",
                  opacity: dim ? 0.25 : 1,
                  cursor: "grab",
                  transition: "opacity 0.2s, border-color 0.2s",
                  zIndex: selected === n.id ? 10 : 1,
                }}
              >
                {/* header strip */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 10px 6px",
                    borderBottom: "1px solid #131c24",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: STATUS_COLOR[n.status],
                        flexShrink: 0,
                      }}
                    />
                    <select
                      value={n.status}
                      onChange={(e) =>
                        updateNode(n.id, { status: e.target.value })
                      }
                      className="no-drag"
                      style={{
                        background: "transparent",
                        border: "none",
                        outline: "none",
                        color: "#5a6a78",
                        fontSize: 9,
                        letterSpacing: "0.05em",
                        fontFamily: "'JetBrains Mono', monospace",
                        cursor: "pointer",
                      }}
                    >
                      {STATUS.map((s) => (
                        <option
                          key={s}
                          value={s}
                          style={{ background: "#0a0f14" }}
                        >
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={(e) => startLink(e, n.id)}
                      className="no-drag"
                      title="Draw trace link"
                      style={{
                        background: "none",
                        border: "none",
                        color: linking === n.id ? "#00d4ff" : "#3a4a58",
                        cursor: "crosshair",
                        padding: 2,
                        display: "flex",
                      }}
                    >
                      <Link2 size={12} />
                    </button>
                    <button
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteNode(n.id);
                      }}
                      className="no-drag"
                      style={{
                        background: "none",
                        border: "none",
                        color: "#3a4a58",
                        cursor: "pointer",
                        padding: 2,
                        display: "flex",
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>

                {/* body */}
                <div style={{ padding: "10px 12px 12px" }}>
                  {isEditing ? (
                    <input
                      autoFocus
                      className="idc-input no-drag"
                      value={n.title}
                      onChange={(e) =>
                        updateNode(n.id, { title: e.target.value })
                      }
                      onBlur={() => setEditing(null)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") setEditing(null);
                      }}
                      style={{
                        width: "100%",
                        background: "#050a0d",
                        border: "1px solid #1a2530",
                        borderRadius: 4,
                        padding: "4px 6px",
                        color: "#eef3f6",
                        fontSize: 13,
                        fontWeight: 600,
                        marginBottom: 6,
                        outline: "none",
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        fontFamily: "'Space Grotesk', sans-serif",
                        fontSize: 13,
                        fontWeight: 600,
                        color: "#eef3f6",
                        marginBottom: 6,
                        lineHeight: 1.3,
                      }}
                    >
                      {n.title || "Untitled signal"}
                    </div>
                  )}

                  {isEditing ? (
                    <textarea
                      className="idc-input no-drag"
                      value={n.body}
                      onChange={(e) =>
                        updateNode(n.id, { body: e.target.value })
                      }
                      rows={3}
                      placeholder="details..."
                      style={{
                        width: "100%",
                        background: "#050a0d",
                        border: "1px solid #1a2530",
                        borderRadius: 4,
                        padding: "5px 6px",
                        color: "#9fb0bd",
                        fontSize: 11.5,
                        resize: "vertical",
                        outline: "none",
                        lineHeight: 1.4,
                      }}
                    />
                  ) : (
                    n.body && (
                      <div
                        style={{
                          fontFamily: "'Space Grotesk', sans-serif",
                          fontSize: 11.5,
                          color: "#8393a0",
                          lineHeight: 1.4,
                          marginBottom: 6,
                          maxHeight: 60,
                          overflow: "hidden",
                        }}
                      >
                        {n.body}
                      </div>
                    )
                  )}

                  <div
                    style={{
                      display: "flex",
                      gap: 4,
                      flexWrap: "wrap",
                      marginTop: 8,
                    }}
                  >
                    {TAGS.map((t) => (
                      <button
                        key={t.id}
                        onPointerDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          updateNode(n.id, { tag: t.id });
                        }}
                        className="no-drag"
                        style={{
                          fontSize: 8,
                          padding: "2px 6px",
                          borderRadius: 4,
                          border: `1px solid ${
                            n.tag === t.id ? t.color : "#1a2530"
                          }`,
                          background:
                            n.tag === t.id ? `${t.color}1c` : "transparent",
                          color: n.tag === t.id ? t.color : "#3a4a58",
                          cursor: "pointer",
                          fontWeight: 700,
                          letterSpacing: "0.03em",
                        }}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* link handle */}
                <div
                  onPointerDown={(e) => e.stopPropagation()}
                  onMouseDown={(e) => startLink(e, n.id)}
                  onMouseUp={(e) => finishLink(e, n.id)}
                  title="Drag to link"
                  style={{
                    position: "absolute",
                    right: -6,
                    top: 34,
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: "#0a0f14",
                    border: `2px solid ${tag.color}`,
                    cursor: "crosshair",
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* footer hint */}
      <div
        style={{
          position: "absolute",
          bottom: 14,
          left: 16,
          fontSize: 10,
          color: "#3a4a58",
          letterSpacing: "0.04em",
          pointerEvents: "none",
        }}
      >
        drag canvas to pan · drag node to move · drag dot to link · dbl-click
        to edit · click link midpoint to sever
      </div>
    </div>
  );
}
