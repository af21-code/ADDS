import socket
import json
import time
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
FREQUENCY_HZ = 100  # 100 Hz standard F1 telemetry rate

def stream_adds_telemetry(duration_sec: float = 10.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dt = 1.0 / FREQUENCY_HZ
    steps = int(duration_sec * FREQUENCY_HZ)

    states = ["CONNECTED", "DECOUPLING", "DECOUPLED", "REV_MATCHING", "REENGAGING"]

    print(f"[ADDS UDP Streamer] Streaming telemetry at {FREQUENCY_HZ} Hz to {UDP_IP}:{UDP_PORT}...")

    for step in range(steps):
        t = step * dt
        packet = {
            "timestamp_ms": round(t * 1000, 1),
            "vehicle_speed_kph": round(180.0 + 40.0 * math.sin(t * 0.8), 2),
            "engine_rpm": int(9500 + 2000 * math.sin(t * 0.8)),
            "clutch_slip_rpm": round(abs(150.0 * math.cos(t * 1.5)), 1),
            "fsm_state": states[(step // 150) % len(states)],
            "fuel_saved_pct": round(min(4.5, t * 0.35), 2)
        }
        payload = json.dumps(packet).encode("utf-8")
        sock.sendto(payload, (UDP_IP, UDP_PORT))
        time.sleep(dt)

    print("[ADDS UDP Streamer] Simulation stream completed.")

if __name__ == "__main__":
    stream_adds_telemetry()
