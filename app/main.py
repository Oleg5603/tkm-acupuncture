import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from data.meridians import SYMPTOMS, MERIDIANS
from engine import analyze_symptoms, build_protocol, priority_text, analyze_ryodoraku

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SYMPTOM_GROUPS = {
    "Дыхание / Лёгкие": [
        "Кашель", "Одышка", "Частые простуды", "Сухость кожи", "Насморк", "Боль в горле"
    ],
    "Сердце / Нервная система": [
        "Бессонница", "Тревога", "Сердцебиение", "Потливость", "Забывчивость"
    ],
    "ЖКТ": [
        "Вздутие живота", "Тошнота", "Диарея", "Запор", "Снижение аппетита", "Боль в животе"
    ],
    "Почки / Мочеполовая": [
        "Боль в пояснице", "Слабость колен", "Частое мочеиспускание",
        "Отёки", "Звон в ушах", "Выпадение волос"
    ],
    "Печень / Желчный": [
        "Раздражительность", "Боль в правом подреберье", "Головная боль в висках",
        "Нарушение зрения", "Боль в суставах", "Мышечные судороги"
    ],
    "Общие": [
        "Усталость", "Озноб", "Холодные ноги", "Жар ладоней и стоп",
        "Головокружение", "Боль в шее", "Боль в плечах"
    ],
}

# Порядок 12 меридианов для Риодораку
RYO_ORDER = ["P", "GI", "E", "RP", "C", "IG", "V", "R", "MC", "TR", "VB", "F"]

