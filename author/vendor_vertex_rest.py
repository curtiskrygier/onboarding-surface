"""Shared Vertex AI REST client — Express Mode (API key) or plain IAM,
whichever this deployment has configured.

A DELIBERATE DUPLICATE of `maison/vertex_rest.py` (this whole repo was
extracted from `maison`, 2026-08-20 — see backlog.md's own entry) — `maison`
still uses its own copy for its Talk feature (`nlp.py`), unrelated to this
repo. A small, self-contained, dependency-free (stdlib + google-auth only)
file duplicating cleanly beat a cross-repo dependency for one signed POST —
same call this repo's own backlog made for litellm/OpenGateLLM. Real,
accepted cost: a fix here (e.g. another Vertex API shape change) needs
applying in BOTH copies.

Historical context worth keeping: extracted from `maison`'s `nlp.py`, whose
own docstring recorded a real outage — every Talk-page message failed with a
bare "(RuntimeError)" the moment the model moved to gemini-3.7-flash, because
the plain-IAM URL shape 404s that model regardless of credentials, and only
Express Mode's shape — no project, no region in the path at all,
authenticated by an `x-goog-api-key` header instead of a bearer token —
actually reaches it.

Vertex AI over REST rather than an SDK: one signed POST doesn't need a whole
SDK's worth of surface to keep current.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
from typing import Any, Dict, List, Optional

DEFAULT_LOCATION = "europe-west1"       # co-located with Cloud Run and Firestore (eur3)

# 2026-09-03: found live, deployed to Cloud Run -- a single run's main
# tool-calling call() hit a bare TimeoutError on urlopen's response read
# (45s already, not a tight budget) and took the whole run down, on an
# ALREADY-WARM container mid-run (confirmed against Cloud Run logs: 7
# prior successful tool-calling round trips over ~3 minutes, ruling out
# a cold-start explanation). The SAME timeout hit stream_call's own
# narration call twice more in the 90 seconds before that, non-fatal
# there only because sketch_agent.py's own _narrate() already wraps it
# in a try/except -- call()'s main loop had no equivalent protection at
# all. A real, recurring transient-network pattern, not a one-off --
# worth a genuine retry, not a shrug. Deliberately narrow: only
# TimeoutError/URLError (connection-level failures where no response
# body was ever received) retry: an HTTPError means Gemini DID answer,
# with a real status code that means something (403/429/5xx) -- retrying
# THOSE the same way would be a different, larger decision (a 429 in
# particular already has its own RateLimited type a caller may want to
# treat differently, e.g. backing off much longer or surfacing to a
# human) that wasn't part of what broke live, so left alone here.
_TRANSIENT_RETRIES = 2   # up to 3 real attempts total
_TRANSIENT_BACKOFF_S = 1.5


def _is_transient(e: BaseException) -> bool:
    # TimeoutError is what actually propagated live (Python's own
    # socket.timeout alias, raised directly by ssl.read -- NOT wrapped in
    # urllib.error.URLError, confirmed against the real Cloud Run
    # traceback). URLError covers connection-establishment failures
    # (DNS, refused, reset) urlopen DOES wrap. HTTPError subclasses
    # URLError but means a real response with a real status arrived --
    # excluded explicitly, not just left to the caller's isinstance
    # order, so this stays correct even if the two except clauses below
    # are ever reordered.
    return isinstance(e, TimeoutError) or (
        isinstance(e, urllib.error.URLError) and not isinstance(e, urllib.error.HTTPError))


class NotConfigured(Exception):
    """Phrased for the person (or the log) reading it."""


def endpoint(model_name: str, method: str = "generateContent") -> str:
    """Two distinct URL shapes. Express Mode (MAISON_GEMINI_API_KEY set) has
    no project or region in the path at all; the plain-IAM path does, and
    404s a model Express Mode reaches fine — see this module's docstring.

    `method` (2026-09-02, real token-by-token streaming -- see stream_call
    below): defaults to the existing "generateContent" so every caller
    before this parameter existed is unaffected; stream_call passes
    "streamGenerateContent" instead. Same two URL shapes either way, just
    the trailing verb differs.
    """
    if os.environ.get("MAISON_GEMINI_API_KEY"):
        return ("https://aiplatform.googleapis.com/v1beta1/publishers/google"
                "/models/{model}:{method}").format(model=model_name, method=method)
    project = os.environ.get("MAISON_PROJECT")
    if not project:
        raise NotConfigured(
            "Needs MAISON_PROJECT set (or MAISON_GEMINI_API_KEY for Express Mode).")
    location = os.environ.get("MAISON_VERTEX_LOCATION", DEFAULT_LOCATION)
    return ("https://{loc}-aiplatform.googleapis.com/v1/projects/{proj}"
            "/locations/{loc}/publishers/google/models/{model}:{method}"
            ).format(loc=location, proj=project, model=model_name, method=method)


def token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def call(model_name: str, contents: List[Dict[str, Any]], *,
         system: Optional[str] = None,
         schema: Optional[Dict[str, Any]] = None,
         tools: Optional[List[Dict[str, Any]]] = None,
         tool_config: Optional[Dict[str, Any]] = None,
         temperature: float = 0.2,
         max_output_tokens: int = 1200,
         timeout: int = 45) -> Dict[str, Any]:
    """One `generateContent` call. Returns the FULL parsed response body
    (`{"candidates": [...], ...}`) rather than pre-extracting a part — a
    tool-calling turn's part holds a `functionCall`, a structured-output
    turn's holds `text` with a JSON string, and only the caller knows which
    it asked for. Use `first_part()` below to get at it safely.

    `schema` and `tools` are mutually meaningful but not mutually exclusive
    at the API level; callers pass whichever they need (nlp.py: schema only;
    daily_agent.py: tools only, no schema — a function-calling turn cannot
    also be constrained to a fixed JSON shape).
    """
    import urllib.error
    import urllib.request

    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if schema is not None:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = schema

    body: Dict[str, Any] = {"contents": contents, "generationConfig": generation_config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools
    if tool_config:
        # e.g. {"functionCallingConfig": {"mode": "ANY"}} — FORCES a function
        # call every turn, eliminating the model-answered-in-prose failure
        # class at the API level instead of merely prompting against it.
        body["toolConfig"] = tool_config

    api_key = os.environ.get("MAISON_GEMINI_API_KEY")
    # Express Mode authenticates by header, not a bearer token — token()
    # fetches Application Default Credentials, which this deployment may not
    # even have configured if it is running on the key alone.
    headers = ({"x-goog-api-key": api_key, "Content-Type": "application/json"}
              if api_key else
              {"Authorization": "Bearer %s" % token(),
               "Content-Type": "application/json"})
    req = urllib.request.Request(
        endpoint(model_name), method="POST",
        data=json.dumps(body).encode(),
        headers=headers)
    for attempt in range(_TRANSIENT_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")[:200]
            if e.code == 403:
                raise NotConfigured(
                    "Not allowed to call Vertex AI yet — the runtime service "
                    "account needs roles/aiplatform.user (or set "
                    "MAISON_GEMINI_API_KEY for Express Mode).")
            if e.code == 429:
                raise RateLimited("Gemini answered HTTP 429: %s" % detail)
            raise RuntimeError("Gemini answered HTTP %d: %s" % (e.code, detail))
        except Exception as e:  # noqa: BLE001 -- narrowed by _is_transient below
            if not _is_transient(e) or attempt >= _TRANSIENT_RETRIES:
                raise
            time.sleep(_TRANSIENT_BACKOFF_S * (attempt + 1))


def stream_call(model_name: str, contents: List[Dict[str, Any]], *,
                system: Optional[str] = None,
                temperature: float = 0.6,
                max_output_tokens: int = 600,
                timeout: int = 30,
                thinking_config: Optional[Dict[str, Any]] = None):
    """Real per-token streaming via Vertex's `:streamGenerateContent?alt=sse`
    -- genuinely incremental, not `call()`'s complete response chopped up
    after the fact (2026-09-02, Curtis: "we get the llm to state what is
    being done" -- proving AG-UI's own TextMessageStart/Content/End is
    real requires the MODEL's own generation to be what's arriving in
    pieces, not a simulation).

    No `tools`/`tool_config` here on purpose: Gemini's ANY function-calling
    mode (what sketch_agent.py's main tool-calling turns use, deliberately,
    for reliability -- see call()'s own toolConfig comment) suppresses free
    text entirely, so a narration-and-a-tool-call in the SAME turn isn't a
    combination this API reliably supports. This is a separate, small,
    text-only call sketch_agent.py makes alongside its real tool-calling
    turn, not a replacement for it -- the existing loop's reliability is
    completely unchanged by this function existing.

    `max_output_tokens` defaults to 600, not the ~40 a short sentence
    would suggest -- confirmed live, 2026-09-02: gemini-3.7-flash (a
    reasoning model) spends invisible "thinking" tokens
    (`usageMetadata.thoughtsTokenCount`) BEFORE any visible text, and this
    is NOT something a caller can turn off from here -- a real request
    with `generationConfig.thinkingConfig.thinkingBudget: 0` was accepted
    (no error) but silently NOT honored (57 thinking tokens still consumed
    against a 60-token budget, leaving zero for the actual answer). A
    caller passing a small budget here WILL get an empty stream and
    `finishReason: MAX_TOKENS`, not a short answer -- this default exists
    so that's the exception, not the norm.

    Yields each PARSED SSE chunk as it arrives (same top-level shape as
    call()'s own return value, just one partial piece at a time) -- Gemini
    streams TEXT parts as a sequence of incremental `text` substrings, one
    per chunk; the FINAL chunk carries `finishReason`/`usageMetadata`, same
    fields call()'s own single response has. A caller wanting the plain
    text stream reads `chunk["candidates"][0]["content"]["parts"][0].get("text")`
    per chunk, same access pattern first_part() already uses on a whole
    response, just applied per-chunk instead of once.

    Uses urllib's own incremental line reads on the response object (a
    real streaming HTTP body, not buffered) -- deliberately NOT httpx or
    requests, matching this module's own "stdlib + google-auth only"
    dependency discipline (see module docstring)."""
    import urllib.error
    import urllib.request

    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if thinking_config is not None:
        # 2026-09-03, real AG-UI Reasoning proof case: {"includeThoughts":
        # True} confirmed live to make gemini-3.7-flash return actual
        # visible thought text (parts with "thought": true), not just the
        # opaque thoughtSignature -- distinct from thinkingBudget (which
        # controls HOW MUCH thinking happens and, confirmed separately,
        # isn't reliably honored at 0 -- see this function's own docstring)
        # this controls whether any of it is EXPOSED at all.
        generation_config["thinkingConfig"] = thinking_config
    body: Dict[str, Any] = {"contents": contents, "generationConfig": generation_config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    api_key = os.environ.get("MAISON_GEMINI_API_KEY")
    headers = ({"x-goog-api-key": api_key, "Content-Type": "application/json"}
              if api_key else
              {"Authorization": "Bearer %s" % token(),
               "Content-Type": "application/json"})
    req = urllib.request.Request(
        endpoint(model_name, method="streamGenerateContent") + "?alt=sse", method="POST",
        data=json.dumps(body).encode(),
        headers=headers)
    # Retry scoped to OPENING the connection only, not the stream itself --
    # once a single chunk has been yielded to the caller, a retry would
    # mean silently restarting the whole generation and re-yielding
    # duplicate/conflicting content, which is a different and much worse
    # failure than just letting a genuine mid-stream error propagate (the
    # caller already handles that non-fatally -- see sketch_agent.py's own
    # _narrate(), the one real caller of this function).
    resp = None
    for attempt in range(_TRANSIENT_RETRIES + 1):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")[:200]
            if e.code == 403:
                raise NotConfigured(
                    "Not allowed to call Vertex AI yet — the runtime service "
                    "account needs roles/aiplatform.user (or set "
                    "MAISON_GEMINI_API_KEY for Express Mode).")
            if e.code == 429:
                raise RateLimited("Gemini answered HTTP 429: %s" % detail)
            raise RuntimeError("Gemini answered HTTP %d: %s" % (e.code, detail))
        except Exception as e:  # noqa: BLE001 -- narrowed by _is_transient below
            if not _is_transient(e) or attempt >= _TRANSIENT_RETRIES:
                raise
            time.sleep(_TRANSIENT_BACKOFF_S * (attempt + 1))

    with resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            # SSE framing: "data: {json}" lines carry payloads; blank
            # lines and any other field (":", "event:") are ignored --
            # Vertex's alt=sse stream only ever sends "data:" in
            # practice, but a real SSE consumer shouldn't assume that.
            if not line.startswith("data:"):
                continue
            chunk_text = line[len("data:"):].strip()
            if chunk_text:
                yield json.loads(chunk_text)


class RateLimited(RuntimeError):
    """HTTP 429 from Vertex — quota pressure, not a real failure. Confirmed
    live, 2026-08-19, after several back-to-back daily-agent runs in one
    day: Express Mode's quota recovers on its own, so the caller should
    back off and retry rather than abort the whole run (which is what the
    generic RuntimeError below caused before this class existed)."""


class MalformedFunctionCall(RuntimeError):
    """The model attempted a tool call that failed Gemini's OWN validation
    (finishReason MALFORMED_FUNCTION_CALL) — confirmed live, 2026-08-17, on
    the daily agent's first real run. Worth one immediate retry before
    treating it as a real failure, the same "transient miss" reasoning
    agent.compose's own retry-once already uses (concepts.py:
    retry_resilience) — a caller that wants that behaviour catches this
    specifically; anything else raises the plain RuntimeError below, which
    is NOT worth retrying (a safety block or genuine refusal repeats).

    `payload` carries the full raw response so a caller can log it —
    diagnosing WHY a call was malformed needs to see what Gemini actually
    attempted, and this is the only place that still has it.
    """
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.payload = payload


def first_part(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The first content part of the first candidate. A blocked or empty
    candidate has no parts — named as such rather than surfacing a bare
    KeyError."""
    try:
        return payload["candidates"][0]["content"]["parts"][0]
    except (KeyError, IndexError):
        reason = (payload.get("candidates") or [{}])[0].get("finishReason", "unknown")
        if reason == "MALFORMED_FUNCTION_CALL":
            raise MalformedFunctionCall(
                "Gemini attempted a function call that failed its own validation.",
                payload=payload)
        raise RuntimeError("Gemini returned no usable answer (finishReason: %s)" % reason)
