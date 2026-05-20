"use client";

import { useEffect, useState } from "react";

/**
 * Pick a numeric height based on a min-width media query. Returns `mobile`
 * below the breakpoint, `desktop` at or above it. Re-evaluates on resize
 * but only fires a state update when the answer actually changes.
 *
 * Default breakpoint = Tailwind's `md` (768px). Used to keep Monaco from
 * eating most of the viewport on phones.
 */
export function useResponsiveHeight(
  mobile: number,
  desktop: number,
  minWidthPx = 768,
): number {
  const [height, setHeight] = useState(desktop);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia(`(min-width: ${minWidthPx}px)`);
    const apply = () => setHeight(mql.matches ? desktop : mobile);
    apply();
    mql.addEventListener("change", apply);
    return () => mql.removeEventListener("change", apply);
  }, [mobile, desktop, minWidthPx]);
  return height;
}
