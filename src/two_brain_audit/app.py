"""Standalone PyWebView app — launches the dashboard in its own window.

Usage:
    python -c "from two_brain_audit.app import launch; launch(engine)"

Or via CLI:
    two-brain-audit dashboard --native
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from two_brain_audit.engine import AuditEngine

log = logging.getLogger("two_brain_audit")


def launch(
    engine: AuditEngine,
    title: str = "Two-Brain Audit",
    width: int = 1100,
    height: int = 750,
    port: int = 8484,
) -> None:
    """Launch the dashboard in a native PyWebView window.

    Starts Flask on a background thread and opens a webview window.
    Window close kills the Flask server.
    """
    try:
        import webview
    except ImportError:
        print(
            "PyWebView not installed. Install it with:\n"
            "  pip install pywebview\n"
            "Falling back to browser mode...",
            file=sys.stderr,
        )
        _fallback_browser(engine, port)
        return

    from flask import Flask

    from two_brain_audit.dashboard import create_blueprint

    app = Flask("two_brain_audit")
    app.register_blueprint(create_blueprint(engine), url_prefix="/audit")

    url = f"http://127.0.0.1:{port}/audit/"

    # Start Flask in a daemon thread
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    # Wait for Flask to be ready
    _wait_for_server(url, timeout=10)

    # Open native window — prefer Qt backend on Windows (pythonnet often broken on 3.13+)
    webview.create_window(
        title,
        url,
        width=width,
        height=height,
        min_size=(800, 500),
        background_color="#0f1117",
    )

    # Try Qt first (works on all Python versions), fall back to default
    for gui in ("qt", None):
        try:
            webview.start(gui=gui)
            break
        except Exception as exc:
            if gui is not None:
                log.debug("pywebview gui=%s failed: %s, trying next", gui, exc)
                continue
            raise


def _wait_for_server(url: str, timeout: int = 10) -> None:
    """Block until the Flask server responds or timeout."""
    import time
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)  # noqa: S310
            return
        except Exception:
            time.sleep(0.2)
    log.warning("Server did not start within %ds, opening window anyway", timeout)


def _fallback_browser(engine: AuditEngine, port: int) -> None:
    """Fall back to opening in the default browser."""
    import webbrowser

    from flask import Flask

    from two_brain_audit.dashboard import create_blueprint

    app = Flask("two_brain_audit")
    app.register_blueprint(create_blueprint(engine), url_prefix="/audit")

    url = f"http://127.0.0.1:{port}/audit/"
    print(f"Dashboard: {url}")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)
