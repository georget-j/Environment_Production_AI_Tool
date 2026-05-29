"use client";

/**
 * concept-play — host for the Play-stage widget.
 *
 * Dispatches on the concept's `play_widget_kind` to the correct widget
 * component. Each widget is purely declarative — it reads its JSON config
 * and renders the state-visible interaction. None of them execute code;
 * authors hand-roll the state transitions per Bret Victor's "See the
 * state" principle.
 *
 * Widget kinds shipping in CC.2:
 *   - code-stepper            (the default; line + state panel)
 *
 * Stubs shipping in CC.2 (full implementations in later sub-phases):
 *   - call-stack-visualiser
 *   - state-machine-animator
 *   - memory-model-viewer
 *   - complexity-plotter
 *   - generic-slider-chart
 */

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { CodeStepper } from "@/components/widgets/code-stepper";

const STUB_KIND_LABELS: Record<string, string> = {
  "call-stack-visualiser": "Call-stack visualiser",
  "state-machine-animator": "State-machine animator",
  "memory-model-viewer": "Memory-model viewer",
  "complexity-plotter": "Complexity plotter",
  "generic-slider-chart": "Slider + chart",
};

export function ConceptPlay({
  widgetKind,
  widgetConfig,
  onComplete,
}: {
  widgetKind: string;
  widgetConfig: Record<string, unknown>;
  onComplete: () => void | Promise<void>;
}) {
  const [unlocked, setUnlocked] = useState(false);
  const [busy, setBusy] = useState(false);

  async function complete() {
    setBusy(true);
    try {
      await onComplete();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {widgetKind === "code-stepper" && (
        <CodeStepper
          // The shape is validated by the widget itself; we hand it the
          // JSON the API delivered without forcing a runtime schema check
          // here. Type-checking happens against the public Config type.
          config={
            widgetConfig as unknown as Parameters<
              typeof CodeStepper
            >[0]["config"]
          }
          onAllStepsViewed={() => setUnlocked(true)}
        />
      )}

      {widgetKind !== "code-stepper" && (
        <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 text-sm">
          <p className="font-semibold">
            {STUB_KIND_LABELS[widgetKind] ?? widgetKind} — coming in a later CC
            sub-phase.
          </p>
          <p className="mt-1 text-muted-foreground">
            For now, this is a placeholder so the unit shell stays usable on
            every concept. The widget framework dispatch is wired — only this
            widget&apos;s implementation is deferred.
          </p>
        </div>
      )}

      <div className="flex justify-end">
        <Button
          onClick={complete}
          disabled={busy || (widgetKind === "code-stepper" && !unlocked)}
        >
          {busy
            ? "…"
            : widgetKind === "code-stepper" && !unlocked
              ? "Step through first"
              : "Mark Play complete → Check"}
        </Button>
      </div>
    </div>
  );
}
