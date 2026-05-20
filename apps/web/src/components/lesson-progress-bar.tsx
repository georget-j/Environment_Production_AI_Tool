type Props = {
  position: number;
  total: number;
};

export function LessonProgressBar({ position, total }: Props) {
  if (total <= 1) return null;
  const pct = Math.max(0, Math.min(100, (position / total) * 100));
  return (
    <div
      role="progressbar"
      aria-valuenow={position}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label={`Lesson ${position} of ${total}`}
      className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        className="h-full bg-primary transition-[width] duration-300"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
