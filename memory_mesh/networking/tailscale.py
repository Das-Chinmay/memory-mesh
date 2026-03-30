"""
Tailscale integration — read-only. We never start/stop Tailscale from here,
just report its status so the CLI can tell the user their remote access IP.
"""
import json
import subprocess
from typing import TypedDict


class TailscaleStatus(TypedDict):
    installed: bool
    running: bool
    ip: str | None


def get_tailscale_ip() -> str | None:
    """
    Return the Tailscale IPv4 address (100.x.x.x) or None.
    Never raises — safe to call even if Tailscale is not installed.
    """
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=3
        )
        ip = result.stdout.strip()
        return ip if result.returncode == 0 and ip else None
    except Exception:
        return None


def tailscale_status() -> TailscaleStatus:
    """
    Return installation and running state plus IP.
    Uses `tailscale status --json` for reliable machine-readable output.
    """
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {"installed": True, "running": False, "ip": None}
        data = json.loads(result.stdout)
        running = data.get("BackendState") == "Running"
        return {"installed": True, "running": running, "ip": get_tailscale_ip()}
    except FileNotFoundError:
        return {"installed": False, "running": False, "ip": None}
    except Exception:
        return {"installed": False, "running": False, "ip": None}
