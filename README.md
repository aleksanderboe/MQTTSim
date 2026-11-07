# MQTT Simulator Project

Simulation-based testing framework for embedded systems using MQTT and a
series RLC plant model (see bachelor thesis).

## Architecture

```
Client (C++)  --circuit/setpoint/cmd-->  MQTT Broker  --circuit/setpoint/cmd-->  Simulator (Python)
Client (C++)  <--circuit/state/value--  MQTT Broker  <--circuit/state/value--  Simulator (Python)
```

| Topic | Publisher | Subscriber | QoS | Payload |
|-------|-----------|------------|-----|---------|
| `circuit/setpoint/cmd` | Client | Simulator | 1 | `{"setpoint": <V>}` |
| `circuit/state/value` | Simulator | Client | 1 | `{"time", "value", "setpoint"}` |

The simulator models a series RLC circuit (R = 3 kΩ, L = 2 H, C = 1000 µF)
with forward Euler integration and publishes capacitor voltage as feedback.

## Prerequisites

- MQTT broker on `localhost:1883` (e.g. Mosquitto)
- Python 3 + venv for the simulator
- CMake, C++17, and [vcpkg](https://vcpkg.io) for the client

## Simulator (Python)

```bash
cd simulator
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 simulator.py
```

## Client (C++)

Build with CMake + vcpkg, then run. With no arguments the client steps AO1
through **0 V → 5 V → 10 V** (5 s each), matching the thesis test procedure.

```bash
cd client
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=$HOME/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build
./build/mqtt_app              # default steps: 0 5 10
./build/mqtt_app 0 2.5 5      # custom voltage steps
```
