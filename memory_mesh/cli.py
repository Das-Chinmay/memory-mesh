from __future__ import annotations

import click

from memory_mesh.config import Config


def _make_store(cfg: Config, **kwargs):
    from memory_mesh.core.store import MemoryStore
    store = MemoryStore(cfg, **kwargs)
    store.connect()
    return store


@click.group()
def cli() -> None:
    """memory-mesh — shared memory for all AI assistants."""


@cli.command()
@click.option("--host", default=None, help="Bind host (default: 127.0.0.1)")
@click.option("--port", default=None, type=int, help="Port (default: 8765)")
@click.option("--auth", is_flag=True, help="Enable Bearer token auth")
@click.option("--config", "config_path", default=None, help="Path to config.json")
def serve(host: str | None, port: int | None, auth: bool, config_path: str | None) -> None:
    """Start the REST API server on localhost:8765."""
    import uvicorn
    from pathlib import Path
    from memory_mesh.transports.rest_server import make_app

    cfg = Config.load(Path(config_path) if config_path else None)
    if host:
        cfg.host = host
    if port:
        cfg.port = port
    if auth:
        cfg.auth_enabled = True

    store = _make_store(cfg)
    app = make_app(store, config=cfg)
    click.echo(f"memory-mesh REST server starting on http://{cfg.host}:{cfg.port}")

    from memory_mesh.networking.mdns import advertise_mdns, stop_mdns, _local_ip
    from memory_mesh.networking.tailscale import tailscale_status
    zc = advertise_mdns(cfg.port)
    click.echo(f"mDNS: broadcasting as memory-mesh.local:{cfg.port} ({_local_ip()})")

    ts = tailscale_status()
    if ts["running"]:
        click.echo(f"Tailscale: reachable at {ts['ip']}:{cfg.port} from any device on your tailnet")
    else:
        click.echo("Tailscale: not detected  →  install tailscale.com for remote access")

    # Windows note: on hard Ctrl+C the finally block may not run.
    # Orphaned mDNS records expire automatically after 120s.
    try:
        uvicorn.run(app, host=cfg.host, port=cfg.port)
    finally:
        stop_mdns(zc)


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.json")
def mcp(config_path: str | None) -> None:
    """Start the MCP stdio server (used by Claude Desktop)."""
    from pathlib import Path
    from memory_mesh.transports.mcp_server import make_mcp_server

    cfg = Config.load(Path(config_path) if config_path else None)
    store = _make_store(cfg)
    server, _ = make_mcp_server(store)
    server.run()


@cli.command("conflicts")
@click.option("--status", default="pending", help="'pending' or 'resolved'")
@click.option("--config", "config_path", default=None, help="Path to config.json")
def list_conflicts(status: str, config_path: str | None) -> None:
    """List and interactively resolve memory conflicts."""
    from pathlib import Path
    from memory_mesh.core.models import Resolution

    cfg = Config.load(Path(config_path) if config_path else None)
    store = _make_store(cfg)
    conflicts = store.list_conflicts(status=status)

    if not conflicts:
        click.echo(f"No {status} conflicts.")
        return

    for conflict in conflicts:
        click.echo(f"\n{'='*60}")
        click.echo(f"Conflict ID: {conflict.id}  [{conflict.trigger}]")
        a = conflict.memory_a
        b = conflict.memory_b
        click.echo(f"\n  A [{conflict.memory_a_id}] ({a.agent_id if a else '?'}):")
        click.echo(f"    {a.content if a else '(not found)'}")
        click.echo(f"\n  B [{conflict.memory_b_id}] ({b.agent_id if b else '?'}):")
        click.echo(f"    {b.content if b else '(not found)'}")

        if status == "resolved":
            click.echo(f"\n  Winner: {conflict.resolution_id} (by {conflict.resolved_by})")
            continue

        choice = click.prompt(
            "\n  Which is correct? [a/b/skip]",
            type=click.Choice(["a", "b", "skip"], case_sensitive=False),
            default="skip",
        )
        if choice == "skip":
            continue
        winning_id = conflict.memory_a_id if choice == "a" else conflict.memory_b_id
        resolution = Resolution(conflict_id=conflict.id, winning_id=winning_id, resolved_by="cli")
        store.resolve_conflict(resolution)
        click.echo(f"  Resolved: {winning_id} wins.")


@cli.command("chatgpt")
@click.option("--ngrok-token", default=None, envvar="NGROK_AUTH_TOKEN",
              help="ngrok auth token (or set NGROK_AUTH_TOKEN env var)")
@click.option("--auth-token", default=None,
              help="memory-mesh Bearer token (enables REST auth)")
@click.option("--port", default=None, type=int)
@click.option("--config", "config_path", default=None)
def chatgpt_command(ngrok_token, auth_token, port, config_path):
    """Start REST server + ngrok tunnel for ChatGPT connector."""
    import threading
    from pathlib import Path
    from memory_mesh.networking.tunnel import start_ngrok_tunnel, stop_ngrok_tunnel
    from memory_mesh.transports.rest_server import make_app
    import uvicorn

    cfg = Config.load(Path(config_path) if config_path else None)
    if port:
        cfg.port = port
    if auth_token:
        cfg.auth_enabled = True
        cfg.auth_token = auth_token

    store = _make_store(cfg)
    app = make_app(store, config=cfg)

    click.echo("Starting ngrok tunnel...")
    try:
        public_url = start_ngrok_tunnel(cfg.port, ngrok_token)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    click.echo("\n" + "=" * 44)
    click.echo("  ChatGPT connector ready")
    click.echo("=" * 44)
    click.echo("  1. ChatGPT → Settings → Connectors")
    click.echo("     toggle ON Developer Mode")
    click.echo("  2. Click + in a new chat → Add Sources")
    click.echo(f"  3. Paste URL: {public_url}")
    if cfg.auth_enabled:
        click.echo(f"  4. Add header: Authorization: Bearer {cfg.auth_token}")
    click.echo("  Ctrl+C to stop")
    click.echo("=" * 44 + "\n")

    try:
        uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="warning")
    finally:
        stop_ngrok_tunnel()
        click.echo("ngrok tunnel closed.")
