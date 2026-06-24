"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { GraphNode, GraphEdge } from "@/lib/types";
import { formatName } from "@/lib/utils";
import { Share2 } from "lucide-react";

const COLOR: Record<string, string> = {
  person: "#8B7CF0", project: "#F0997B", task: "#35C28E", report: "#9AA0AB", email: "#E0B341",
};
const RADIUS: Record<string, number> = { person: 7, project: 10, task: 5, report: 6, email: 5 };
const W = 600, H = 320;
const R = 120;          // sphere radius for the initial layout
const FL = 460;         // perspective focal length (smaller = stronger 3D)
const GOLDEN = Math.PI * (3 - Math.sqrt(5));

// 3D node: position, velocity, and a phase for perpetual floating.
type P = { x: number; y: number; z: number; vx: number; vy: number; vz: number; ph: number };

export default function GraphPanel() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const pos = useRef<Record<string, P>>({});
  const tick = useRef(0);
  const [, render] = useState(0);

  useEffect(() => {
    api.getGraph()
      .then((g) => { setNodes(g.nodes); setEdges(g.edges); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!nodes.length) return;
    // Seed positions on a Fibonacci sphere so it starts looking 3D.
    const p: Record<string, P> = {};
    const N = nodes.length;
    nodes.forEach((n, i) => {
      const y = 1 - (i / Math.max(1, N - 1)) * 2;     // 1 → -1
      const rr = Math.sqrt(Math.max(0, 1 - y * y));
      const th = GOLDEN * i;
      p[n.id] = {
        x: Math.cos(th) * rr * R, y: y * R, z: Math.sin(th) * rr * R,
        vx: 0, vy: 0, vz: 0, ph: Math.random() * Math.PI * 2,
      };
    });
    pos.current = p;
    const ids = new Set(nodes.map((n) => n.id));
    const E = edges.filter((e) => ids.has(e.source) && ids.has(e.target));

    let raf = 0;
    const step = () => {
      const P0 = pos.current;
      // Force-directed layout in 3D (repulsion + edge springs + centering).
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const A = P0[nodes[i].id], B = P0[nodes[j].id];
          const dx = A.x - B.x, dy = A.y - B.y, dz = A.z - B.z;
          const d2 = dx * dx + dy * dy + dz * dz + 0.01, d = Math.sqrt(d2);
          const f = 2600 / d2, ux = dx / d, uy = dy / d, uz = dz / d;
          A.vx += ux * f; A.vy += uy * f; A.vz += uz * f;
          B.vx -= ux * f; B.vy -= uy * f; B.vz -= uz * f;
        }
      }
      for (const e of E) {
        const A = P0[e.source], B = P0[e.target];
        const dx = B.x - A.x, dy = B.y - A.y, dz = B.z - A.z;
        const d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
        const f = (d - 70) * 0.015, ux = dx / d, uy = dy / d, uz = dz / d;
        A.vx += ux * f; A.vy += uy * f; A.vz += uz * f;
        B.vx -= ux * f; B.vy -= uy * f; B.vz -= uz * f;
      }
      for (const n of nodes) {
        const a = P0[n.id];
        a.vx += -a.x * 0.004; a.vy += -a.y * 0.004; a.vz += -a.z * 0.004;  // pull to origin
        a.vx *= 0.9; a.vy *= 0.9; a.vz *= 0.9;
        a.x += a.vx; a.y += a.vy; a.z += a.vz;
      }
      tick.current += 1;
      render((v) => (v + 1) % 1e9);
      raf = requestAnimationFrame(step);   // never stops — perpetual motion
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [nodes, edges]);

  const P0 = pos.current;
  const ready = nodes.length > 0 && !!P0[nodes[0].id];

  // Project the tumbling 3D scene to 2D for this frame.
  const t = tick.current;
  const ay = t * 0.004;                          // slow spin around Y
  const ax = 0.34 + Math.sin(t * 0.005) * 0.16;  // gentle tumble around X
  const cay = Math.cos(ay), say = Math.sin(ay), cax = Math.cos(ax), sax = Math.sin(ax);

  const project = (a: P) => {
    const bob = Math.sin(t * 0.02 + a.ph) * 4;          // floating bob
    const bx = a.x, by = a.y + bob, bz = a.z;
    const x1 = bx * cay + bz * say;                      // rotate Y
    const z1 = -bx * say + bz * cay;
    const y2 = by * cax - z1 * sax;                      // rotate X
    const z2 = by * sax + z1 * cax;
    const s = FL / (FL + z2);                            // perspective
    return { sx: W / 2 + x1 * s, sy: H / 2 + y2 * s, s };
  };

  const proj: Record<string, { sx: number; sy: number; s: number }> = {};
  if (ready) for (const n of nodes) proj[n.id] = project(P0[n.id]);

  // Draw far nodes first so nearer ones sit on top.
  const order = ready ? [...nodes].sort((a, b) => proj[a.id].s - proj[b.id].s) : [];

  const legend = [
    ["person", "People"], ["project", "Projects"], ["task", "Tasks"], ["report", "Reports"], ["email", "Emails"],
  ] as const;

  return (
    <div className="rounded-xl bg-surface border border-ui-border p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-text-1">
          <Share2 className="h-4 w-4 text-brand-purple" /> Knowledge Graph
        </h2>
        <div className="flex items-center gap-3 text-[10px] text-text-3">
          {legend.map(([k, label]) => (
            <span key={k} className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: COLOR[k] }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[320px] flex items-center justify-center text-text-3 text-xs">Loading graph…</div>
      ) : nodes.length === 0 ? (
        <div className="h-[320px] flex items-center justify-center text-text-3 text-xs">No connections to show yet</div>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
          {ready && edges.map((e, i) => {
            const a = proj[e.source], b = proj[e.target];
            if (!a || !b) return null;
            const depth = (a.s + b.s) / 2;
            return (
              <line key={i} x1={a.sx} y1={a.sy} x2={b.sx} y2={b.sy}
                stroke="var(--ui-border)" strokeWidth={depth} strokeOpacity={0.15 + depth * 0.25} />
            );
          })}
          {ready && order.map((n) => {
            const a = proj[n.id];
            if (!a) return null;
            const r = (RADIUS[n.type] ?? 5) * a.s;
            const showLabel = (n.type === "person" || n.type === "project") && a.s > 0.92;
            const label = n.type === "person" ? formatName(n.label) : n.label;
            return (
              <g key={n.id} opacity={Math.max(0.35, Math.min(1, a.s * 0.85))}>
                <circle cx={a.sx} cy={a.sy} r={r} fill={COLOR[n.type] ?? "#888"} stroke="var(--surface)" strokeWidth={1.5}>
                  <title>{label}</title>
                </circle>
                {showLabel && (
                  <text x={a.sx} y={a.sy + r + 9} textAnchor="middle" fontSize={9} fill="var(--text-2)">
                    {label.length > 14 ? label.slice(0, 13) + "…" : label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
