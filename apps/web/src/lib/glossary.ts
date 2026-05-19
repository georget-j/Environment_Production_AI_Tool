/**
 * Plain-English definitions of jargon that appears in the UI.
 *
 * The <Glossary term="..."> component wraps a word in an underline +
 * hover/tap tooltip that reads from this dictionary. Keep the term key
 * lowercase; the wrapper does case-insensitive lookup.
 */

export type GlossaryEntry = {
  term: string;
  short: string; // one sentence, max ~140 chars
  more?: string; // optional follow-on sentence for the curious
};

export const GLOSSARY: Record<string, GlossaryEntry> = {
  pytest: {
    term: "pytest",
    short: "Python's most popular test runner — it executes each function whose name starts with test_ and reports pass/fail.",
    more: "We run pytest inside your browser (no install needed) every time you click Run tests.",
  },
  test: {
    term: "test",
    short: "A small Python function whose only job is to call your code and check the result against an expected value.",
    more: "If the check passes, the test passes. If it fails, you'll see exactly what went wrong.",
  },
  assertion: {
    term: "assertion",
    short: "A statement starting with `assert` that says 'this must be true; if it isn't, fail the test.'",
    more: "Example: `assert total == 3350` means 'the total must be exactly 3350 cents.'",
  },
  function: {
    term: "function",
    short: "A named block of code that takes inputs, runs some logic, and returns a result.",
  },
  traceback: {
    term: "traceback",
    short: "The list of file paths and line numbers that pytest prints when something blows up — it's a trail of breadcrumbs from where the error happened back through the calls that led there.",
  },
  "exit code": {
    term: "exit code",
    short: "A single number a program returns when it finishes. 0 means 'everything passed'; anything else means 'something went wrong.'",
  },
  fixture: {
    term: "fixture",
    short: "A pytest helper that prepares test data — e.g. seeding two products before a test about order totals runs.",
  },
  submission: {
    term: "submission",
    short: "A snapshot of your code being recorded as your answer to this challenge. We store the passing test output and run an AI review on it.",
  },
  pyodide: {
    term: "Pyodide",
    short: "Python compiled to WebAssembly. It runs entirely inside your browser, so we never send your code to a server to execute it.",
  },
  hint: {
    term: "hint",
    short: "How specific you want the mentor's help to be. Level 1 asks you a question. Level 2 points at a file. Level 3 sketches pseudocode.",
  },
};

export function lookup(term: string): GlossaryEntry | undefined {
  return GLOSSARY[term.toLowerCase()];
}
