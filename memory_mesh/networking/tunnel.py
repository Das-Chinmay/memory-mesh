"""
ngrok tunnel — wraps pyngrok for ChatGPT connector support.

Windows fix: pyngrok downloads its binary to ~/.ngrok2/ on first run.
On Windows this sometimes hits a permissions error in restricted environments.
We set the ngrok config_path explicitly to the user's home dir to avoid
"Access Denied" errors in PowerShell running without admin rights.
"""
from __future__ import annotations
from pathlib import Path


def _get_ngrok():
    """Import pyngrok or raise a helpful error."""
    try:
        from pyngrok import ngrok, conf
        return ngrok, conf
    except ImportError:
        raise RuntimeError(
            "pyngrok is not installed.\n"
            "Run: pip install 'memory-mesh[chatgpt]'\n"
            "Or:  pip install pyngrok"
        )


def start_ngrok_tunnel(port: int, auth_token: str | None = None) -> str:
    """
    Open an ngrok HTTPS tunnel to localhost:<port>.
    Returns the public URL e.g. 'https://abc123.ngrok-free.app'.

    Windows binary path fix: sets pyngrok config dir to ~/.ngrok2 explicitly
    so the binary download doesn't fail in restricted PowerShell sessions.
    """
    ngrok, conf = _get_ngrok()

    # Windows fix: explicit config path avoids permission errors
    ngrok_config = conf.PyngrokConfig(
        ngrok_path=str(Path.home() / ".ngrok2" / "ngrok.exe"),
        config_path=str(Path.home() / ".ngrok2" / "ngrok.yml"),
    )
    conf.set_default(ngrok_config)

    if auth_token:
        ngrok.set_auth_token(auth_token)

    tunnel = ngrok.connect(port, "http")
    return tunnel.public_url.replace("http://", "https://")


def stop_ngrok_tunnel() -> None:
    """Kill all ngrok tunnels. Safe to call even if none are running."""
    try:
        ngrok, _ = _get_ngrok()
        ngrok.kill()
    except Exception:
        pass
