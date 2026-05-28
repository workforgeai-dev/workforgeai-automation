import yaml
import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
CALENDAR_PATH = BASE_DIR / "content_calendar.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_calendar():
    with open(CALENDAR_PATH) as f:
        return json.load(f)


def save_calendar(data):
    with open(CALENDAR_PATH, "w") as f:
        json.dump(data, f, indent=2)


def log(module, message, level="INFO"):
    print(f"[{level}] [{module}] {message}")


def truncate_text(text, max_chars=200):
    if len(text) <= max_chars:
        return text
    return text[:max_chars-3] + "..."
