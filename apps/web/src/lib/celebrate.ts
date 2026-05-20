/**
 * Fire a single, modest confetti burst. No-op on the server.
 * The import is dynamic so canvas-confetti is only pulled into the chunk
 * that actually uses it.
 */
export async function celebrate(): Promise<void> {
  if (typeof window === "undefined") return;
  const { default: confetti } = await import("canvas-confetti");
  confetti({
    particleCount: 60,
    spread: 70,
    origin: { y: 0.6 },
    disableForReducedMotion: true,
  });
}
