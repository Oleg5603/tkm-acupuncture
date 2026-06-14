# Движок анализа ТКМ
from data.meridians import (
    MERIDIANS, SHENG_CYCLE, KO_CYCLE, MIDNIGHT_NOON,
    TONING_SEDATING, YUAN_POINTS, LUO_POINTS, XI_POINTS, SYMPTOMS
)


def analyze_ryodoraku(values: dict[str, tuple]) -> dict:
    """
    values: {код: (левая, правая)} — показатели в мкА.
    Возвращает {код: отклонение_от_среднего} отсортированный по убыванию отклонения.
    """
    all_vals = [v for pair in values.values() for v in pair]
    if not all_vals:
        return {}
    mean = sum(all_vals) / len(all_vals)
    scores = {}
    for code, (l, r) in values.items():
        avg = (l + r) / 2
        deviation = avg - mean   # отрицательное = недостаток, положительное = избыток
        scores[code] = round(abs(deviation), 1)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def analyze_symptoms(selected: list[str]) -> dict:
    """По списку симптомов возвращает словарь {код: суммарный вес}."""
    scores = {}
    for symptom in selected:
        for meridian, weight in SYMPTOMS.get(symptom, {}).items():
            scores[meridian] = scores.get(meridian, 0) + weight
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def get_element_meridians(element: str) -> list[str]:
    return [k for k, v in MERIDIANS.items() if v["element"] == element]


def build_protocol(scores: dict, acute_pain: bool = False) -> list[dict]:
    """
    Строит протокол 4–5 точек на сеанс.
    Приоритет:
      1. Тонизация главного меридиана (обязательно)
      2. Тонизация «матери» главного меридиана (обязательно)
      3. Тонизация второго меридиана (если есть слот)
      4. Полдень-полночь антагонист (только для главного, если балл >= 5)
      5. Xi-точка (только при острой боли, заменяет п.4 если слот занят)
    Итого: не более 5 точек.
    """
    MAX_POINTS = 5
    if not scores:
        return []

    points = []
    seen_pts: set[str] = set()

    def add(code, point, action, rule, score):
        if point not in seen_pts and len(points) < MAX_POINTS:
            seen_pts.add(point)
            m = MERIDIANS[code]
            points.append({
                "code": code,
                "name": m["name"],
                "point": point,
                "action": action,
                "rule": rule,
                "score": score,
            })

    top = list(scores.items())[:2]   # работаем с топ-2 меридианами

    for idx, (code, score) in enumerate(top):
        m = MERIDIANS[code]
        element = m["element"]
        ts = TONING_SEDATING[code]

        # MVP: недостаток по умолчанию (тонизация)
        # 1. Главная точка меридиана
        add(code, ts["тонизация"], "тонизация",
            f"Мать-сын: недостаток {m['name']} — тонизация", score)

        # 2. Точка «матери»
        mother_el = next((k for k, v in SHENG_CYCLE.items() if v == element), None)
        if mother_el:
            for mm in get_element_meridians(mother_el)[:1]:
                add(mm, TONING_SEDATING[mm]["тонизация"], "тонизация",
                    f"Мать-сын: укрепляем «мать» {mother_el} → {m['name']}", score)

        # 3. Полдень-полночь — только для главного меридиана при высоком балле
        if idx == 0 and score >= 5:
            ant = MIDNIGHT_NOON.get(code)
            if ant:
                add(ant, TONING_SEDATING[ant]["тонизация"], "тонизация",
                    f"Полдень-полночь: антагонист {m['name']}", score)

    # 4. Xi-точка при острой боли — для самого главного меридиана
    if acute_pain and top:
        code, score = top[0]
        xi = XI_POINTS.get(code)
        if xi:
            add(code, xi, "обезболивание",
                f"Xi-точка: острая боль / спазм {MERIDIANS[code]['name']}", score)

    return points


def priority_text(scores: dict) -> str:
    """Формирует текст о приоритетном меридиане."""
    if not scores:
        return "Симптомы не выбраны."
    top_code, top_score = list(scores.items())[0]
    m = MERIDIANS[top_code]
    element = m["element"]
    mother_el = next((k for k, v in SHENG_CYCLE.items() if v == element), "—")
    return (
        f"▶ Восстанавливать в первую очередь: {m['name']} ({top_code}) — недостаток\n"
        f"   Элемент: {element}  |  Мать: {mother_el}\n"
        f"   Суммарный балл симптомов: {top_score}"
    )
