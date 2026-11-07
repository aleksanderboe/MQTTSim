"""
Series RLC circuit simulator for the MQTT-based IPS testing framework.

Subscribes to circuit/setpoint/cmd, integrates the second-order plant with
forward Euler, and publishes capacitor voltage on circuit/state/value.
"""

from __future__ import annotations

import json
import signal
import sys
import time

import paho.mqtt.client as mqtt

# Circuit parameters (Table 3.1)
R = 3000.0          # ohm
L = 2.0             # henry
C = 1000e-6         # farad (1000 uF)

# Numerical / MQTT timing
DT = 0.001                  # integration step [s]
PUBLISH_INTERVAL = 0.025    # state publish period [s]
HOST = "localhost"
PORT = 1883
KEEPALIVE = 30
CLIENT_ID = "RLC_SIMULATOR"
SETPOINT_TOPIC = "circuit/setpoint/cmd"
STATE_TOPIC = "circuit/state/value"
QOS = 1

# Plant state
v_in = 0.0
v_c = 0.0
i_l = 0.0
sim_time = 0.0
time_since_publish = 0.0
_connected = False
_running = True


def on_connect(client, userdata, flags, reason_code, properties):
    global _connected
    if getattr(reason_code, "is_failure", False):
        _connected = False
        print(f"Connection failed: {reason_code}")
        return

    _connected = True
    client.subscribe(SETPOINT_TOPIC, qos=QOS)
    print(f"Connected — subscribed to {SETPOINT_TOPIC}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global _connected
    _connected = False
    print(f"Disconnected: {reason_code}")


def on_message(client, userdata, msg):
    global v_in
    try:
        data = json.loads(msg.payload.decode())
        v_in = float(data["setpoint"])
        print(f"Setpoint updated: {v_in:.3f} V")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
    except (KeyError, TypeError, ValueError) as e:
        print(f"Invalid command: {e}")


def step_circuit() -> None:
    """One forward-Euler step of the series RLC model (Listing 5.1)."""
    global v_c, i_l, sim_time, time_since_publish

    dv_c = i_l / C
    di_l = (v_in - v_c - R * i_l) / L

    v_c += dv_c * DT
    i_l += di_l * DT
    sim_time += DT
    time_since_publish += DT


def maybe_publish(client: mqtt.Client) -> None:
    global time_since_publish

    if time_since_publish < PUBLISH_INTERVAL:
        return

    payload = json.dumps(
        {
            "time": round(sim_time, 2),
            "value": round(v_c, 4),
            "setpoint": v_in,
        }
    )
    # Physics keeps running during broker outages; only publishing pauses.
    if _connected:
        client.publish(STATE_TOPIC, payload, qos=QOS)
    time_since_publish = 0.0


def stop_handler(signum, frame):
    global _running
    _running = False


def main() -> int:
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    client.connect_async(HOST, PORT, KEEPALIVE)
    client.loop_start()

    print(
        f"RLC simulator started "
        f"(R={R} Ω, L={L} H, C={C * 1e6:.0f} µF, dt={DT * 1000:.0f} ms)"
    )
    print(f"Publishing state on {STATE_TOPIC} every {PUBLISH_INTERVAL * 1000:.0f} ms")

    try:
        while _running:
            step_circuit()
            maybe_publish(client)
            time.sleep(DT)
    finally:
        client.loop_stop()
        client.disconnect()
        print("Simulator stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
