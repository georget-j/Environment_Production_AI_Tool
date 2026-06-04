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

import { useMemo, useState } from "react";

import { AnnotatedFrames } from "@/components/widgets/annotated-frames";
import { Button } from "@/components/ui/button";
import { CodeStepper } from "@/components/widgets/code-stepper";
import { framesFromWidgetConfig } from "@/lib/play-adapters";

// M6 — code-stepper keeps its bespoke renderer; every other widget kind
// is normalised to AnnotatedFrame[] via play-adapters.ts and rendered by
// the generic <AnnotatedFrames> widget. Zero "coming soon" stubs in prod.

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

  const isCodeStepper = widgetKind === "code-stepper";
  const adapted = useMemo(
    () =>
      isCodeStepper
        ? { title: undefined, frames: [] }
        : framesFromWidgetConfig(widgetKind, widgetConfig),
    [isCodeStepper, widgetKind, widgetConfig],
  );
  const hasFrames = !isCodeStepper && adapted.frames.length > 0;

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
      {isCodeStepper && (
        <CodeStepper
          config={
            widgetConfig as unknown as Parameters<
              typeof CodeStepper
            >[0]["config"]
          }
          onAllStepsViewed={() => setUnlocked(true)}
        />
      )}

      {!isCodeStepper && hasFrames && (
        <AnnotatedFrames
          title={adapted.title}
          frames={adapted.frames}
          onAllStepsViewed={() => setUnlocked(true)}
        />
      )}

      {!isCodeStepper && !hasFrames && (
        <div className="rounded-md border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground">
          This Play widget doesn&apos;t have any frames authored yet — you can
          mark this stage complete and continue.
        </div>
      )}

      <div className="flex justify-end">
        <Button
          onClick={complete}
          disabled={
            busy || (isCodeStepper && !unlocked) || (hasFrames && !unlocked)
          }
        >
          {busy
            ? "…"
            : (isCodeStepper || hasFrames) && !unlocked
              ? "Step through first"
              : "Mark Play complete → Check"}
        </Button>
      </div>
    </div>
  );
}
