/**
 * CLIENT-SAFE typed wrappers + types for the Mental Models concept-atom
 * endpoints. Mirrors apps/api/app/schemas.py (CC.1).
 *
 * NOTE: this file is imported by `components/concept-unit.tsx` which is
 * a client component. It must NOT import from `lib/api.ts` (which uses
 * `next/headers` for the server-side supabase client). Server-only
 * fetchers live in `lib/concepts-server.ts`.
 */

// ----------------------------------------------------------------------------
// Types — mirror Pydantic schemas in apps/api/app/schemas.py
// ----------------------------------------------------------------------------

export type ConceptMCQ = {
  q: string;
  options: string[];
  correct: number;
  why?: string;
};

export type ConceptStageProgress = {
  try_attempted_at: string | null;
  try_attempt_text: string | null;
  read_completed_at: string | null;
  play_completed_at: string | null;
  check_completed_at: string | null;
  apply_completed_at: string | null;
  reflect_completed_at: string | null;
  mastered_at: string | null;
  next_recall_due_at: string | null;
  recall_interval_days: number;
  recall_streak: number;
  status: "in_progress" | "mastered" | "needs_review";
};

export type ConceptSummary = {
  id: string;
  slug: string;
  layer: "universal" | "topic" | "applied";
  topic_slug: string | null;
  title: string;
  one_line: string;
  order_index: number;
};

export type ConceptDetail = ConceptSummary & {
  try_prompt_md: string;
  try_kind: "code" | "text-reasoning";
  try_expected_attempts_json: Array<{ pattern: string; callback_md: string }>;
  exposition_md: string;
  worked_example_md: string;
  play_widget_kind: string;
  play_widget_json: Record<string, unknown>;
  check_mcqs_json: ConceptMCQ[];
  apply_challenge_slug: string | null;
  reflect_question: string;
  reflect_rubric_json: Record<string, unknown>;
  recall_checks_json: Array<Record<string, unknown>>;
  prereqs: string[];
  progress: ConceptStageProgress | null;
};

export type StageCompleteResponse = {
  progress: ConceptStageProgress;
};

export type ReflectGradeResponse = {
  verdict: "complete" | "shallow";
  follow_up: string | null;
  rubric_hits: Record<string, unknown>;
  progress: ConceptStageProgress;
};

// ----------------------------------------------------------------------------
// Client-side mutations (called from concept-unit.tsx). These hit the API
// directly with the user's bearer token; mirror the pattern used by the
// existing challenge runner. Server-side fetchers (fetchConcept, listConcepts)
// live in `lib/concepts-server.ts` to keep this file client-safe.
// ----------------------------------------------------------------------------

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function authedPost<T>(
  accessToken: string,
  path: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

export async function recordTryAttempt(
  accessToken: string,
  slug: string,
  attemptText: string,
): Promise<StageCompleteResponse> {
  return authedPost(accessToken, `/api/concepts/${slug}/try`, {
    attempt_text: attemptText,
  });
}

export async function markStageComplete(
  accessToken: string,
  slug: string,
  stage: "read" | "play" | "check" | "apply" | "reflect",
): Promise<StageCompleteResponse> {
  return authedPost(
    accessToken,
    `/api/concepts/${slug}/stages/${stage}/complete`,
    {},
  );
}

export async function gradeReflect(
  accessToken: string,
  slug: string,
  explanation: string,
): Promise<ReflectGradeResponse> {
  return authedPost(accessToken, `/api/concepts/${slug}/reflect`, {
    explanation,
  });
}
