RED_FLAG_TERMS = (
    "боль в груди", "потеря сознания", "паралич", "нарушение речи",
    "кровотечение", "кровохарканье", "судороги", "удушье",
    "высокая температура", "острая боль в животе", "суицид",
)


def evaluate_safety(clinical: dict) -> dict:
    text = " ".join([
        clinical.get("complaints", ""),
        clinical.get("red_flags", ""),
    ]).lower()
    detected = [term for term in RED_FLAG_TERMS if term in text]
    missing = []
    for key, label in (
        ("allergies", "аллергии"),
        ("medications", "принимаемые лекарства"),
    ):
        if not clinical.get(key, "").strip():
            missing.append(label)
    return {
        "blocked": bool(detected),
        "detected": detected,
        "herbs_allowed": not detected and not missing,
        "missing": missing,
    }
