"use client";

import { useEffect, useId, useRef, useState } from "react";
import { lookup, type GlossaryEntry } from "@/lib/glossary";
import { cn } from "@/lib/utils";

type Props = {
  /** Lowercase term key, e.g. "pytest". */
  term: string;
  /** Optional display text — defaults to the term verbatim. */
  children?: React.ReactNode;
  className?: string;
};

/**
 * Inline glossary trigger. Wraps a piece of text in a dashed underline;
 * clicking or hovering reveals a definition popover from `lib/glossary.ts`.
 *
 * Falls back to plain text when the term isn't in the dictionary so this
 * is safe to sprinkle anywhere.
 */
export function Glossary({ term, children, className }: Props) {
  const entry = lookup(term);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement | null>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!entry) {
    return <span className={className}>{children ?? term}</span>;
  }

  return (
    <span className="relative inline-block" ref={wrapperRef}>
      <button
        type="button"
        aria-describedby={open ? popoverId : undefined}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        className={cn(
          "cursor-help border-b border-dashed border-current decoration-dotted underline-offset-2 hover:text-foreground",
          className,
        )}
      >
        {children ?? entry.term}
      </button>
      {open && <Popover id={popoverId} entry={entry} onClose={() => setOpen(false)} />}
    </span>
  );
}

function Popover({
  id,
  entry,
  onClose,
}: {
  id: string;
  entry: GlossaryEntry;
  onClose: () => void;
}) {
  return (
    <span
      id={id}
      role="tooltip"
      onMouseLeave={onClose}
      className="absolute left-0 top-full z-50 mt-1 w-72 rounded-md border border-border bg-white p-3 text-xs leading-relaxed text-foreground shadow-lg"
    >
      <span className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
        {entry.term}
      </span>
      <span className="block text-foreground">{entry.short}</span>
      {entry.more && (
        <span className="mt-1 block text-muted-foreground">{entry.more}</span>
      )}
    </span>
  );
}
