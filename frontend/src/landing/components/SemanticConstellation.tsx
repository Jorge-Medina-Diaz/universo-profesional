import { useEffect, useRef, useState, type CSSProperties } from "react";

/* ------------------------------------------------------------------ *
 *  SemanticConstellation
 *
 *  A living knowledge-graph backdrop: nodes are scattered into labelled
 *  semantic REGIONS (Experiencia, Skills, Proyectos…) rather than a
 *  single ring or zig-zag. Curved glowing edges connect nodes within a
 *  region and bridge regions together. The whole field drifts gently,
 *  pulses, follows the cursor (desktop), and fires the occasional
 *  "signal" travelling along an edge.
 *
 *  Pure canvas — no Three.js / sigma. dpr + node caps keep it 60fps.
 *  Region labels are crisp DOM tags layered over the canvas.
 * ------------------------------------------------------------------ */

export interface ConstellationRegion {
  id: string;
  label: string;
  color: string;
  /** centroid in normalised 0..1 canvas space */
  cx: number;
  cy: number;
  /** number of nodes scattered around the centroid */
  count: number;
  /** spread radius as a fraction of the canvas min-dimension */
  spread?: number;
}

export const DEFAULT_REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "Experiencia", color: "#ffda6e", cx: 0.24, cy: 0.30, count: 6, spread: 0.1 },
  { id: "skill", label: "Skills", color: "#6ece9d", cx: 0.6, cy: 0.2, count: 7, spread: 0.12 },
  { id: "proj", label: "Proyectos", color: "#00d4aa", cx: 0.8, cy: 0.5, count: 6, spread: 0.1 },
  { id: "edu", label: "Educación", color: "#6ece9d", cx: 0.32, cy: 0.68, count: 5, spread: 0.09 },
  { id: "cert", label: "Certificaciones", color: "#ffda6e", cx: 0.62, cy: 0.8, count: 4, spread: 0.08 },
  { id: "lang", label: "Carrera", color: "#00d4aa", cx: 0.12, cy: 0.52, count: 4, spread: 0.07 },
];

interface Node {
  rx: number; // resting position (px)
  ry: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  region: number;
  anchor: boolean;
  pulse: number;
  pulseSpeed: number;
  bobPhase: number;
  bobAmp: number;
}

interface Edge {
  a: number;
  b: number;
  color: string;
  cross: boolean;
}

interface Signal {
  edge: number;
  t: number;
  speed: number;
  color: string;
}

