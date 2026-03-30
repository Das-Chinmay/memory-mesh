"""
mDNS advertisement so phones on the same Wi-Fi can find the server
at memory-mesh.local:<port> without knowing the IP address.

Windows/Android/iOS fix: always pass a concrete local IP to ServiceInfo,
never leave addresses blank. Some Android and iOS mDNS resolvers silently
fail when no address hint is provided.
"""
import socket
from zeroconf import ServiceInfo, Zeroconf


def _local_ip() -> str:
    """Return the machine's LAN IP (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def advertise_mdns(port: int, instance_name: str = "memory-mesh") -> Zeroconf:
    """
    Broadcast this machine as `memory-mesh.local:<port>` on the LAN.
    Returns the Zeroconf instance — caller must keep it alive.
    Call stop_mdns() to clean up on shutdown.
    """
    zc = Zeroconf()
    ip = _local_ip()
    info = ServiceInfo(
        "_http._tcp.local.",
        f"{instance_name}._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"version": "0.1.0", "path": "/v1"},
    )
    zc.register_service(info)
    return zc


def stop_mdns(zc: Zeroconf) -> None:
    """Gracefully unregister the mDNS service and close the socket."""
    try:
        zc.unregister_all()
        zc.close()
    except Exception:
        pass  # best-effort on shutdown
