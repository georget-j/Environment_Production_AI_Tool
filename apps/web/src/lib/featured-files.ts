/**
 * Per-challenge file previews on the challenge page.
 *
 * Map a challenge slug → list of file paths (relative to the template repo root).
 * The CodePreview component fetches each one from raw.githubusercontent.com
 * on the challenge's repo_branch. Ordering matters — first file is opened
 * by default.
 *
 * Eventually this should live in the challenges table (or challenge YAML)
 * so non-engineers can edit it; for the MVP it's hardcoded.
 */

export const FEATURED_FILES: Record<string, string[]> = {
  "fastapi-commerce-run-and-explore": [
    "README.md",
    "app/main.py",
    "tests/test_orders.py",
  ],
  "fastapi-commerce-fix-failing-test": [
    "tests/test_orders.py",
    "app/orders.py",
    "app/models.py",
  ],
  "fastapi-commerce-reject-invalid-coupons": [
    "app/coupons.py",
    "app/main.py",
    "tests/test_coupons.py",
  ],
};
