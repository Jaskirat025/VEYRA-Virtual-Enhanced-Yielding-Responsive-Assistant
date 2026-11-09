import { useEffect, useRef } from "react";
import type { OrbState } from "../lib/types";

interface OrbProps {
  state: OrbState;
  level: number;
  lowPower?: boolean;
  size?: number;
}

function readToken(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function withAlpha(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  if (value.length !== 6) return `rgba(255, 90, 31, ${alpha})`;
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

export function Orb({ state, level, lowPower = false, size = 280 }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef(state);
  const levelRef = useRef(level);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  useEffect(() => {
    levelRef.current = level;
  }, [level]);

  useEffect(() => {
    if (lowPower) return;
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * ratio;
    canvas.height = size * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    const silver = readToken("--vy-silver-300", "#c5cbd0");
    const bright = readToken("--vy-silver-100", "#e4e8eb");
    const accent = readToken("--vy-accent-500", "#ff5a1f");
    const dark = readToken("--vy-gunmetal-900", "#161c1f");

    let frame = 0;
    const started = performance.now();

    const draw = (now: number) => {
      const time = now - started;
      const center = size / 2;
      const base = size * 0.24;
      const current = stateRef.current;
      const audio = levelRef.current;

      context.clearRect(0, 0, size, size);

      let colour = silver;
      let radius = base * (1 + 0.02 * Math.sin(time / 1400));
      let alpha = 0.92;

      if (current === "listening") {
        colour = accent;
        radius = base * (1 + 0.035 * Math.sin(time / 220));
      } else if (current === "thinking") {
        colour = bright;
        radius = base * 0.97;
      } else if (current === "speaking") {
        colour = accent;
        radius = base * (1 + 0.12 * audio + 0.025 * Math.sin(time / 120));
      } else if (current === "error") {
        colour = accent;
        alpha = 0.55 + 0.45 * Math.abs(Math.sin(time / 110));
      }

      const glow = context.createRadialGradient(
        center,
        center,
        radius * 0.15,
        center,
        center,
        radius * 2.1,
      );
      glow.addColorStop(0, withAlpha(colour, 0.2 * alpha));
      glow.addColorStop(1, withAlpha(colour, 0));
      context.fillStyle = glow;
      context.beginPath();
      context.arc(center, center, radius * 2.1, 0, Math.PI * 2);
      context.fill();

      if (current === "listening" || current === "thinking" || current === "speaking") {
        const rings = current === "listening" ? 3 : 2;
        for (let ring = 0; ring < rings; ring += 1) {
          const phase = (time / (current === "thinking" ? 2400 : 1600) + ring / rings) % 1;
          const ringRadius = radius * (1.15 + phase * 0.75);
          context.strokeStyle = withAlpha(colour, 0.28 * (1 - phase));
          context.lineWidth = 1;
          context.beginPath();
          context.arc(center, center, ringRadius, 0, Math.PI * 2);
          context.stroke();
        }
      }

      if (current === "thinking") {
        for (let segment = 0; segment < 3; segment += 1) {
          const start = time / (900 + segment * 260) + (segment * Math.PI * 2) / 3;
          context.strokeStyle = withAlpha(accent, 0.55);
          context.lineWidth = 2;
          context.beginPath();
          context.arc(center, center, radius * 1.28, start, start + 0.55);
          context.stroke();
        }
      }

      const core = context.createRadialGradient(
        center - radius * 0.28,
        center - radius * 0.32,
        radius * 0.08,
        center,
        center,
        radius,
      );
      core.addColorStop(0, bright);
      core.addColorStop(0.52, colour);
      core.addColorStop(1, dark);

      context.globalAlpha = alpha;
      context.fillStyle = core;
      context.beginPath();
      const points = 72;
      for (let index = 0; index <= points; index += 1) {
        const angle = (index / points) * Math.PI * 2;
        const wobble =
          current === "speaking"
            ? 1 + (0.045 + 0.16 * audio) * Math.sin(angle * 5 + time / 130)
            : 1;
        const x = center + Math.cos(angle) * radius * wobble;
        const y = center + Math.sin(angle) * radius * wobble;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      }
      context.closePath();
      context.fill();

      context.globalAlpha = 1;
      context.strokeStyle = withAlpha(silver, 0.28);
      context.lineWidth = 1;
      context.beginPath();
      context.arc(center, center, radius * 1.02, 0, Math.PI * 2);
      context.stroke();

      frame = requestAnimationFrame(draw);
    };

    const onVisibility = () => {
      cancelAnimationFrame(frame);
      if (!document.hidden) frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [lowPower, size]);

  if (lowPower) {
    return (
      <div
        aria-hidden="true"
        style={{ width: size, height: size }}
        className="flex items-center justify-center"
      >
        <div
          className="rounded-full"
          style={{
            width: size * 0.42,
            height: size * 0.42,
            background: `radial-gradient(circle at 35% 30%, var(--vy-silver-100), ${
              state === "listening" || state === "speaking"
                ? "var(--vy-accent-500)"
                : "var(--vy-silver-500)"
            } 60%, var(--vy-gunmetal-900))`,
            boxShadow: "inset 0 0 0 1px var(--vy-line-strong)",
          }}
        />
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ width: size, height: size }}
      className="select-none"
    />
  );
}
