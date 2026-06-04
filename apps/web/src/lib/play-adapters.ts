/**
 * Play widget adapters (M6).
 *
 * Each adapter takes the authored JSON for a specific widget_kind and
 * normalises it into the generic AnnotatedFrame[] shape used by the
 * AnnotatedFrames widget. Authored content stays the way it was; the
 * runtime understands every kind without needing a bespoke renderer per
 * kind.
 *
 * A few kinds — code-stepper most importantly — still have their own
 * renderers; this file only feeds the generic fallback. The dispatcher
 * in concept-play.tsx picks which path to take.
 */

import type { AnnotatedFrame } from "@/components/widgets/annotated-frames";

type AnyRecord = Record<string, unknown>;

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}
function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}
function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as AnyRecord)
    : {};
}

/** Memory-model-viewer — each frame has {caption, stack[], heap[]}. We
 * render stack + heap as a small ASCII block so the visual changes
 * between frames in a way that makes aliasing legible. */
function memoryModelAdapter(config: AnyRecord): AnnotatedFrame[] {
  const frames = asArray(config.frames);
  return frames.map((raw) => {
    const f = asRecord(raw);
    const stack = asArray(f.stack)
      .map((s) => {
        const sf = asRecord(s);
        const name = asString(sf.name);
        const vars = asRecord(sf.vars);
        const varLines = Object.entries(vars)
          .map(([k, v]) => `    ${k} = ${String(v)}`)
          .join("\n");
        return varLines ? `frame: ${name}\n${varLines}` : `frame: ${name}`;
      })
      .join("\n  ─\n");
    const heap = asArray(f.heap)
      .map((h) => {
        const hf = asRecord(h);
        const id = asString(hf.id);
        const value = asString(hf.value);
        const labels = asArray(hf.labels).map(asString).filter(Boolean);
        const labelsStr = labels.length ? `   ← ${labels.join(", ")}` : "";
        return `${id}: ${value}${labelsStr}`;
      })
      .join("\n");
    const visual =
      stack || heap
        ? [stack && `STACK\n${stack}`, heap && `\nHEAP\n${heap}`]
            .filter(Boolean)
            .join("\n")
        : undefined;
    return {
      caption_md: asString(f.caption) || "(no caption)",
      visual,
    };
  });
}

/** Call-stack-visualiser — generic shape supports either an authored
 * `frames` array (preferred) or a `calls` sequence built up over time. */
function callStackAdapter(config: AnyRecord): AnnotatedFrame[] {
  const frames = asArray(config.frames);
  if (frames.length > 0) {
    return frames.map((raw) => {
      const f = asRecord(raw);
      const stack = asArray(f.stack).map((s) => {
        const sf = asRecord(s);
        return `▶ ${asString(sf.label) || asString(sf.name)}${
          sf.args ? ` (${JSON.stringify(sf.args)})` : ""
        }${sf.returns !== undefined ? ` → ${JSON.stringify(sf.returns)}` : ""}`;
      });
      const visual = stack.length
        ? "CALL STACK (bottom → top)\n" + stack.join("\n")
        : undefined;
      return {
        caption_md: asString(f.caption) || "(no caption)",
        visual,
      };
    });
  }
  // Synthesize frames from a `calls` list — handy when only a tree is given.
  const calls = asArray(config.calls);
  return calls.map((raw, idx) => {
    const c = asRecord(raw);
    return {
      caption_md:
        asString(c.caption) ||
        `Call ${idx + 1}: ${asString(c.label) || "frame"}`,
    };
  });
}

/** State-machine-animator — each frame is `{caption, active_state,
 * edge_taken?}`. We render the state set with the active one highlighted. */
function stateMachineAdapter(config: AnyRecord): AnnotatedFrame[] {
  const states = asArray(config.states).map(asString).filter(Boolean);
  const frames = asArray(config.frames);
  return frames.map((raw) => {
    const f = asRecord(raw);
    const active = asString(f.active_state);
    const edge = asString(f.edge_taken);
    const stateLine = states
      .map((s) => (s === active ? `▶ ${s}` : `  ${s}`))
      .join("\n");
    const visual = stateLine
      ? `STATES\n${stateLine}${edge ? `\n\nTransition: ${edge}` : ""}`
      : undefined;
    return {
      caption_md: asString(f.caption) || "(no caption)",
      visual,
    };
  });
}

/** Complexity-plotter — each frame is `{caption, n, ops_o_n,
 * ops_o_n_squared, ...}`. Render as a small ASCII table. */
function complexityPlotterAdapter(config: AnyRecord): AnnotatedFrame[] {
  const frames = asArray(config.frames);
  return frames.map((raw) => {
    const f = asRecord(raw);
    // Pull every numeric "ops_..." field for the table.
    const rows = Object.entries(f)
      .filter(([k, v]) => k.startsWith("ops_") && typeof v === "number")
      .map(([k, v]) => `  ${k.replace("ops_", "")}: ${v}`);
    const n = f.n !== undefined ? `n = ${String(f.n)}` : null;
    const visual = rows.length
      ? [n, "ops:", ...rows].filter(Boolean).join("\n")
      : undefined;
    return {
      caption_md: asString(f.caption) || "(no caption)",
      visual,
    };
  });
}

/** Generic catch-all — used by `annotated-frames` widgets that author
 * directly in the target shape, and as the absolute fallback when a
 * widget_kind isn't recognised. */
function genericAdapter(config: AnyRecord): AnnotatedFrame[] {
  // Common shapes: `frames[]`, `steps[]`, or just nothing.
  const list = asArray(config.frames).length
    ? asArray(config.frames)
    : asArray(config.steps);
  if (!list.length) return [];
  return list.map((raw) => {
    const f = asRecord(raw);
    return {
      caption_md:
        asString(f.caption) || asString(f.caption_md) || "(no caption)",
      detail_md: asString(f.detail_md) || undefined,
      visual: asString(f.visual) || undefined,
      code: asString(f.code) || undefined,
    };
  });
}

export function framesFromWidgetConfig(
  widgetKind: string,
  config: Record<string, unknown>,
): { title: string | undefined; frames: AnnotatedFrame[] } {
  const cfg = (config ?? {}) as AnyRecord;
  const title = asString(cfg.title) || undefined;
  let frames: AnnotatedFrame[] = [];
  switch (widgetKind) {
    case "memory-model-viewer":
      frames = memoryModelAdapter(cfg);
      break;
    case "call-stack-visualiser":
      frames = callStackAdapter(cfg);
      break;
    case "state-machine-animator":
      frames = stateMachineAdapter(cfg);
      break;
    case "complexity-plotter":
      frames = complexityPlotterAdapter(cfg);
      break;
    case "annotated-frames":
    case "generic-slider-chart":
    default:
      frames = genericAdapter(cfg);
      break;
  }
  return { title, frames };
}
