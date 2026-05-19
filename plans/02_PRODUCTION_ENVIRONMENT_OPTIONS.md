# 02 — Production Environment Options

This is the most important technical decision.

The product needs realistic production environments, but building a secure multi-user cloud IDE and sandbox is expensive and risky. The MVP should emulate production workflow without overbuilding infrastructure.

## Recommended staged approach

### Stage 1 — MVP: GitHub-first workflow

Use:

- GitHub template repos
- devcontainer files
- Docker Compose
- GitHub Actions for validation
- Learner submits repo URL or commit SHA
- Platform pulls validation result or asks learner to paste output at first

This is the best MVP option because it teaches real production workflow while avoiding custom sandbox risk.

#### Pros

- Fastest to build
- Real Git/GitHub workflow
- Real CI/CD
- Real Docker/devcontainer setup
- Low infrastructure cost
- Easier to debug
- No need to execute arbitrary user code on our servers

#### Cons

- User needs GitHub account
- Less seamless than an embedded IDE
- Some users may struggle with setup
- Harder to control hidden tests unless using private validation infrastructure later

#### Best for

The first sellable MVP.

---

### Stage 2 — Polished MVP: GitHub Codespaces

Use:

- GitHub Codespaces
- devcontainers
- GitHub Actions
- “Open in Codespaces” buttons
- Template repos per challenge

GitHub Codespaces provides cloud-hosted development environments backed by containers/VMs, and devcontainers define the environment. This gives a much smoother learner experience than local setup.

#### Pros

- Very production-like
- Cloud-based
- No local dependency issues
- Great for Docker/devcontainer workflows
- Learners still use real GitHub flow

#### Cons

- Codespaces cost/quotas
- Requires GitHub account
- Platform has less direct control than own IDE
- B2B/education permissions may need thought

#### Best for

A polished V1 after the first MVP.

---

### Stage 3 — Embedded sandbox provider

Consider providers such as:

- CodeSandbox SDK
- E2B
- Modal Sandboxes
- StackBlitz WebContainers for Node-focused tracks

These let the platform create or manage isolated development/code execution environments more directly.

#### Pros

- Better integrated UX
- More platform control
- Easier to embed in product flow
- Can automate environment lifecycle

#### Cons

- More vendor dependency
- More cost complexity
- May not perfectly match production backend environments
- Security and abuse considerations still matter

#### Best for

Post-MVP once users are paying and environment friction is the top bottleneck.

---

### Stage 4 — Custom sandbox infrastructure

Use:

- Kubernetes jobs
- Docker containers
- gVisor/Kata Containers/Firecracker-style isolation
- per-submission ephemeral environments
- strict network/file/CPU/memory/time limits
- artifact collection

#### Pros

- Maximum control
- Can support hidden tests properly
- Can scale B2B validation
- Can support many languages/stacks

#### Cons

- Security risk
- High engineering effort
- Operational complexity
- Expensive to build before validation

#### Best for

After product-market validation or enterprise demand.

---

## Decision matrix

| Option | MVP speed | Realism | UX | Security burden | Cost risk | Recommendation |
|---|---:|---:|---:|---:|---:|---|
| Local Docker + GitHub Actions | High | High | Medium | Low | Low | Best first MVP |
| GitHub Codespaces | High | High | High | Low-Med | Med | Best polished V1 |
| CodeSandbox SDK | Medium | Med-High | High | Med | Med | Good later |
| E2B/Modal | Medium | High | High | Med | Med-High | Good for validation/sandbox layer |
| WebContainers | High for JS | Medium | High | Low-Med | Low-Med | Good for Node/JS track, not Python backend MVP |
| Custom Kubernetes/Firecracker | Low | Very High | High | Very High | High | Do not build first |

## Clear recommendation

### Start with GitHub template repos + devcontainer + GitHub Actions.

The product is about production workflow. GitHub, PRs, CI, branches, tests, and Docker are not a compromise — they are part of the learning value.

### Upgrade to Codespaces next.

Codespaces reduces local setup friction while preserving the real production workflow.

### Add sandbox providers later.

Only add embedded sandbox execution once you know users want the product and can identify the biggest friction point.
