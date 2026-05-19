"use client";

import { Fragment } from "react";

/**
 * Render a mentor message with inline jump-to-code buttons where it mentions
 * a file path (e.g. "app/orders.py") or path + line (e.g. "app/orders.py:24").
 *
 * Everything else is preserved verbatim, with line breaks kept (whitespace-
 * pre-wrap). Backticks around a file reference are also recognised.
 */

// app/orders.py     OR     app/orders.py:24     OR     `app/orders.py:24`
// Also tests/foo.py, tests/foo.py:N. Capture file + optional line.
const FILE_REF_RE = /`?((?:app|tests)\/[\w./-]+\.py)(?::(\d+))?`?/g;

type Props = {
  text: string;
  onJumpToCode?: (file: string, line: number | null) => void;
};

export function MentorMessage({ text, onJumpToCode }: Props) {
  const parts: Array<{ kind: "text"; value: string } | { kind: "ref"; file: string; line: number | null }> = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  // Reset regex state (it's stateful when used with /g).
  FILE_REF_RE.lastIndex = 0;
  while ((match = FILE_REF_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ kind: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({
      kind: "ref",
      file: match[1],
      line: match[2] ? parseInt(match[2], 10) : null,
    });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ kind: "text", value: text.slice(lastIndex) });
  }

  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed">
      {parts.map((part, i) =>
        part.kind === "text" ? (
          <Fragment key={i}>{part.value}</Fragment>
        ) : onJumpToCode ? (
          <button
            key={i}
            type="button"
            onClick={() => onJumpToCode(part.file, part.line)}
            className="mx-0.5 inline rounded border border-blue-200 bg-blue-50 px-1 py-0.5 font-mono text-xs text-blue-700 hover:bg-blue-100"
            title="Click to jump to this file in the editor"
          >
            {part.file}
            {part.line !== null ? `:${part.line}` : ""}
          </button>
        ) : (
          <code key={i} className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
            {part.file}
            {part.line !== null ? `:${part.line}` : ""}
          </code>
        ),
      )}
    </p>
  );
}
