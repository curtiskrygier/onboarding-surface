# Architecture

<!-- onboarding-surface:begin codemap -->
![Architecture sketch](assets/onboarding/architecture-sketch.svg)

| module | what it does | grep for |
|---|---|---|
| serve | Exposes the pipeline as a stateless A2A service with remote skills | grep for skill dispatch in `serve/` |
| author | Runs the governed LLM step to produce prose and landmine records | grep for prompt invocation in `author/` |
| extract | Collects repository facts into `facts.json` offline or via GitHub | grep for facts extraction in `extract/` |
| draw | Produces deterministic D2 architecture sketches and repo-mark proposals | grep for D2 sketch generation in `draw/` |
| render | Formats repository facts and authored prose into standard markdown docs | grep for template rendering in `render/` |
| review | Provides a read-only human-in-the-loop review interface | grep for review UI logic in `review/` |
<!-- onboarding-surface:end codemap -->

<!-- onboarding-surface:begin landmines -->
None extracted. Sources checked: lint configs, revert history, review comments, agent docs.
<!-- onboarding-surface:end landmines -->
