# Движок анализа ТКМ
from data.meridians import (
    MERIDIANS, SHENG_CYCLE, KO_CYCLE, MIDNIGHT_NOON,
    TONING_SEDATING, YUAN_POINTS, LUO_POINTS, XI_POINTS, SYMPTOMS, POINT_TYPES
)
from data.symptoms_extended import SYMPTOMS_EXT
from data.herbs import HERBS_BY_MERIDIAN

_ALL_SYMPTOMS = {**SYMPTOMS_EXT, **SYMPTOMS}   # SYMPTOMS (meridians.py) имеет приоритет

def point_info(point_code: str) -> tuple[str, str]:
    """Возвращает (тип_точки, описание) по коду точки."""
    base = point_code.split(" ")[0]   # берём только код без скобок
    return POINT_TYPES.get(base, ("", ""))


def analyze_ryodoraku(values: dict[str, tuple]) -> tuple[dict, dict]:
    """
    values: {код: (левая, правая)} — показатели в мкА.
    Возвращает:
      scores  — {код: abs_отклонение} для протокола (сортировка по убыванию)
      details — {код: (avg, deviation, mean)} для графика
    """
    all_vals = [v for pair in values.values() for v in pair]
    if not all_vals:
        return {}, {}
    mean = sum(all_vals) / len(all_vals)
    scores = {}
    details = {}
    for code, (l, r) in values.items():
        avg = (l + r) / 2
        deviation = round(avg - mean, 1)   # < 0 = недостаток, > 0 = избыток
        scores[code] = round(abs(deviation), 1)
        details[code] = (round(avg, 1), deviation, round(mean, 1))
    scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    return scores, details


def analyze_symptoms(selected: list[str]) -> dict:
    scores = {}
    for symptom in selected:
        for meridian, weight in _ALL_SYMPTOMS.get(symptom, {}).items():
            scores[meridian] = scores.get(meridian, 0) + weight
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def get_element_meridians(element: str) -> list[str]:
    return [k for k, v in MERIDIANS.items() if v["element"] == element]


def build_protocol(scores: dict, acute_pain: bool = False,
                   point_limit: int | None = 0) -> list[dict]:
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
    if not scores:
        return []

    points = []
    seen_pts: set[str] = set()

    def add(code, point, action, rule, score):
        if point not in seen_pts:
            seen_pts.add(point)
            m = MERIDIANS[code]
            pt_code = point.split(" ")[0]
            ptype, pdesc = point_info(pt_code)
            points.append({
                "code": code,
                "name": m["name"],
                "point": point,
                "action": action,
                "rule": rule,
                "score": score,
                "point_type": ptype,
                "point_desc": pdesc,
            })

    top = list(scores.items())[:2] if point_limit == 0 else list(scores.items())

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

        # 3. Муж-жена (Ко-цикл) — ищем «мужа» который угнетает этот элемент
        if idx == 0:
            husband_el = next((k for k, v in KO_CYCLE.items() if v == element), None)
            if husband_el:
                for hm in get_element_meridians(husband_el)[:1]:
                    add(hm, TONING_SEDATING[hm]["седация"], "седация",
                        f"Муж-жена: снимаем избыток «мужа» {husband_el} → освобождаем {m['name']}", score)

        # 4. Полдень-полночь — только для главного меридиана при высоком балле
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

    effective_limit = 5 if point_limit == 0 else point_limit
    return points if effective_limit is None else points[:effective_limit]


def recommend_herbs(scores: dict, limit: int = 3) -> list[dict]:
    """Справочно подбирает фитокомплексы для ведущих меридианов."""
    result = []
    seen = set()
    for code in scores:
        herb = HERBS_BY_MERIDIAN.get(code)
        if herb and herb["id"] not in seen:
            seen.add(herb["id"])
            result.append({**herb, "meridian": MERIDIANS[code]["name"]})
        if len(result) >= limit:
            break
    return result


