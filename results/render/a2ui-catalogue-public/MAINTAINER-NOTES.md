# Maintainer notes — not for the public surface

## Landmines held back (spec §15)

- **[private-ref]** Operational tooling, internal logs, and incident records rely on symlinks into a private sibling repository that are absent in a clean checkout. *(source: AGENTS.md)*
- **[exploitable]** A wired surface MCP action will fail silently if its verb is not present in both the MCP worker definitions and the Apps Script transport allowlist. *(source: CLAUDE.md)*

