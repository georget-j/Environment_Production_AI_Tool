/**
 * Server-only fetchers for the concept atoms. Imports `apiFetch` which
 * pulls the supabase session from `next/headers` — that's why this file
 * is split from the client-safe `lib/concepts.ts`.
 *
 * Use these in server components (e.g. `app/concepts/[slug]/page.tsx`).
 * Do NOT import from a client component.
 */

import { apiFetch } from "@/lib/api";
import type { ConceptDetail, ConceptSummary } from "@/lib/concepts";

export async function fetchConcept(slug: string): Promise<ConceptDetail> {
  return apiFetch<ConceptDetail>(`/api/concepts/${slug}`, {
    requireAuth: true,
    revalidate: false,
  });
}

export async function listConcepts(): Promise<ConceptSummary[]> {
  return apiFetch<ConceptSummary[]>(`/api/concepts`, {
    requireAuth: true,
  });
}

/**
 * M9 — concept-mastery rollup for the authenticated user. Keyed by concept
 * slug. Concepts the learner hasn't touched are omitted (caller defaults
 * to "untouched"). Used by the concept-map UI to colour nodes.
 */
export type ConceptMasteryEntry = {
  mastered_at: string | null;
  status: "in_progress" | "mastered" | "needs_review";
  started: boolean;
  next_recall_due_at: string | null;
};

export async function fetchMyConceptMastery(): Promise<
  Record<string, ConceptMasteryEntry>
> {
  return apiFetch<Record<string, ConceptMasteryEntry>>(
    `/api/me/concept-mastery`,
    { requireAuth: true },
  );
}
