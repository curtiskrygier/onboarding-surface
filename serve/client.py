"""client.py — a real a2a-sdk client call against `serve`, for real remote use
or in-process testing (see `test_serve.py`). Not a CLI — import and call.

    import httpx
    from serve.client import call_agent
    # If the server has ONBOARDING_SURFACE_TOKEN set, put it on the client
    # itself -- every request this client makes (card fetch AND the RPC
    # call) then carries it, rather than this helper guessing at which SDK
    # call accepts a per-request header override.
    headers = {"Authorization": "Bearer <token>"}
    async with httpx.AsyncClient(base_url="https://onboarding-surface.example",
                                 headers=headers) as hc:
        result = await call_agent(hc, "render", facts=facts, exposure="public")
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import DataPart, Message, Part, Role


async def call_agent(hc: httpx.AsyncClient, job: str, *, facts: dict,
                     **options: Any) -> dict:
    """One request/reply A2A call. `hc`'s base_url is the running `serve`
    instance (in-process via httpx.ASGITransport, or a real deployed URL);
    an auth token, if the server requires one, goes on `hc` itself (see the
    module docstring) — every request `hc` makes carries it automatically.
    `options` are folded straight into the payload (digest, authored,
    exposure, model, detail — see serve.py's OnboardingSurfaceExecutor)."""
    base_url = str(hc.base_url)
    card = await A2ACardResolver(hc, base_url).get_agent_card()
    client = ClientFactory(ClientConfig(httpx_client=hc, streaming=False)).create(card)

    payload = {"job": job, "facts": facts, **options}
    msg = Message(role=Role.user, message_id=str(uuid.uuid4()),
                 parts=[Part(root=DataPart(data=payload))])

    got = None
    async for event in client.send_message(msg):
        got = event
    if not isinstance(got, Message):
        raise RuntimeError(f"expected a bare Message reply, got {type(got)}: {got!r}")

    data_part = next(
        (getattr(p, "root", p) for p in got.parts
         if isinstance(getattr(p, "root", p), DataPart)),
        None)
    if data_part is not None:
        return data_part.data
    text_part = next(
        (getattr(p, "root", p) for p in got.parts if hasattr(getattr(p, "root", p), "text")),
        None)
    raise RuntimeError(f"serve returned no DataPart" +
                      (f": {text_part.text}" if text_part else f" ({got!r})"))
