import { createClient } from "@/lib/supabase/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

type FetchOptions = Omit<RequestInit, "cache"> & {
  requireAuth?: boolean;
  /** Seconds of edge-cache revalidation. Defaults to 30 for public reads,
   *  ignored for authenticated requests (no-store).
   *  Pass `false` to opt out of caching for a specific public read. */
  revalidate?: number | false;
};

export async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { requireAuth = false, revalidate, headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };
  Object.assign(finalHeaders, headers ?? {});

  if (requireAuth) {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      throw new Error("Not authenticated");
    }
    finalHeaders.Authorization = `Bearer ${session.access_token}`;
  }

  // Authenticated reads are per-user → no-store. Public reads default to
  // a 30s revalidate so listing pages don't refetch on every navigation.
  // Callers can override via `revalidate`.
  const noStore = requireAuth || revalidate === false;
  const seconds = typeof revalidate === "number" ? revalidate : 30;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    ...(noStore
      ? { cache: "no-store" as const }
      : { next: { revalidate: seconds } }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${path} → ${response.status}: ${body}`);
  }
  return (await response.json()) as T;
}

// --- shared types (mirror of apps/api/app/schemas.py) ---

export type TrackOut = {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  difficulty: string | null;
};

export type ModuleOut = {
  id: string;
  slug: string;
  title: string;
  order_index: number;
};

export type ChallengeSummary = {
  id: string;
  slug: string;
  title: string;
  order_index: number;
  is_free: boolean;
  skills: string[];
  module_id: string;
};

export type ChallengeNavRef = {
  slug: string;
  title: string;
};

export type ChallengeDetail = ChallengeSummary & {
  scenario: string;
  learner_goal: string;
  instructions: string;
  repo_template_url: string | null;
  repo_branch: string | null;
  validation_config_json: Record<string, unknown>;
  ai_rules_json: Record<string, unknown>;
  module: ModuleOut;
  previous: ChallengeNavRef | null;
  next: ChallengeNavRef | null;
  position_in_track: number;
  total_in_track: number;
};

export type TrackDetail = TrackOut & {
  modules: ModuleOut[];
  challenges: ChallengeSummary[];
};

export type ProgressOut = {
  id: string;
  challenge_id: string;
  status: "not_started" | "in_progress" | "completed";
  started_at: string | null;
  completed_at: string | null;
  attempts_count: number;
};

export type TrackProgressOut = {
  slug: string;
  title: string;
  description: string | null;
  difficulty: string | null;
  completed: number;
  total: number;
  latest_in_progress_slug: string | null;
};

export type ContinueRef = {
  track_slug: string;
  track_title: string;
  module_title: string;
  challenge_slug: string;
  challenge_title: string;
  position: number;
  total: number;
};

export type MeProgressOut = {
  tracks: TrackProgressOut[];
  continue_lesson: ContinueRef | null;
};

export type TrackProgressDetail = {
  completed_slugs: string[];
  in_progress_slugs: string[];
  next_unsolved_slug: string | null;
  completed: number;
  total: number;
  module_progress: Record<string, { completed: number; total: number }>;
};
