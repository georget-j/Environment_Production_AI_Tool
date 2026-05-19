import { z } from "zod";

/**
 * Structured PR-style review schema.
 *
 * Mirrored from packages/shared/src/review.ts and apps/api/app/ai/review.py.
 * Inlined into apps/web because Vercel's monorepo workspace install path
 * is fragile; keep the three copies in sync until that's resolved.
 */

export const ReviewIssueSchema = z.object({
  severity: z.enum(["minor", "major", "critical"]),
  title: z.string(),
  suggestion: z.string(),
});

export const PrReviewSchema = z.object({
  passed: z.boolean(),
  score: z.number().int().min(0).max(100),
  summary: z.string(),
  strengths: z.array(z.string()),
  issues: z.array(ReviewIssueSchema),
  required_fixes: z.array(z.string()),
  skills_practiced: z.array(z.string()),
  next_recommended_challenge: z.string().nullable(),
});

export type ReviewIssue = z.infer<typeof ReviewIssueSchema>;
export type PrReview = z.infer<typeof PrReviewSchema>;
