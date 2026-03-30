import json
from unittest.mock import MagicMock, patch
from memory_mesh.networking.tailscale import get_tailscale_ip, tailscale_status


def _mock_run(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_get_ip_returns_ip_when_running():
    with patch("subprocess.run", return_value=_mock_run(returncode=0, stdout="100.64.0.1\n")):
        result = get_tailscale_ip()
    assert result == "100.64.0.1"


def test_get_ip_returns_none_on_nonzero():
    with patch("subprocess.run", return_value=_mock_run(returncode=1, stdout="")):
        result = get_tailscale_ip()
    assert result is None


def test_get_ip_returns_none_on_exception():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = get_tailscale_ip()
    assert result is None


def test_status_installed_and_running():
    status_json = json.dumps({"BackendState": "Running"})
    with patch("subprocess.run", return_value=_mock_run(returncode=0, stdout=status_json)), \
         patch("memory_mesh.networking.tailscale.get_tailscale_ip", return_value="100.64.0.1"):
        result = tailscale_status()
    assert result["installed"] is True
    assert result["running"] is True
    assert result["ip"] == "100.64.0.1"


def test_status_not_installed():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = tailscale_status()
    assert result["installed"] is False
    assert result["running"] is False
    assert result["ip"] is None


def test_status_dict_has_required_keys():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = tailscale_status()
    assert "installed" in result
    assert "running" in result
    assert "ip" in result