/** tiny seeded RNG so layout is stable between renders/resizes */
function makeRng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function hexToRgb(hex: string): [number, number, number] {
  const m = hex.replace("#", "");
  const n = parseInt(m.length === 3 ? m.split("").map((c) => c + c).join("") : m, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function SemanticConstellation({
  regions = DEFAULT_REGIONS,
  className = "",
  interactive = true,
  showLabels = true,
  intensity = 1,
}: {
  regions?: ConstellationRegion[];
  className?: string;
  interactive?: boolean;
  showLabels?: boolean;
  /** 0..1 — scales node count / motion for denser or calmer fields */
  intensity?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const signalsRef = useRef<Signal[]>([]);
  const rafRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0 });
  const pointerRef = useRef({ x: -9999, y: -9999, tx: 0, ty: 0, cx: 0, cy: 0 });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const coarse = window.matchMedia("(max-width: 768px)").matches;
    const allowPointer = interactive && !coarse && !reduced;

    function build() {
      const w = wrap!.clientWidth;
      const h = wrap!.clientHeight;
      if (w === 0 || h === 0) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      sizeRef.current = { w, h };
      canvas!.width = Math.floor(w * dpr);
      canvas!.height = Math.floor(h * dpr);
      canvas!.style.width = w + "px";
      canvas!.style.height = h + "px";
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

      const min = Math.min(w, h);
      const rng = makeRng(20240517);
      const nodes: Node[] = [];
      const densityScale = coarse ? 0.62 : 1;

      regions.forEach((region, ri) => {
        const spread = (region.spread ?? 0.1) * min;
        const count = Math.max(3, Math.round(region.count * intensity * densityScale));
        // anchor (region core)
        nodes.push({
          rx: region.cx * w,
          ry: region.cy * h,
          x: region.cx * w,
          y: region.cy * h,
          vx: 0,
          vy: 0,
          radius: 3.4,
          color: region.color,
          region: ri,
          anchor: true,
          pulse: rng() * Math.PI * 2,
          pulseSpeed: 0.01 + rng() * 0.01,
          bobPhase: rng() * Math.PI * 2,
          bobAmp: 2 + rng() * 2,
        });
        for (let i = 0; i < count; i++) {
          const ang = rng() * Math.PI * 2;
          const r = Math.pow(rng(), 0.7) * spread;
          const rx = region.cx * w + Math.cos(ang) * r;
          const ry = region.cy * h + Math.sin(ang) * r * 0.85;
          nodes.push({
            rx,
            ry,
            x: rx,
            y: ry,
            vx: 0,
            vy: 0,
            radius: 1.3 + rng() * 1.9,
            color: region.color,
            region: ri,
            anchor: false,
            pulse: rng() * Math.PI * 2,
            pulseSpeed: 0.006 + rng() * 0.014,
            bobPhase: rng() * Math.PI * 2,
            bobAmp: 3 + rng() * 4,
          });
        }
      });

      // edges: within-region (node → its anchor + a near neighbour), and
      // sparse cross-region bridges (anchor → anchor of adjacent region).
      const edges: Edge[] = [];
      const anchorIdx: number[] = [];
      nodes.forEach((n, i) => {
        if (n.anchor) anchorIdx[n.region] = i;
      });
      nodes.forEach((n, i) => {
        if (n.anchor) return;
        edges.push({ a: i, b: anchorIdx[n.region], color: n.color, cross: false });
        // one extra near-neighbour link for graph texture
        let best = -1;
        let bestD = Infinity;
        nodes.forEach((m, j) => {
          if (j === i || m.region !== n.region || m.anchor) return;
          const d = (m.x - n.x) ** 2 + (m.y - n.y) ** 2;
          if (d < bestD) {
            bestD = d;
            best = j;
          }
        });
        if (best >= 0 && rng() > 0.45) edges.push({ a: i, b: best, color: n.color, cross: false });
      });
      // cross-region bridges
      for (let r = 0; r < regions.length; r++) {
        const a = anchorIdx[r];
        const b = anchorIdx[(r + 1) % regions.length];
        if (a != null && b != null) edges.push({ a, b, color: "#ffffff", cross: true });
        if (r % 2 === 0) {
          const c = anchorIdx[(r + 2) % regions.length];
          if (a != null && c != null) edges.push({ a, b: c, color: "#ffffff", cross: true });
        }
      }

      nodesRef.current = nodes;
      edgesRef.current = edges;
      signalsRef.current = [];
      setReady(true);
    }

    build();

    const ro = new ResizeObserver(() => build());
    ro.observe(wrap);

    function onMove(e: MouseEvent) {
      const rect = wrap!.getBoundingClientRect();
      pointerRef.current.x = e.clientX - rect.left;
      pointerRef.current.y = e.clientY - rect.top;
      pointerRef.current.tx = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      pointerRef.current.ty = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    }
    function onLeave() {
      pointerRef.current.x = -9999;
      pointerRef.current.y = -9999;
      pointerRef.current.tx = 0;
      pointerRef.current.ty = 0;
    }
    if (allowPointer) {
      wrap.addEventListener("mousemove", onMove);
      wrap.addEventListener("mouseleave", onLeave);
    }

    let frame = 0;
    function draw() {
      const { w, h } = sizeRef.current;
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const signals = signalsRef.current;
      const p = pointerRef.current;
      ctx!.clearRect(0, 0, w, h);

      // ease the global parallax offset toward the pointer target
      p.cx += (p.tx * 14 - p.cx) * 0.06;
      p.cy += (p.ty * 14 - p.cy) * 0.06;
      if (wrap) wrap.style.setProperty("--px", `${p.cx.toFixed(2)}px`);
      if (wrap) wrap.style.setProperty("--py", `${p.cy.toFixed(2)}px`);

      // physics
      for (const n of nodes) {
        if (!reduced) {
          n.bobPhase += 0.01;
          const driftX = Math.cos(n.bobPhase) * n.bobAmp * 0.04;
          const driftY = Math.sin(n.bobPhase * 0.9) * n.bobAmp * 0.04;
          n.vx += (n.rx - n.x) * 0.004 + driftX;
          n.vy += (n.ry - n.y) * 0.004 + driftY;
          if (allowPointer && p.x > -9000) {
            const dx = n.x - p.x;
            const dy = n.y - p.y;
            const dist = Math.hypot(dx, dy);
            if (dist < 150 && dist > 0.5) {
              const f = ((150 - dist) / 150) * 0.5;
              n.vx += (dx / dist) * f;
              n.vy += (dy / dist) * f;
            }
          }
          n.vx *= 0.9;
          n.vy *= 0.9;
          n.x += n.vx + p.cx * 0.02;
          n.y += n.vy + p.cy * 0.02;
          n.pulse += n.pulseSpeed;
        }
      }

      // edges
      for (const e of edges) {
        const a = nodes[e.a];
        const b = nodes[e.b];
        if (!a || !b) continue;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        const cx = (a.x + b.x) / 2 + Math.sin(frame * 0.008 + e.a) * dist * 0.06;
        const cy = (a.y + b.y) / 2 + Math.cos(frame * 0.008 + e.b) * dist * 0.06;
        ctx!.beginPath();
        ctx!.moveTo(a.x, a.y);
        ctx!.quadraticCurveTo(cx, cy, b.x, b.y);
        if (e.cross) {
          ctx!.strokeStyle = `rgba(244,241,234,0.07)`;
          ctx!.lineWidth = 0.6;
        } else {
          const [r, g, bl] = hexToRgb(e.color);
          ctx!.strokeStyle = `rgba(${r},${g},${bl},0.22)`;
          ctx!.lineWidth = 0.8;
        }
        ctx!.stroke();
      }

      // signals travelling along edges
      if (!reduced && frame % 70 === 0 && edges.length) {
        const ei = Math.floor(Math.random() * edges.length);
        signalsRef.current.push({
          edge: ei,
          t: 0,
          speed: 0.012 + Math.random() * 0.02,
          color: edges[ei].cross ? "#ffffff" : edges[ei].color,
        });
      }
      for (let i = signals.length - 1; i >= 0; i--) {
        const s = signals[i];
        const e = edges[s.edge];
        const a = nodes[e?.a];
        const b = nodes[e?.b];
        if (!a || !b) {
          signals.splice(i, 1);
          continue;
        }
        s.t += s.speed;
        if (s.t >= 1) {
          signals.splice(i, 1);
          continue;
        }
        const mx = (a.x + b.x) / 2 + Math.sin(frame * 0.008 + e.a) * Math.hypot(a.x - b.x, a.y - b.y) * 0.06;
        const my = (a.y + b.y) / 2 + Math.cos(frame * 0.008 + e.b) * Math.hypot(a.x - b.x, a.y - b.y) * 0.06;
        const t = s.t;
        const it = 1 - t;
        const sx = it * it * a.x + 2 * it * t * mx + t * t * b.x;
        const sy = it * it * a.y + 2 * it * t * my + t * t * b.y;
        const [r, g, bl] = hexToRgb(s.color);
        const grad = ctx!.createRadialGradient(sx, sy, 0, sx, sy, 6);
        grad.addColorStop(0, `rgba(${r},${g},${bl},0.9)`);
        grad.addColorStop(1, `rgba(${r},${g},${bl},0)`);
        ctx!.fillStyle = grad;
        ctx!.beginPath();
        ctx!.arc(sx, sy, 6, 0, Math.PI * 2);
        ctx!.fill();
      }

      // nodes
      for (const n of nodes) {
        const pulseR = n.radius + Math.sin(n.pulse) * 0.5;
        const [r, g, bl] = hexToRgb(n.color);

        // halo
        const haloR = pulseR * (n.anchor ? 7 : 5);
        const grad = ctx!.createRadialGradient(n.x, n.y, pulseR * 0.5, n.x, n.y, haloR);
        grad.addColorStop(0, `rgba(${r},${g},${bl},${n.anchor ? 0.28 : 0.18})`);
        grad.addColorStop(1, `rgba(${r},${g},${bl},0)`);
        ctx!.fillStyle = grad;
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, haloR, 0, Math.PI * 2);
        ctx!.fill();

        // core
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, pulseR, 0, Math.PI * 2);
        ctx!.fillStyle = n.anchor ? "#fffaf0" : n.color;
        ctx!.globalAlpha = n.anchor ? 1 : 0.55 + Math.sin(n.pulse) * 0.25;
        ctx!.fill();
        ctx!.globalAlpha = 1;
      }

      frame++;
      rafRef.current = requestAnimationFrame(draw);
    }

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(rafRef.current);
      if (allowPointer) {
        wrap.removeEventListener("mousemove", onMove);
        wrap.removeEventListener("mouseleave", onLeave);
      }
    };
  }, [regions, interactive, intensity]);

  return (
    <div ref={wrapRef} className={className}>
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="absolute inset-0 h-full w-full"
        style={{
          transform: "translate3d(var(--px,0), var(--py,0), 0)",
          transition: "transform 0.6s cubic-bezier(0.2,0.8,0.2,1)",
        }}
      />
      {showLabels && ready && (
        <div className="pointer-events-none absolute inset-0">
          {regions.map((region, i) => (
            <span
              key={region.id}
              className="cos-region-label"
              style={
                {
                  left: `${region.cx * 100}%`,
                  top: `${region.cy * 100}%`,
                  // lift the label just above its node cluster
                  marginTop: "-34px",
                  "--cl-color": region.color,
                  animation: `cos-fade-in 0.8s ease ${0.3 + i * 0.12}s both`,
                  transform:
                    "translate(-50%, -50%) translate3d(calc(var(--px,0px) * 1.4), calc(var(--py,0px) * 1.4), 0)",
                } as CSSProperties
              }
            >
              {region.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