ACTION_COLOR = {
    "тонизация":     "#2ecc71",
    "седация":       "#e74c3c",
    "обезболивание": "#f39c12",
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ТКМ — Подбор акупунктурных точек")
        self.geometry("1200x800")
        self.minsize(960, 640)
        self._checks: dict[str, ctk.BooleanVar] = {}
        self._acute_var = ctk.BooleanVar(value=False)
        self._ryo_vars: dict[str, tuple] = {}   # code -> (left_var, right_var)
        self._build_ui()

    # ─────────────────────────────────── UI ──────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Вкладки
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self._tabs.add("🩺 По жалобам")
        self._tabs.add("📊 Риодораку")
        self._tabs.set("🩺 По жалобам")

        # Панель результата (общая для обоих вкладок)
        result_outer = ctk.CTkFrame(self, fg_color="#131c28")
        result_outer.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        result_outer.grid_columnconfigure(0, weight=1)
        result_outer.grid_rowconfigure(1, weight=1)

        self._priority_label = ctk.CTkLabel(
            result_outer,
            text="Выберите симптомы или введите данные Риодораку",
            font=ctk.CTkFont(size=13),
            text_color="#5a7a9a",
            justify="left",
            wraplength=1100,
        )
        self._priority_label.grid(row=0, column=0, sticky="w", padx=14, pady=(8, 2))

        self._result_frame = ctk.CTkScrollableFrame(
            result_outer, fg_color="#131c28",
            label_text="Протокол точек", height=320
        )
        self._result_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        self._build_symptoms_tab()
        self._build_ryodoraku_tab()

    def _build_symptoms_tab(self):
        tab = self._tabs.tab("🩺 По жалобам")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=240)
        scroll.grid(row=0, column=0, sticky="nsew")

        for group, symptoms in SYMPTOM_GROUPS.items():
            ctk.CTkLabel(
                scroll, text=group,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#7a9bb5"
            ).pack(anchor="w", padx=8, pady=(10, 2))
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(anchor="w", padx=16, fill="x")
            for i, s in enumerate(symptoms):
                var = ctk.BooleanVar(value=False)
                self._checks[s] = var
                ctk.CTkCheckBox(
                    frame, text=s, variable=var, command=self._update_symptoms,
                    font=ctk.CTkFont(size=13), width=260
                ).grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=2)

        bottom = ctk.CTkFrame(scroll, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(12, 4))
        ctk.CTkCheckBox(
            bottom, text="⚡ Острая боль / спазм (добавить Xi-точки)",
            variable=self._acute_var, command=self._update_symptoms,
            font=ctk.CTkFont(size=13), text_color="#f39c12"
        ).pack(side="left")
        ctk.CTkButton(
            bottom, text="Очистить", command=self._clear_symptoms,
            fg_color="#3a4a5a", hover_color="#4a5a6a", width=100
        ).pack(side="right")

    def _build_ryodoraku_tab(self):
        tab = self._tabs.tab("📊 Риодораку")
        tab.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ctk.CTkLabel(tab, text="Введите показатели (мкА) для каждого меридиана:",
                     font=ctk.CTkFont(size=13), text_color="#aac4e0"
                     ).grid(row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(6, 4))
        ctk.CTkLabel(tab, text="Меридиан",   font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=0, padx=4)
        ctk.CTkLabel(tab, text="Левая",      font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=1, padx=4)
        ctk.CTkLabel(tab, text="Правая",     font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=2, padx=4)
        ctk.CTkLabel(tab, text="Меридиан",   font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=3, padx=4)
        ctk.CTkLabel(tab, text="Левая",      font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=4, padx=4)
        ctk.CTkLabel(tab, text="Правая",     font=ctk.CTkFont(size=12, weight="bold"), text_color="#7a9bb5"
                     ).grid(row=1, column=5, padx=4)

        # 12 меридианов в 2 столбца (по 6)
        for i, code in enumerate(RYO_ORDER):
            col_offset = (i // 6) * 3
            row = (i % 6) + 2
            name = MERIDIANS[code]["name"]
            lv = ctk.StringVar(value="")
            rv = ctk.StringVar(value="")
            self._ryo_vars[code] = (lv, rv)

            ctk.CTkLabel(tab, text=f"{name} ({code})",
                         font=ctk.CTkFont(size=13), anchor="w"
                         ).grid(row=row, column=col_offset, sticky="w", padx=(12, 4), pady=3)
            ctk.CTkEntry(tab, textvariable=lv, width=70, justify="center"
                         ).grid(row=row, column=col_offset + 1, padx=4, pady=3)
            ctk.CTkEntry(tab, textvariable=rv, width=70, justify="center"
                         ).grid(row=row, column=col_offset + 2, padx=4, pady=3)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=8, column=0, columnspan=6, pady=(10, 4))
        ctk.CTkButton(btn_row, text="Анализировать Риодораку",
                      command=self._update_ryodoraku, width=220
                      ).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Очистить", command=self._clear_ryo,
                      fg_color="#3a4a5a", hover_color="#4a5a6a", width=100
                      ).pack(side="left")

    # ─────────────────────────────── логика ──────────────────────────────────

    def _update_symptoms(self):
        selected = [s for s, v in self._checks.items() if v.get()]
        scores = analyze_symptoms(selected)
        protocol = build_protocol(scores, self._acute_var.get())
        self._show_result(scores, protocol)

    def _update_ryodoraku(self):
        values = {}
        for code, (lv, rv) in self._ryo_vars.items():
            try:
                l = float(lv.get().replace(",", "."))
                r = float(rv.get().replace(",", "."))
                values[code] = (l, r)
            except ValueError:
                pass
        if not values:
            self._priority_label.configure(
                text="Введите показатели Риодораку", text_color="#c0392b")
            return
        scores = analyze_ryodoraku(values)
        protocol = build_protocol(scores, False)
        self._show_result(scores, protocol, mode="ryodoraku")

    def _show_result(self, scores: dict, protocol: list, mode: str = "symptoms"):
        self._priority_label.configure(
            text=priority_text(scores) if scores else "Нет данных",
            text_color="#e8f0fe" if scores else "#5a7a9a",
        )
        for w in self._result_frame.winfo_children():
            w.destroy()
        if not protocol:
            ctk.CTkLabel(self._result_frame, text="Нет точек",
                         text_color="#556677").pack(pady=20)
            return
        for p in protocol:
            self._add_card(p)

    def _add_card(self, p: dict):
        color = ACTION_COLOR.get(p["action"], "#888")
        card = ctk.CTkFrame(self._result_frame, fg_color="#1e2d3d", corner_radius=10)
        card.pack(fill="x", padx=4, pady=4)

        top = ctk.CTkFrame(card, fg_color="#243547", corner_radius=8)
        top.pack(fill="x", padx=6, pady=(6, 2))

        ctk.CTkLabel(top, text=f"  {p['point']}",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=color).pack(side="left", padx=6, pady=5)
        ctk.CTkLabel(top,
                     text=f"{p['name']} ({p['code']})   ·   {p['action'].upper()}",
                     font=ctk.CTkFont(size=13),
                     text_color="#aac4e0").pack(side="left", padx=4, pady=5)

        ctk.CTkLabel(card, text=f"  {p['rule']}",
                     font=ctk.CTkFont(size=12), text_color="#7a9bb5",
                     justify="left", wraplength=900
                     ).pack(anchor="w", padx=10, pady=(0, 6))

    def _clear_symptoms(self):
        for v in self._checks.values():
            v.set(False)
        self._acute_var.set(False)
        self._update_symptoms()

    def _clear_ryo(self):
        for lv, rv in self._ryo_vars.values():
            lv.set("")
            rv.set("")
        for w in self._result_frame.winfo_children():
            w.destroy()
        self._priority_label.configure(
            text="Введите показатели Риодораку", text_color="#5a7a9a")


if __name__ == "__main__":
    App().mainloop()
