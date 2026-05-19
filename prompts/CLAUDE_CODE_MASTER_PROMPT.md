# Claude Code Master Prompt

Use this prompt when starting a new Claude Code session.

```text
We are building ProdReady AI, an AI-powered production coding simulator.

Read CLAUDE.md first, then read the plans folder in order.

Your goal is to build the MVP, not the final platform.

Key constraints:
- Do not build a custom cloud IDE.
- Do not run arbitrary user code on our infrastructure.
- Use GitHub template repos, devcontainers/Codespaces, and GitHub Actions for the first environment strategy.
- Build a narrow Backend Production Developer track first.
- AI mentor guides and reviews; automated checks decide pass/fail.
- Keep implementation simple, typed, testable, and modular.

Start by implementing the next unchecked item in plans/09_CLAUDE_CODE_TASK_LIST.md.
Before editing, summarize the files you will touch.
After editing, run relevant tests/lint if available.
Update docs if behavior changes.
```
