#!/usr/bin/env python3
"""Thermal Guard v2 — keeps Pi 5 cool without requiring root"""
import subprocess, time, os
from pathlib import Path

BASE = os.path.expanduser("~/automation")
LOG = f"{BASE}/logs/thermal.log"
MAX_TEMP = 72

def read_temp():
    try:
        p = Path("/sys/class/thermal/thermal_zone0/temp")
        return int(p.read_text().strip()) // 1000
    except:
        return 0

def set_governor(gov):
    for cpu in range(4):
        try:
            p = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
            p.write_text(gov)
        except PermissionError:
            pass  # Not root, that's fine

def set_ollama_threads(n):
    home = os.path.expanduser("~")
    env_file = f"{home}/.ollama/environment"
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    with open(env_file, "w") as f:
        f.write(f"OLLAMA_NUM_THREADS={n}\n")

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

if __name__ == "__main__":
    temp = read_temp()
    gov = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()

    if temp > 78:
        log(f"🔥 CRITICAL: {temp}C > 78C - emergency powersave")
        set_ollama_threads(1)
        if gov != "powersave":
            set_governor("powersave")
    elif temp > MAX_TEMP:
        log(f"⚠️  HIGH: {temp}C > {MAX_TEMP}C - limiting Ollama threads")
        set_ollama_threads(2)
    else:
        log(f"✅ OK: {temp}C (gov={gov}) - nominal")
        set_ollama_threads(2)

    print(f"[Thermal] {temp}C - {gov}")
