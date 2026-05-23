"""
TransportRouter: reads WL_TRANSPORT_PATTERN and instantiates the right transport.

    WL_TRANSPORT_PATTERN   file (ODAG) | pubsub (CDAG) | pushpull (legacy)
"""

import os
import re


def build_transport():
    """Build and return the appropriate transport from environment variables."""
    pattern = os.environ.get("WL_TRANSPORT_PATTERN", "pushpull").lower()

    if pattern == "file":
        from wl.transport.file import FileTransport
        return FileTransport()

    if pattern == "mqtt":
        from wl.transport.mqtt import MqttTransport
        peers: dict[str, str] = {}
        return MqttTransport(peers)

    if pattern == "shared_volume":
        from wl.transport.shared_volume import SharedVolumeTransport
        return SharedVolumeTransport()

    # ZMQ transports (CDAG pubsub, or legacy pushpull)
    from wl.transport.zeromq import ZmqPushPullTransport, ZmqPubSubTransport

    _PEER_RE = re.compile(r"^WL_PEER_([A-Z0-9_]+)$")
    peers: dict[str, str] = {}
    for key, value in os.environ.items():
        m = _PEER_RE.match(key)
        if m:
            peer_name = m.group(1).lower().replace("_", "-")
            peers[peer_name] = value

    if pattern == "pubsub":
        pub_port = int(os.environ.get("WL_PUB_PORT", "5555"))
        return ZmqPubSubTransport(pub_port, peers)
    else:
        recv_port = int(os.environ.get("WL_RECV_PORT", "5555"))
        return ZmqPushPullTransport(recv_port, peers)
