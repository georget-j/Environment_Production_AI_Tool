"use client";

import { useEffect } from "react";
import { getPyodide } from "@/lib/pyodide";

/**
 * Kick off the (bare) Pyodide warm-up while the user is browsing a track
 * detail page. By the time they click into a lesson, the singleton is
 * already loading. Uses `requestIdleCallback` so we never compete with
 * the page's main thread; falls back to a short setTimeout on Safari.
 */
export function PyodidePrewarm() {
  useEffect(() => {
    const w = window as Window & {
      requestIdleCallback?: (fn: () => void) => number;
    };
    const fire = () => {
      void getPyodide().catch(() => {
        // Silent — the lesson page will surface the error if it actually fails.
      });
    };
    if (typeof w.requestIdleCallback === "function") {
      w.requestIdleCallback(fire);
    } else {
      const id = window.setTimeout(fire, 200);
      return () => window.clearTimeout(id);
    }
  }, []);
  return null;
}
