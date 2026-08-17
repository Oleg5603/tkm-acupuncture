import json
import os
import hashlib
import hmac
from datetime import datetime, timedelta

TRIAL_DAYS = 7
_STATE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TKM")
_STATE_PATH = os.path.join(_STATE_DIR, "trial.json")
_ACTIVATION_HASH = "3ea542bd251a10948a349b20a641baa667c44d6b1887dacad074da9f1749aff9"


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

    if state.get("activated") is True:
        return True, TRIAL_DAYS

    first_run = datetime.fromisoformat(state["first_run"])
    expires = first_run + timedelta(days=TRIAL_DAYS)
    days_left = (expires - datetime.now()).days
    is_valid = datetime.now() < expires
    return is_valid, max(days_left, 0)


def activate_demo(password: str) -> bool:
    """Activate Demo on this Windows profile when the private code matches."""
    candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(candidate, _ACTIVATION_HASH):
        return False
    state = _read_state() or {"first_run": datetime.now().isoformat()}
    state["activated"] = True
    state["activated_at"] = datetime.now().isoformat()
    _write_state(state)
    return True
