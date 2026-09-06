# Architecture

<!-- onboarding-surface:begin codemap -->
| module | what it does | grep for |
| --- | --- | --- |
| a2a_counterpart | Agent-to-Agent counterpart server implementation | grep `a2a_counterpart` |
| apps-script-surface | Google Apps Script UI renderer and state handling | grep `apps-script-surface` |
| benchmarks | Performance and quality benchmark suites | grep `benchmarks` |
| cloud-run-renderer | Cloud Run HTTP server rendering service | grep `cloud-run-renderer` |
| components | Declarative catalog components and visual definitions | grep `components` |
| examples | Demonstration scripts and usage examples | grep `examples` |
| googlechat | Google Chat integration adapters and surfaces | grep `googlechat` |
| knowledge-catalogue | Document and reference knowledge definitions | grep `knowledge-catalogue` |
| molecules | Higher-order compound UI components built from atoms | grep `molecules` |
| renderers | Target surface renderers and layout generation logic | grep `renderers` |
| scripts | Generation, compilation, and utility scripts | grep `scripts` |
| spec | Formal format schemas and contract specifications | grep `spec` |
| src | Core shared source logic | grep `src` |
| tests | Python verification suite and manifest audits | grep `tests` |
| tests-js | JavaScript and Node environment parity tests | grep `tests-js` |
<!-- onboarding-surface:end codemap -->

<!-- onboarding-surface:begin landmines -->
- Never perform improvised deployment sequences like raw `clasp push` or ad-hoc regeneration chains; every operation must be declared in `project.yaml` and executed via `ops/ops.py` *(source: CLAUDE.md)*.
- Renderer code in `.gs` files is the absolute ground truth over documentation; if `atoms/schema.yaml` and a renderer disagree on field shape, the renderer wins *(source: AGENTS.md)*.
- Standalone clones are incomplete; `ops/`, `thoughts/`, `a2uithoughts.md`, and `improve.yaml` are untracked symlinks pointing to sibling private repository `a2ui-private` *(source: AGENTS.md)*.
- Never hand-craft or copy encoded `?p=` payload URLs across surfaces; emit them solely through `scripts/make_url.py` *(source: CLAUDE.md)*.
- Nothing new may be published to public surfaces without Curtis's explicit per-artifact opt-in in `project.yaml` under `policy.published`, and preview atoms must retain `stage: preview` *(source: CLAUDE.md)*.
- MCP verbs must be explicitly registered in both `mcp-worker/src/tools.js` and `A2UIState.html`'s `MCP_VERBS` allowlist; missing entries cause instant silent UI failures *(source: CLAUDE.md)*.
- Any deliberate change to `tools/list` requires updating the parity suite in the same commit, otherwise live-vs-local deploy gates deadlock *(source: CLAUDE.md)*.
- Do not edit training prompts directly; prompts are generated from `spec/training-md-v0.1.md` via `gen_training_prompt.py`, and parity is enforced between `scripts/parse_training_md.py` and `training_parser.gs` *(source: CLAUDE.md)*.
- Deployed does not mean reachable: always verify on the live surface (via tools such as `worker-verify` or `gas-verify`) rather than assuming a passing build or deploy reached users *(source: CLAUDE.md)*.
<!-- onboarding-surface:end landmines -->
