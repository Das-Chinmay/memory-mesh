import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call


def _make_mock_ngrok(public_url="http://abc123.ngrok-free.app"):
    mock_ngrok = MagicMock()
    mock_conf = MagicMock()
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = public_url
    mock_ngrok.connect.return_value = mock_tunnel
    return mock_ngrok, mock_conf


def test_start_returns_https_url():
    mock_ngrok, mock_conf = _make_mock_ngrok("http://abc123.ngrok-free.app")
    with patch.dict("sys.modules", {"pyngrok": MagicMock(), "pyngrok.ngrok": mock_ngrok, "pyngrok.conf": mock_conf}):
        from importlib import reload
        import memory_mesh.networking.tunnel as tunnel_mod
        reload(tunnel_mod)
        with patch.object(tunnel_mod, "_get_ngrok", return_value=(mock_ngrok, mock_conf)):
            url = tunnel_mod.start_ngrok_tunnel(8765)
    assert url.startswith("https://")


def test_start_sets_auth_token_when_provided():
    mock_ngrok, mock_conf = _make_mock_ngrok()
    with patch("memory_mesh.networking.tunnel._get_ngrok", return_value=(mock_ngrok, mock_conf)):
        from memory_mesh.networking.tunnel import start_ngrok_tunnel
        start_ngrok_tunnel(8765, auth_token="mytoken")
    mock_ngrok.set_auth_token.assert_called_once_with("mytoken")


def test_start_skips_auth_when_none():
    mock_ngrok, mock_conf = _make_mock_ngrok()
    with patch("memory_mesh.networking.tunnel._get_ngrok", return_value=(mock_ngrok, mock_conf)):
        from memory_mesh.networking.tunnel import start_ngrok_tunnel
        start_ngrok_tunnel(8765, auth_token=None)
    mock_ngrok.set_auth_token.assert_not_called()


def test_stop_calls_kill():
    mock_ngrok, mock_conf = _make_mock_ngrok()
    with patch("memory_mesh.networking.tunnel._get_ngrok", return_value=(mock_ngrok, mock_conf)):
        from memory_mesh.networking.tunnel import stop_ngrok_tunnel
        stop_ngrok_tunnel()
    mock_ngrok.kill.assert_called_once()


def test_stop_survives_exception():
    mock_ngrok, mock_conf = _make_mock_ngrok()
    mock_ngrok.kill.side_effect = RuntimeError("ngrok gone")
    with patch("memory_mesh.networking.tunnel._get_ngrok", return_value=(mock_ngrok, mock_conf)):
        from memory_mesh.networking.tunnel import stop_ngrok_tunnel
        stop_ngrok_tunnel()  # must not raise


def test_start_raises_helpful_error_if_pyngrok_missing():
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name.startswith("pyngrok"):
            raise ImportError("No module named 'pyngrok'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        import importlib
        import memory_mesh.networking.tunnel as tunnel_mod
        importlib.reload(tunnel_mod)
        try:
            tunnel_mod._get_ngrok()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "pip install" in str(e)


def test_windows_config_path_set():
    mock_ngrok, mock_conf = _make_mock_ngrok()
    mock_pyngrok_config_instance = MagicMock()
    mock_conf.PyngrokConfig.return_value = mock_pyngrok_config_instance

    with patch("memory_mesh.networking.tunnel._get_ngrok", return_value=(mock_ngrok, mock_conf)):
        from memory_mesh.networking.tunnel import start_ngrok_tunnel
        start_ngrok_tunnel(8765)

    call_kwargs = mock_conf.PyngrokConfig.call_args
    config_path = call_kwargs.kwargs.get("config_path", "") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else "")
    assert ".ngrok2" in str(config_path)
    assert str(config_path).endswith(".ngrok2/ngrok.yml") or "ngrok.yml" in str(config_path)
