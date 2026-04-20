"""
Shared pytest fixtures:

  http_fixture_server — starts an in-process HTTP server serving
    tests/fixtures/probe/ on a random port. Session-scoped. Yields
    the base URL; tears down on session end.

  browser — Playwright Chromium browser launched once per session
    (saves the ~1s cold-start per test). Tests create their own
    contexts from the shared browser via probe()'s internal
    context.new_context call, so session-shared is safe.

No public-web dependency per §R1.1 test strategy.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path
from typing import Iterator

import pytest


FIXTURES_PROBE = Path(__file__).parent / "fixtures" / "probe"


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        # Suppress per-request stderr noise during tests
        return


@pytest.fixture(scope="session")
def http_fixture_server() -> Iterator[str]:
    def _handler_factory(*args, **kwargs):
        return _SilentHandler(*args, directory=str(FIXTURES_PROBE), **kwargs)

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _handler_factory)
    server.allow_reuse_address = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        try:
            yield br
        finally:
            br.close()
