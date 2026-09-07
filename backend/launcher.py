"""Application launcher: init DB, start server, open browser, exit when UI closes."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def _ensure_stdio() -> None:
    """Windowed PyInstaller builds set stdout/stderr to None — breaks uvicorn logging."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")


_ensure_stdio()

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)
elif str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Shared shutdown / heartbeat state used by API + launcher watchdog
_last_heartbeat = 0.0
_heartbeat_started = False
_server = None
_shutdown_requested = threading.Event()
_force_exit_started = False
_lock = threading.Lock()
_runtime_info: dict = {}

# Avoid uvicorn ColourizedFormatter (calls stream.isatty) under noconsole EXE
_UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "logging.Formatter",
            "fmt": "%(levelname)s: %(message)s",
        },
        "access": {
            "()": "logging.Formatter",
            "fmt": '%(levelname)s: %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "WARNING", "propagate": False},
    },
}


def bind_host() -> str:
    """Listen address. Default 0.0.0.0 = this PC + LAN. Set PTO_HOST=127.0.0.1 for local-only."""
    return (os.environ.get("PTO_HOST") or "0.0.0.0").strip() or "0.0.0.0"


def lan_share_enabled(host: str | None = None) -> bool:
    h = (host or bind_host()).lower()
    return h in ("0.0.0.0", "::", "[::]")


def find_free_port(preferred: int = 8765, host: str = "0.0.0.0") -> int:
    for port in [preferred, *range(8766, 8800)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def lan_ipv4_addresses() -> list[str]:
    ips: list[str] = []

    def add(ip: str) -> None:
        if not ip or ip.startswith("127.") or ip.startswith("169.254."):
            return
        if ip not in ips:
            ips.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            add(s.getsockname()[0])
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            add(info[4][0])
    except Exception:
        pass

    return ips


def build_access_urls(port: int, host: str) -> dict:
    local_url = f"http://127.0.0.1:{port}/"
    lan_ips = lan_ipv4_addresses() if lan_share_enabled(host) else []
    lan_urls = [f"http://{ip}:{port}/" for ip in lan_ips]
    return {
        "host": host,
        "port": port,
        "local_url": local_url,
        "lan_urls": lan_urls,
        "lan_ips": lan_ips,
        "lan_share": lan_share_enabled(host),
        "keep_alive": lan_share_enabled(host),
    }


def write_access_file(info: dict) -> Path | None:
    try:
        from backend.paths import data_dir, install_dir

        lines = [
            "PowerTrain Optimizer — access addresses",
            "========================================",
            "",
            f"This PC (browser on the same laptop):  {info['local_url']}",
        ]
        if info.get("lan_urls"):
            lines.append("")
            lines.append("Other laptops on the same Wi‑Fi / office network:")
            for u in info["lan_urls"]:
                lines.append(f"  {u}")
            lines.append("")
            lines.append("Keep PowerTrainOptimizer.exe running on this laptop.")
            lines.append("Use Quit App only when everyone should disconnect.")
            lines.append("Windows Firewall: allow Private network access if prompted.")
        else:
            lines.append("")
            lines.append("LAN sharing is off (PTO_HOST=127.0.0.1) or no network IP was found.")
        lines.append("")
        text = "\n".join(lines) + "\n"
        path = data_dir() / "ACCESS_URLS.txt"
        path.write_text(text, encoding="utf-8")
        # Also next to the EXE when frozen (easy to find / share the path)
        try:
            if getattr(sys, "frozen", False):
                (install_dir() / "ACCESS_URLS.txt").write_text(text, encoding="utf-8")
        except Exception:
            pass
        return path
    except Exception:
        return None


def get_runtime_info() -> dict:
    return dict(_runtime_info)


def note_heartbeat():
    global _last_heartbeat, _heartbeat_started
    _last_heartbeat = time.monotonic()
    _heartbeat_started = True


def _force_exit_soon(delay: float = 0.8):
    """Always kill the process after shutdown — uvicorn.should_exit alone can hang on Windows."""
    global _force_exit_started
    with _lock:
        if _force_exit_started:
            return
        _force_exit_started = True

    def _kill():
        time.sleep(delay)
        os._exit(0)

    threading.Thread(target=_kill, daemon=True).start()


def request_shutdown():
    _shutdown_requested.set()
    srv = _server
    if srv is not None:
        try:
            srv.should_exit = True
            srv.force_exit = True
        except Exception:
            pass
    _force_exit_soon(0.8)


def wait_until_ready(url: str, timeout: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout
    health = url.rstrip("/") + "/api/health"
    while time.monotonic() < deadline:
        if _shutdown_requested.is_set():
            return False
        try:
            with urllib.request.urlopen(health, timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def _watchdog(grace_sec: float = 8.0, first_beat_timeout: float = 90.0):
    """Exit if the browser/UI stops sending heartbeats (local-only mode)."""
    wait_deadline = time.monotonic() + first_beat_timeout
    while not _shutdown_requested.is_set() and not _heartbeat_started:
        if time.monotonic() > wait_deadline:
            request_shutdown()
            return
        time.sleep(0.4)
    while not _shutdown_requested.is_set():
        time.sleep(0.5)
        if _heartbeat_started and (time.monotonic() - _last_heartbeat) > grace_sec:
            request_shutdown()
            return
    _force_exit_soon(0.5)


def main():
    global _runtime_info
    _ensure_stdio()
    from backend.database.init_db import initialize_database
    from backend.logging_setup import setup_logging
    from backend.main import create_app

    log = setup_logging()
    log.info("Starting PowerTrain Optimizer")
    initialize_database()

    host = bind_host()
    port = find_free_port(host=host)
    info = build_access_urls(port, host)
    _runtime_info = info
    write_access_file(info)

    local_url = info["local_url"]
    app = create_app(init_db=False)

    app.state.launcher_note_heartbeat = note_heartbeat
    app.state.launcher_request_shutdown = request_shutdown
    app.state.runtime_info = info

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        reload=False,
        log_config=_UVICORN_LOG_CONFIG,
    )
    global _server
    _server = uvicorn.Server(config)

    def open_when_ready():
        if wait_until_ready(local_url):
            try:
                webbrowser.open(local_url)
            except Exception:
                log.warning("Could not open browser automatically. Open %s manually.", local_url)
            if info.get("lan_urls"):
                log.info("LAN access: %s", ", ".join(info["lan_urls"]))
        else:
            log.error("Server did not become ready in time")
            request_shutdown()

    threading.Thread(target=open_when_ready, daemon=True).start()
    # LAN / keep-alive: do not kill the server when the host closes the browser —
    # remote users on the network may still be connected. Exit only via Quit App.
    if not info.get("keep_alive"):
        threading.Thread(target=_watchdog, kwargs={"grace_sec": 8.0}, daemon=True).start()

    log.info("Listening on %s (bind %s:%s)", local_url, host, port)
    for u in info.get("lan_urls") or []:
        log.info("Network URL: %s", u)
    try:
        _server.run()
    finally:
        log.info("PowerTrain Optimizer stopped")
        os._exit(0)


if __name__ == "__main__":
    main()
