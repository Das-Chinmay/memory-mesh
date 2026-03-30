from unittest.mock import MagicMock, patch
import socket
from memory_mesh.networking.mdns import _local_ip, advertise_mdns, stop_mdns


def test_local_ip_returns_string():
    result = _local_ip()
    assert isinstance(result, str)
    assert len(result) > 0


def test_advertise_calls_register():
    mock_zc = MagicMock()
    mock_info = MagicMock()
    with patch("memory_mesh.networking.mdns.Zeroconf", return_value=mock_zc), \
         patch("memory_mesh.networking.mdns.ServiceInfo", return_value=mock_info):
        advertise_mdns(8765)
    mock_zc.register_service.assert_called_once_with(mock_info)


def test_advertise_passes_concrete_ip():
    captured = {}
    mock_zc = MagicMock()

    def fake_service_info(*args, **kwargs):
        captured["addresses"] = kwargs.get("addresses", args[2] if len(args) > 2 else None)
        return MagicMock()

    with patch("memory_mesh.networking.mdns.Zeroconf", return_value=mock_zc), \
         patch("memory_mesh.networking.mdns.ServiceInfo", side_effect=fake_service_info):
        advertise_mdns(8765)

    addrs = captured["addresses"]
    assert isinstance(addrs, list)
    assert len(addrs) == 1
    assert addrs[0] != socket.inet_aton("0.0.0.0")


def test_stop_calls_unregister_and_close():
    mock_zc = MagicMock()
    stop_mdns(mock_zc)
    mock_zc.unregister_all.assert_called_once()
    mock_zc.close.assert_called_once()


def test_stop_survives_exception():
    mock_zc = MagicMock()
    mock_zc.unregister_all.side_effect = RuntimeError("boom")
    # Should not raise
    stop_mdns(mock_zc)
