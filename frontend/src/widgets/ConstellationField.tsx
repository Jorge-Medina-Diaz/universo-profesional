import { useEffect, useRef } from "react";

interface Node {
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  pulse: number;
  pulseSpeed: number;
}

const PALETTE = ["#ffda6e", "#6ece9d", "#00d4aa", "#0a0a0a"];
const PALETTE_DARK = ["#ffda6e", "#6ece9d", "#00d4aa", "#ffffff"];
const PALETTE_WEIGHTS = [0.35, 0.3, 0.2, 0.15];

function pickColor(dark = false): string {
  const palette = dark ? PALETTE_DARK : PALETTE;
  const r = Math.random();
  let sum = 0;
  for (let i = 0; i < PALETTE_WEIGHTS.length; i++) {
    sum += PALETTE_WEIGHTS[i];
    if (r <= sum) return palette[i];
  }
  return palette[0];
}

function initNodes(w: number, h: number, dark = false, density = 0.00014): Node[] {
  const count = Math.max(30, Math.min(110, Math.floor(w * h * density)));
  const nodes: Node[] = [];
  for (let i = 0; i < count; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    nodes.push({
      x,
      y,
      baseX: x,
      baseY: y,
      vx: (Math.random() - 0.5) * 0.2,
      vy: (Math.random() - 0.5) * 0.2,
      radius: Math.random() * 2.0 + 0.6,
      color: pickColor(dark),
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: 0.006 + Math.random() * 0.012,
    });
  }
  return nodes;
}

export function ConstellationField({
  className = "",
  dark = false,
}: {
  className?: string;
  dark?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<Node[]>([]);
  const rafRef = useRef<number>(0);
  const sizeRef = useRef({ w: 0, h: 0 });
  const mouseRef = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function onMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }
    function onMouseLeave() {
      mouseRef.current = { x: -1000, y: -1000 };
    }

    function resize() {
      const parent = canvas!.parentElement;
      if (!parent) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = parent.clientWidth;
      const h = parent.clientHeight;
      sizeRef.current = { w, h };
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      canvas!.style.width = w + "px";
      canvas!.style.height = h + "px";
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      nodesRef.current = initNodes(w, h, dark);
    }

    resize();
    window.addEventListener("resize", resize);
    canvas.parentElement?.addEventListener("mousemove", onMouseMove);
    canvas.parentElement?.addEventListener("mouseleave", onMouseLeave);

    let frame = 0;
    function draw() {
      if (!ctx) return;
      const { w, h } = sizeRef.current;
      const mouse = mouseRef.current;
      ctx.clearRect(0, 0, w, h);

      const nodes = nodesRef.current;
      const connectDist = 150;

      // Mouse parallax: nodes gently follow cursor
      if (!reduced) {
        for (const n of nodes) {
          const dx = mouse.x - n.x;
          const dy = mouse.y - n.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 200 && dist > 1) {
            const force = (200 - dist) / 200 * 0.08;
            n.vx += (dx / dist) * force;
            n.vy += (dy / dist) * force;
          }
          // Spring back to base
          n.vx += (n.baseX - n.x) * 0.0008;
          n.vy += (n.baseY - n.y) * 0.0008;
          // Damping
          n.vx *= 0.98;
          n.vy *= 0.98;
        }
      }

      // Draw connections with Bézier curves for organic feel
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < connectDist) {
            const alpha = (1 - dist / connectDist) * (dark ? 0.12 : 0.15);
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            const cx = (a.x + b.x) / 2 + (Math.sin(frame * 0.01 + i) * dist * 0.08);
            const cy = (a.y + b.y) / 2 + (Math.cos(frame * 0.01 + j) * dist * 0.08);
            ctx.quadraticCurveTo(cx, cy, b.x, b.y);
            ctx.strokeStyle = dark ? `rgba(255,255,255,${alpha})` : `rgba(10,10,10,${alpha})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (const n of nodes) {
        if (!reduced) {
          n.x += n.vx;
          n.y += n.vy;
          n.pulse += n.pulseSpeed;

          // Wrap around
          if (n.x < -20) { n.x = w + 20; n.baseX = n.x; }
          if (n.x > w + 20) { n.x = -20; n.baseX = n.x; }
          if (n.y < -20) { n.y = h + 20; n.baseY = n.y; }
          if (n.y > h + 20) { n.y = -20; n.baseY = n.y; }
        }

        const pulseR = n.radius + Math.sin(n.pulse) * 0.35;
        const alpha = 0.65 + Math.sin(n.pulse) * 0.25;

        ctx.beginPath();
        ctx.arc(n.x, n.y, pulseR, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.globalAlpha = alpha;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Soft halo for colored nodes
        if (n.color !== "#0a0a0a" && n.color !== "#ffffff") {
          ctx.beginPath();
          ctx.arc(n.x, n.y, pulseR * 4, 0, Math.PI * 2);
          const grad = ctx.createRadialGradient(n.x, n.y, pulseR, n.x, n.y, pulseR * 4);
          const base = dark ? "255,255,255" : n.color.replace("#", "").match(/.{2}/g)?.map(x => parseInt(x, 16)).join(",") ?? "10,10,10";
          grad.addColorStop(0, `rgba(${base},${dark ? 0.08 : 0.18})`);
          grad.addColorStop(1, `rgba(${base},0)`);
          ctx.fillStyle = grad;
          ctx.fill();
        }
      }

      // Shooting stars
      frame++;
      if (!reduced && frame % 180 === 0 && nodes.length > 2) {
        const a = nodes[Math.floor(Math.random() * nodes.length)];
        const b = nodes[Math.floor(Math.random() * nodes.length)];
        if (a !== b) {
          const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          grad.addColorStop(0, "rgba(255,218,110,0)");
          grad.addColorStop(0.5, dark ? "rgba(255,218,110,0.25)" : "rgba(255,218,110,0.35)");
          grad.addColorStop(1, "rgba(255,218,110,0)");
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      rafRef.current = requestAnimationFrame(draw);
    }

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", resize);
      canvas.parentElement?.removeEventListener("mousemove", onMouseMove);
      canvas.parentElement?.removeEventListener("mouseleave", onMouseLeave);
      cancelAnimationFrame(rafRef.current);
    };
  }, [dark]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
    />
  );
}
