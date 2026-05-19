/**
 * Per-challenge in-browser runner config.
 *
 * Each challenge declares:
 *  - editable: files the learner can change (shown in Monaco tabs)
 *  - readonly: support files loaded into Pyodide but not editable
 *               (test files, models, fixtures — context the tests need)
 *  - pytestArgs: passed to pytest.main(...) — usually a list of test paths
 *  - mode: 'pyodide' (Monaco + pytest) or 'reading' (read-only code preview)
 *
 * Files are still fetched from raw.githubusercontent.com on `repo_branch`
 * (template repo holds the canonical content), but the learner never
 * sees GitHub once they're in the runner.
 */

export type ChallengeRunnerConfig =
  | {
      mode: "pyodide";
      editable: string[];
      readonly: string[];
      pytestArgs: string[];
    }
  | {
      mode: "reading";
      readonly: string[];
    };

export const CHALLENGE_CONFIG: Record<string, ChallengeRunnerConfig> = {
  "fastapi-commerce-run-and-explore": {
    mode: "reading",
    readonly: ["README.md", "app/main.py", "tests/test_orders.py"],
  },
  "fastapi-commerce-fix-failing-test": {
    mode: "pyodide",
    editable: ["app/orders.py"],
    readonly: [
      "app/__init__.py",
      "app/coupons.py",
      "app/models.py",
      "tests/__init__.py",
      "tests/conftest.py",
      "tests/test_orders.py",
    ],
    pytestArgs: ["-v", "tests/test_orders.py"],
  },
  "fastapi-commerce-reject-invalid-coupons": {
    mode: "pyodide",
    editable: ["app/coupons.py", "app/main.py", "tests/test_coupons.py"],
    readonly: [
      "app/__init__.py",
      "app/models.py",
      "app/orders.py",
      "tests/__init__.py",
      "tests/conftest.py",
      "tests/test_orders.py",
    ],
    pytestArgs: ["-v"],
  },
};
