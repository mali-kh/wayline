"""
MQTT transport implementation for Wayline — centralized broker baseline.

All messages route through a single MQTT broker (Mosquitto). This serves
as a comparison point against Wayline's native P2P ZeroMQ transport to
demonstrate the scalability advantage of direct communication.

Topic convention:
    wayline/<cdag-name>/<src-task>/broadcast   — broadcast messages
    wayline/<cdag-name>/<src-task>/to/<target>  — targeted messages

Env vars:
    WL_MQTT_BROKER   — broker address (default: mqtt-broker.wl-system.svc.cluster.local)
    WL_MQTT_PORT     — broker port (default: 1883)
    WL_ODAG_NAME or WL_CDAG_NAME — used as topic prefix
"""

import json
import os
import time
import threading
from typing import Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    raise ImportError("paho-mqtt not installed. Install with: pip install paho-mqtt")


class MqttTransport:
    """
    MQTT-based transport for Wayline evaluation.

    All messages go through a centralized MQTT broker — this is the
    baseline against which we compare Wayline's P2P transport.
    """

    BROADCAST_SUFFIX = "broadcast"

    def __init__(self, peer_endpoints: dict[str, str]) -> None:
        self._task_name = os.environ.get("WL_TASK_NAME", "unknown")
        self._dag_name = os.environ.get("WL_CDAG_NAME", os.environ.get("WL_ODAG_NAME", "unknown"))
        self._broker = os.environ.get("WL_MQTT_BROKER", "mqtt-broker.wl-system.svc.cluster.local")
        self._port = int(os.environ.get("WL_MQTT_PORT", "1883"))
        self._peers = peer_endpoints  # not used for connectivity, just for peer names

        # Message queues per subscription topic.
        self._inbox: dict[str, list[bytes]] = {}
        self._inbox_lock = threading.Lock()
        self._inbox_event = threading.Event()

        # Connect to broker.
        self._client = mqtt.Client(client_id=f"wl-{self._dag_name}-{self._task_name}", protocol=mqtt.MQTTv5)
        self._client.on_message = self._on_message
        self._client.connect(self._broker, self._port, keepalive=60)
        self._client.loop_start()

        # Subscribe to broadcast and targeted topics for this task.
        self._client.subscribe(f"wayline/{self._dag_name}/+/{self.BROADCAST_SUFFIX}", qos=0)
        self._client.subscribe(f"wayline/{self._dag_name}/+/to/{self._task_name}", qos=0)

        time.sleep(0.3)  # let subscriptions propagate

    def _on_message(self, client, userdata, msg):
        """Callback: route incoming message to the right inbox."""
        # Extract source task from topic: wayline/<dag>/<src>/broadcast or wayline/<dag>/<src>/to/<target>
        parts = msg.topic.split("/")
        if len(parts) >= 3:
            src_task = parts[2]
        else:
            src_task = "unknown"

        with self._inbox_lock:
            if src_task not in self._inbox:
                self._inbox[src_task] = []
            self._inbox[src_task].append(msg.payload)
        self._inbox_event.set()

    # -- Legacy send/recv interface (backward compat) -------------------------

    def send(self, payload: bytes) -> None:
        """Publish broadcast."""
        topic = f"wayline/{self._dag_name}/{self._task_name}/{self.BROADCAST_SUFFIX}"
        self._client.publish(topic, payload, qos=0)

    def recv(self, peer: str | None = None) -> bytes:
        """Receive one message from a specific peer."""
        if peer is None:
            raise ValueError("MQTT transport requires a peer name for recv()")
        while True:
            with self._inbox_lock:
                if peer in self._inbox and self._inbox[peer]:
                    return self._inbox[peer].pop(0)
            self._inbox_event.clear()
            self._inbox_event.wait(timeout=1.0)

    def recv_all(self) -> dict[str, bytes]:
        raise NotImplementedError("recv_all() is not supported for MQTT transport")

    # -- Streaming API --------------------------------------------------------

    def publish(self, payload: bytes, topic: bytes = b"") -> None:
        """Publish with optional targeting."""
        target = topic.decode() if topic and topic != b"*" else ""
        if target and target != "*":
            mqtt_topic = f"wayline/{self._dag_name}/{self._task_name}/to/{target}"
        else:
            mqtt_topic = f"wayline/{self._dag_name}/{self._task_name}/{self.BROADCAST_SUFFIX}"
        self._client.publish(mqtt_topic, payload, qos=0)

    def subscribe(self, peer: str):
        """Return a pseudo-socket object that has recv_multipart()."""
        return _MqttSubSocket(self, peer)

    def poll_subscribers(self, sockets: dict[str, "_MqttSubSocket"],
                         timeout_ms: int = -1) -> list[tuple[str, bytes]]:
        """Poll multiple subscriptions."""
        deadline = None if timeout_ms < 0 else time.time() + timeout_ms / 1000.0
        while True:
            results: list[tuple[str, bytes]] = []
            with self._inbox_lock:
                for name, sock in sockets.items():
                    peer = sock._peer
                    if peer in self._inbox and self._inbox[peer]:
                        results.append((name, self._inbox[peer].pop(0)))
            if results:
                return results
            if deadline and time.time() >= deadline:
                return []
            self._inbox_event.clear()
            self._inbox_event.wait(timeout=0.1)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


class _MqttSubSocket:
    """Adapter to make MQTT subscriptions look like ZMQ sockets for the SDK."""

    def __init__(self, transport: MqttTransport, peer: str):
        self._transport = transport
        self._peer = peer

    def recv_multipart(self, flags: int = 0) -> list[bytes]:
        """Block until a message arrives from this peer."""
        data = self._transport.recv(self._peer)
        # Return as [topic, payload] to match ZMQ multipart format.
        return [self._peer.encode(), data]
