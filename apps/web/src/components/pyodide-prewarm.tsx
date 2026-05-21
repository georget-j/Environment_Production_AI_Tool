"use client";

import { useEffect } from "react";
import { ensureMatplotlib, getPyodide } from "@/lib/pyodide";

type Props = {
  /** When set, prewarm the extras that track's lessons typically need. */
  trackSlug?: string;
};

/**
 * Kick off the (bare) Pyodide warm-up while the user is browsing a track
 * detail page. By the time they click into a lesson, the singleton is
 * already loading. Uses `requestIdleCallback` so we never compete with
 * the page's main thread; falls back to a short setTimeout on Safari.
 *
 * Quant track also warms matplotlib (~3MB additional download) so the
 * first chart-bearing lesson doesn't pay the full cost on click.
 */
export function PyodidePrewarm({ trackSlug }: Props = {}) {
  useEffect(() => {
    const w = window as Window & {
      requestIdleCallback?: (fn: () => void) => number;
    };
    const fire = () => {
      void (async () => {
        try {
          await getPyodide();
          if (trackSlug === "quant-programmer") {
            await ensureMatplotlib();
          }
        } catch {
          // Silent — the lesson page surfaces errors if the boot actually fails.
        }
      })();
    };
    if (typeof w.requestIdleCallback === "function") {
      w.requestIdleCallback(fire);
    } else {
      const id = window.setTimeout(fire, 200);
      return () => window.clearTimeout(id);
    }
  }, [trackSlug]);
  return null;
}
