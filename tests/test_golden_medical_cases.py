import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from data.diagnoses import DIAGNOSES
from engine import analyze_ryodoraku, analyze_symptoms, build_protocol


SUITE = json.loads(
    (ROOT / "tests" / "fixtures" / "golden_cases_v1.json").read_text(encoding="utf-8")
)


def compact_protocol(protocol):
    return [[p["code"], p["point"], p["action"], p["score"]] for p in protocol]


class GoldenMedicalCasesTests(unittest.TestCase):
    def test_suite_is_release_approved_and_has_exactly_five_cases(self):
        self.assertEqual("approved", SUITE["decision"])
        self.assertEqual("Олег", SUITE["reviewer"])
        self.assertEqual(5, len(SUITE["cases"]))
        self.assertEqual(5, len({case["case_id"] for case in SUITE["cases"]}))

    def test_approved_outputs_are_stable(self):
        for case in SUITE["cases"]:
            with self.subTest(case_id=case["case_id"]):
                input_data = case["input"]
                mode = input_data["mode"]
                if mode == "diagnosis":
                    scores = DIAGNOSES[input_data["diagnosis"]]
                elif mode == "symptoms":
                    scores = analyze_symptoms(input_data.get("symptoms", []))
                elif mode == "ryodoraku":
                    values = {code: tuple(pair) for code, pair in input_data["values"].items()}
                    scores, _ = analyze_ryodoraku(values)
                else:
                    self.fail(f"Unsupported fixture mode: {mode}")

                protocol = build_protocol(scores, input_data.get("acute_pain", False))
                self.assertEqual(case["expected"]["scores"], scores)
                self.assertEqual(case["expected"]["protocol"], compact_protocol(protocol))


if __name__ == "__main__":
    unittest.main()