def generate_tcm_explanation(scores: dict, protocol: list, selected_symptoms: list) -> str:
    """Генерирует текстовое объяснение принципов ТКМ для данного протокола."""
    if not scores or not protocol:
        return "Выберите симптомы для получения объяснения."

    lines = []
    top_items = list(scores.items())[:3]

    lines.append("═══ АНАЛИЗ СОСТОЯНИЯ ПО ТКМ ═══\n")

    # 1. Симптомы
    if selected_symptoms:
        lines.append(f"Жалобы: {', '.join(selected_symptoms)}\n")

    # 2. Поражённые меридианы и элементы
    lines.append("ПОРАЖЁННЫЕ МЕРИДИАНЫ:")
    for code, score in top_items:
        m = MERIDIANS[code]
        el = m["element"]
        mother_el = next((k for k, v in SHENG_CYCLE.items() if v == el), "—")
        ko_husband = next((k for k, v in KO_CYCLE.items() if v == el), "—")
        lines.append(
            f"  • {m['name']} ({code}) — элемент {el}, балл {score}\n"
            f"    Питающий элемент (Мать): {mother_el}\n"
            f"    Угнетающий элемент (Муж): {ko_husband}"
        )

    # 3. Характер нарушения
    lines.append("\nХАРАКТЕР НАРУШЕНИЯ:")
    top_code = top_items[0][0]
    top_m = MERIDIANS[top_code]
    el = top_m["element"]
    element_pathology = {
        "Дерево":  "Застой ци Печени, нарушение свободного движения ци. Часто — эмоциональный стресс, подавленный гнев.",
        "Огонь":   "Дисбаланс Сердца/Перикарда. Нарушение шэнь (духа). Беспокойство, нарушение сна, сердечно-сосудистые симптомы.",
        "Земля":   "Недостаточность ци Селезёнки/Желудка. Плохое переваривание пищи и «переработка» мыслей, накопление сырости.",
        "Металл":  "Слабость лёгких и защитной ци. Уязвимость к внешним патогенам, кожные и дыхательные проблемы.",
        "Вода":    "Истощение эссенции Почек (цзин). Основа жизненной силы, наследственный потенциал, репродуктивная функция.",
    }
    lines.append(f"  {element_pathology.get(el, '')}")

    # 4. Задействованные правила
    rules_used = set()
    for p in protocol:
        if "Мать-сын" in p["rule"]:
            rules_used.add("Мать-сын (Шэн-цикл)")
        if "Муж-жена" in p["rule"]:
            rules_used.add("Муж-жена (Ко-цикл)")
        if "Полдень-полночь" in p["rule"]:
            rules_used.add("Полдень-полночь (Цзы-у)")
        if "Xi" in p["rule"]:
            rules_used.add("Xi-точки (острая боль)")

    lines.append(f"\nПРИМЕНЁННЫЕ ПРАВИЛА: {', '.join(rules_used)}")

    # 5. Объяснение каждой точки
    lines.append("\nЛОГИКА ВЫБОРА ТОЧЕК:")
    for p in protocol:
        pt = p["point"]
        ptype = p.get("point_type", "")
        pdesc = p.get("point_desc", "")
        lines.append(f"  ▸ {pt} [{p['name']}]")
        if ptype:
            lines.append(f"    Тип: {ptype}")
        lines.append(f"    Правило: {p['rule']}")
        if pdesc:
            lines.append(f"    Действие: {pdesc}")

    # 6. Что корректируем
    lines.append("\nЧТО КОРРЕКТИРУЕМ:")
    for code, score in top_items[:2]:
        m = MERIDIANS[code]
        lines.append(f"  • Восполняем недостаток ци {m['name']} → укрепляем питающий элемент")

    lines.append("\nКРИТЕРИЙ УЛУЧШЕНИЯ:")
    lines.append("  Снижение интенсивности симптомов на 30%+ через 3–5 сеансов.")
    lines.append("  При Риодораку: отклонение меридиана < 15% от среднего уровня.")

    return "\n".join(lines)


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
