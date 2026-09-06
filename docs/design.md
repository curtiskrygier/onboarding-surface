# Design — service shape

Companion to `spec/onboarding-surface-v0.1.md` §11–12. This is the *how it runs*,
kept separate from the *what it produces*.

## Shape

A small Cloud Run service (same pattern as `maison`): a stateless HTTP handler
that runs the pipeline once per call.

```
request  ──▶  extract facts.json (deterministic)
         ──▶  if mode=full: one governed LLM call → authored section records
         ──▶  deterministic parse + validate against spec §3.1
         ──▶  render Markdown (marker blocks) + facts.json + report
response ◀──  A2A task result: artifacts[ README.md, ARCHITECTURE.md,
              CONTRIBUTING.md, facts.json, report.json ]
```

No database. The "document that learns" analytics store is a later, optional
addition and is not in the request path.

## A2A endpoint

- `GET /.well-known/agent-card.json` — public. One skill:
  `generate-onboarding-surface`.
- `POST /` — `message/send` (+ `message/stream` SSE for progress later).
  Parts: N `file` parts (the doc-relevant repo slice, bundled by the caller),
  one `text` part `mode=check|full`.
- The caller bundles the slice — the service never gets repo credentials and
  never clones. Slice = tree listing, manifests, CI config, lint configs,
  `.github/`, existing docs, a code digest of entrypoints + most-churned files.
- History-dependent sections (§6 review comments, §7 starter issues) need the
  platform API. The caller passes a short-lived read token as a `text` part
  (`github_token=...`) or the service is handed a pre-fetched
  `history.json` in the bundle. Prefer the latter — keeps the service
  credential-free.

## CI adapter

A composite GitHub Action, `curtiskrygier/onboarding-surface@v1`:

- **push, doc-relevant paths:** calls `mode=check`, writes the deterministic
  marker blocks, `git commit --amend`-style adds them to the push (or, on a
  fork PR, posts the diff as a review comment). Never fails.
- **merge to main / `docs:refresh` label / weekly cron:** calls `mode=full`,
  opens one PR with the combined update.
- Auth: repo's existing WIF → Google OIDC token → service verifies + checks the
  repo against an allowlist. Fallback: `secrets.ONBOARDING_SURFACE_TOKEN`.

## Hosting / infra

- Cloud Run service `onboarding-surface`, project + region TBD (co-locate with
  the LLM region).
- LLM: Gemini via Vertex Express (`vendor_vertex_rest.py` pattern), or Claude —
  decide at build. `mode=check` makes no LLM call.
- CI for this repo dogfoods the Action on itself.

## Build order

1. `extract` — `facts.json` from a local repo path. No network, no LLM. Testable
   against this repo + a2ui-catalogue + maison.
2. `render` — `facts.json` + authored records → the three Markdown files. Authored
   records hand-written first, to lock the format.
3. `author` — the one governed LLM call producing the records. Prompt generated
   from the spec.
4. `serve` — the A2A wrapper.
5. `action` — the CI composite.
