# Design — service shape

Companion to `spec/onboarding-surface-v0.1.md` §11–12. This is the *how it runs*,
kept separate from the *what it produces*.

## Shape — as built (`serve/`, 2026-09-06)

**Revised from this doc's original sketch below** (kept for the record): the
original had the service run `extract` itself over a caller-bundled raw file
slice. `extract` as actually built (step 1, below) is a `git`-checkout tool —
`git ls-files`, `git log` for history/contrib facts — reimplementing that
against an uploaded bundle would duplicate the logic for a shakier input, and
(Gemini 3.8 Flash design review, 2026-09-06) reopens exactly the security
surface a stateless, repo-blind server was meant to avoid: SSRF via clone,
credential delegation, disk cleanup.

```
CALLER (has the git checkout)         SERVICE (repo-blind, stateless)
  extract  → facts.json          ──▶  author  → authored prose + landmines
  build_digest → digest text          render  → README/ARCHITECTURE/
  (both local, no network)                      CONTRIBUTING(+MAINTAINER-NOTES)
                                       draw    → architecture-sketch SVG (D2,
                                                 no LLM)
                                 ◀──  one A2A DataPart reply per job
```

Four skills (`author`, `render`, `draw`, `full`), not one `mode=check|full`
call — see spec §12 for why (proxy/client timeouts on a 60-90s batched call).
`render` always runs `--fresh` — no target repo here to splice into.

No database. The "document that learns" analytics store is a later, optional
addition and is not in the request path.

## A2A endpoint — as built

- `GET /.well-known/agent-card.json` — public (unless `ONBOARDING_SURFACE_TOKEN`
  is set). Skills: `author`, `render`, `draw`, `full`.
- `POST /` — `message/send`. One `DataPart`: `{job, facts, digest?, authored?,
  exposure?, model?, detail?}` in; one `DataPart` reply out.
- The caller sends `facts.json` (+ an optional digest string) — never the repo
  itself, never credentials. See `serve/README.md` for the exact contract and
  a runnable client example.
- History-dependent sections (§6 review comments, §7 starter issues) already
  come from `extract --github`, which runs locally alongside everything else
  — no separate token-passing scheme needed at the A2A boundary.

## Original sketch, superseded above

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

A composite GitHub Action, `curtiskrygier/onboarding-surface/action@v1`:

- **push, doc-relevant paths:** calls `mode=check`, writes the deterministic
  marker blocks, `git commit --amend`-style adds them to the push (or, on a
  fork PR, posts the diff as a review comment). Never fails.
- **merge to main / `docs:refresh` label / weekly cron:** calls `mode=full`,
  opens one PR with the combined update.
- Auth: repo's existing WIF → Google OIDC token → service verifies + checks the
  repo against an allowlist. Fallback: `secrets.ONBOARDING_SURFACE_TOKEN`.

## Hosting / infra

- Cloud Run service `onboarding-surface`, project + region TBD (co-locate with
  the LLM region). `render`/`draw:architecture` make no LLM call either way —
  only `author`/`draw:mark`/`full` need `MAISON_GEMINI_API_KEY` configured.
- LLM: Gemini via Vertex Express (`author/vendor_vertex_rest.py` pattern).
- `draw`'s architecture job needs the `d2` CLI on the service's image/PATH.
- CI for this repo dogfoods the Action on itself (once `action` is built).

## Build order

1. `extract` — `facts.json` from a local repo path. No network, no LLM. Testable
   against this repo + a2ui-catalogue + maison. **Built.**
2. `render` — `facts.json` + authored records → the three Markdown files. Authored
   records hand-written first, to lock the format. **Built.**
3. `author` — the one governed LLM call producing the records. Prompt generated
   from the spec. **Built.**
4. `draw` — the architecture sketch (D2, deterministic) + repo-mark proposals
   (LLM, human-gated). Not in the original build order — added once the
   visuals work (spec §16) proved worth doing. **Built.**
5. `serve` — the A2A wrapper. **Built** (this doc, above).
6. `action` — the CI composite. **Built.** See `action/README.md`.
