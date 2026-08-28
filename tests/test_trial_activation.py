import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import trial


def test_trial_is_valid_for_ten_days(tmp_path, monkeypatch):
    state_path = tmp_path / "trial.json"
    state_path.write_text('{"first_run":"2099-01-01T00:00:00"}', encoding="utf-8")
    monkeypatch.setattr(trial, "_STATE_PATH", str(state_path))

    assert trial.TRIAL_DAYS == 10
    assert trial.check_trial()[0] is True


def test_owner_code_activates_expired_demo_permanently(tmp_path, monkeypatch):
    state_path = tmp_path / "trial.json"
    state_path.write_text('{"first_run":"2000-01-01T00:00:00"}', encoding="utf-8")
    monkeypatch.setattr(trial, "_STATE_PATH", str(state_path))

    assert trial.check_trial() == (False, 0)
    assert not trial.activate_demo("wrong")
    assert trial.activate_demo("0689")
    assert trial.check_trial()[0] is True
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["permanent"] is True
    assert trial.check_trial() == (True, -1)
