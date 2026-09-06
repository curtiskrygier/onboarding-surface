# Architecture

<!-- onboarding-surface:begin codemap -->
| module | what it does | grep for |
| --- | --- | --- |
| a2a_counterpart | Agent-to-agent counterpart integration and entrypoint | grep `main` |
| apps-script-surface | Google Apps Script UI surfaces, state handling, and renderer templates | grep `MCP_VERBS` |
| benchmarks | Performance and compliance benchmarks | grep `benchmark` |
| cloud-run-renderer | Cloud Run server implementation for hosting the renderer | grep `server` |
| components | Composite UI component declarations | grep `components` |
| examples | Demonstration payloads and usage examples | grep `examples` |
| googlechat | Google Chat card interfaces and rendering adaptations | grep `googlechat` |
| knowledge-catalogue | Catalogue schemas and knowledge documentation | grep `catalogue` |
| molecules | Mid-level compound UI molecule definitions | grep `molecules` |
| renderers | Target platform UI renderer implementations | grep `renderers` |
| scripts | Utility generation, URL formatting, and validation scripts | grep `make_url` |
| spec | Domain specifications and training prompt contracts | grep `training-md` |
| src | Core library implementation source files | grep `src` |
| tests | Python verification suite testing manifests, staging, and parity | grep `test_staging` |
| tests-js | JavaScript and Node-based test suites | grep `test` |
<!-- onboarding-surface:end codemap -->

<!-- onboarding-surface:begin landmines -->
- Renderer source code is ground truth over schema documentation, meaning discrepancies in field shapes favour the renderer implementation. *(source: AGENTS.md)*
- Changes to `spec/` prompt contracts require re-running the prompt generation process to bump the handoff cache. *(source: CLAUDE.md)*
- Changes to atoms default to preview stage and are strictly prevented from public deployment until explicitly promoted and audited. *(source: CLAUDE.md)*
- Updates to tools require immediate parity suite updates within the same commit or the deployment gate will deadlock. *(source: CLAUDE.md)*
- Encoded payload URLs must always be emitted using `scripts/make_url.py` rather than typed or copied manually. *(source: CLAUDE.md)*
- Never diagnose a failure for a third time without stopping to report observations and ruled-out hypotheses. *(source: CLAUDE.md)*

*Some maintainer-only notes for this repo are kept out of the public docs.*
<!-- onboarding-surface:end landmines -->
