import json
import os
from datetime import datetime, timedelta

TRIAL_DAYS = 7
_STATE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TKM")
_STATE_PATH = os.path.join(_STATE_DIR, "trial.json")


def _read_state() -> dict | None:
    try:
        with open(_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_state(state: dict) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


def check_trial() -> tuple[bool, int]:
    """Returns (is_valid, days_left). Starts the trial clock on first call."""
    state = _read_state()
    if state is None:
        state = {"first_run": datetime.now().isoformat()}
        _write_state(state)

    first_run = datetime.fromisoformat(state["first_run"])
    expires = first_run + timedelta(days=TRIAL_DAYS)
    days_left = (expires - datetime.now()).days
    is_valid = datetime.now() < expires
    return is_valid, max(days_left, 0)
