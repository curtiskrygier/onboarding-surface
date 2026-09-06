# Architecture

<!-- onboarding-surface:begin codemap -->
| module | what it does | grep for |
| --- | --- | --- |
| a2a_counterpart | Entrypoint and multi-turn derived state adapter for A2A protocols | `main.py` |
| apps-script-surface | Google Apps Script surface renderer implementation and transport maps | `MCP_VERBS` |
| benchmarks | Benchmark suites for scoring system dimensions | `benchmarks` |
| cloud-run-renderer | Cloud Run server implementation for hosting renderer services | `server.py` |
| components | UI component vocabulary definitions and building blocks | `components` |
| examples | Usage examples showing composed agent payloads | `examples` |
| googlechat | Google Chat surface adapters and integrations | `googlechat` |
| knowledge-catalogue | Documented vocabulary, patterns, and catalogue metadata | `knowledge-catalogue` |
| molecules | Compound structures composed from baseline atomic UI units | `molecules` |
| renderers | Target rendering engines converting atomic payloads to UI | `renderers` |
| scripts | Utility tooling for generating prompts, parsing markdown, and URL encoding | `make_url` |
| spec | Domain contracts and specifications including training markdown | `training-md` |
| src | Core runtime source code and application logic | `src` |
| tests | Python pytest suite covering manifest rules, staging, and parsers | `test_project_manifest` |
| tests-js | JavaScript-based test suites and parity checks | `tests-js` |
<!-- onboarding-surface:end codemap -->

<!-- onboarding-surface:begin landmines -->
- Ad-hoc commands or raw execution (such as raw `clasp push`, raw `clasp deploy`, or improvised regeneration chains) are strictly forbidden; every command must be declared in `project.yaml` and executed via `ops.py run <process>`. *(source: authored)*
- When `atoms/schema.yaml` text and a renderer `.gs` file disagree regarding a field's shape, the renderer source code is ground truth (e.g. `spring_nodes` edges take `{from, to}` node IDs, not documented `{a, b}` pairs). *(source: authored)*
- Nothing new is published to public surfaces without explicit per-artifact opt-in in `project.yaml` (`policy.published`, `published_prompts`), which is enforced by tests. *(source: authored)*
- New dev-first atoms must start with `stage: preview`; preview atoms are filtered out of public releases until explicitly promoted by removing the stage line. *(source: authored)*
- Private tier assets (`ops/`, `**/Code.private.gs`, `.clasp.json`) must never be committed; the manifest audit fails the build if they are tracked. *(source: authored)*
- Encoded payload `?p=` URLs must never be hand-typed or copied between surfaces; they must only be generated via `scripts/make_url.py`. *(source: authored)*
- In Apps Script, the stable `/exec` URL must be injected using `_getWebAppUrl()` via template at serve time rather than relying on `window.location`. *(source: authored)*
- A wired surface's `mcp:<verb>` action fails immediately and silently unless both `mcp-worker/src/tools.js` and `apps-script-surface/gas-wired-renderer/A2UIState.html`'s `MCP_VERBS` allowlist are kept in manual sync. *(source: authored)*
- Deployed does not mean reachable: do not trust deploy success messages without verifying the live surface directly via tools like `worker-verify` or `gas-verify`. *(source: authored)*
- Any deliberate modification to `tools/list` requires updating the parity suite in the same commit, or the deployment gate will deadlock. *(source: authored)*
- Do not attempt a third fix after two consecutive failures with the same symptom; stop and report observations. *(source: authored)*
<!-- onboarding-surface:end landmines -->
