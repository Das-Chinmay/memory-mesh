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
    uvicorn.run(app, host=cfg.host, port=cfg.port)


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
