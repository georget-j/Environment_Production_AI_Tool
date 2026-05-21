// Ambient types for picoc-js (no .d.ts shipped upstream).
// We only use runC; both stdout and errors come back through the callback.
declare module "picoc-js" {
  export function runC(code: string, consoleWrite: (s: string) => void): void;
}
