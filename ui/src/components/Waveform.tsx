interface WaveformProps {
  level: number;
  active: boolean;
  bars?: number;
}

const capped = (value: number) => Math.max(0, Math.min(1, value));

export function Waveform({ level, active, bars = 40 }: WaveformProps) {
  const value = capped(level);

  return (
    <div
      className="flex h-10 items-center justify-center gap-[3px]"
      aria-hidden="true"
      data-active={active}
    >
      {Array.from({ length: bars }).map((_, index) => {
        const envelope = Math.sin((index / Math.max(1, bars - 1)) * Math.PI);
        const seed = Math.abs(Math.sin(index * 12.9898) * 43758.5453) % 1;
        const height = active
          ? 4 + envelope * (6 + value * 52) * (0.45 + seed * 0.55)
          : 3 + seed * 3;
        return (
          <span
            key={index}
            className="w-[3px] rounded-full transition-[height,background-color] duration-150"
            style={{
              height: `${height.toFixed(1)}px`,
              backgroundColor: active ? "var(--vy-accent-500)" : "var(--vy-silver-500)",
              opacity: active ? 0.9 : 0.35,
            }}
          />
        );
      })}
    </div>
  );
}
