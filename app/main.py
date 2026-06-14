import sys, os, tempfile, subprocess, json
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from tkinter import filedialog
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from data.meridians import MERIDIANS
from data.symptom_categories import CATALOG
from data.diagnoses import DIAGNOSES
from engine import (
    analyze_symptoms, build_protocol, priority_text,
    analyze_ryodoraku, generate_tcm_explanation, _ALL_SYMPTOMS
)
from word_export import generate_word

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CUSTOM_PATH = os.path.join(os.path.dirname(__file__), "data", "custom_symptoms.json")

RYO_ORDER = ["P", "GI", "E", "RP", "C", "IG", "V", "R", "MC", "TR", "VB", "F"]

ACTION_COLOR = {
    "тонизация":     "#2ecc71",
    "седация":       "#e74c3c",
    "обезболивание": "#f39c12",
}


def _load_custom() -> dict:
    try:
        with open(CUSTOM_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_custom(data: dict):
    with open(CUSTOM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ТКМ — Подбор акупунктурных точек")
        self.geometry("1280x880")
        self.minsize(1000, 660)

        self._selected: list[str] = []
        self._acute_var = ctk.BooleanVar(value=False)
        self._ryo_vars: dict[str, tuple] = {}
        self._symptom_vars: dict[str, ctk.BooleanVar] = {}
        self._last_scores: dict = {}
        self._last_protocol: list = []
        self._custom: dict = _load_custom()
        self._current_category: str = ""
        self._cat_buttons: dict = {}

        self._build_ui()

    # ──────────────────────────────────────────────────────────── UI ──────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=2)

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self._tabs.add("🩺 По жалобам")
        self._tabs.add("📊 Риодораку")
        self._tabs.add("🏥 Диагнозы")
        self._tabs.set("🩺 По жалобам")

        # ── Панель протокола ──
        result_outer = ctk.CTkFrame(self, fg_color="#131c28")
        result_outer.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        result_outer.grid_columnconfigure(0, weight=1)
        result_outer.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(result_outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        hdr.grid_columnconfigure(0, weight=1)

        self._priority_label = ctk.CTkLabel(
            hdr, text="Выберите симптомы или введите данные Риодораку",
            font=ctk.CTkFont(size=13), text_color="#5a7a9a",
            justify="left", wraplength=760,
        )
        self._priority_label.grid(row=0, column=0, sticky="w")

        btn_bar = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_bar.grid(row=0, column=1, sticky="e")
        for txt, cmd, color, w in [
            ("⛶ Развернуть",    self._expand_protocol,     "#2a2a4a", 120),
            ("📖 Принципы ТКМ", self._show_tcm_principles, "#2a4a2a", 145),
            ("📄 Word",          self._save_word,           "#1a4a2a", 80),
            ("💾 .txt",          self._save_protocol,       "#1a3a5a", 70),
            ("🖨 Печать",        self._print_protocol,      "#3a2a5a", 80),
        ]:
            ctk.CTkButton(btn_bar, text=txt, command=cmd,
                          fg_color=color, hover_color="#4a5a6a",
                          width=w, height=30
                          ).pack(side="left", padx=2)

        self._result_frame = ctk.CTkScrollableFrame(
            result_outer, fg_color="#131c28", label_text="Протокол точек"
        )
        self._result_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        self._build_symptoms_tab()
        self._build_ryodoraku_tab()
        self._build_diagnoses_tab()

    # ─────────────────────────── Вкладка жалоб ───────────────────────────────

    def _build_symptoms_tab(self):
        tab = self._tabs.tab("🩺 По жалобам")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # ── Строка поиска ──
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 2))
        top.grid_columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_symptom_search)
        ctk.CTkEntry(
            top, textvariable=self._search_var,
            placeholder_text="Поиск симптома...",
            font=ctk.CTkFont(size=13), height=32,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            top, text="➕ Добавить свой симптом",
            command=self._add_custom_dialog,
            fg_color="#2a4a2a", hover_color="#3a5a3a", height=32, width=200
        ).grid(row=0, column=1, padx=(0, 6))

        ctk.CTkButton(
            top, text="✕ Снять все",
            command=self._clear_symptoms,
            fg_color="#3a2a2a", hover_color="#4a3a3a", height=32, width=100
        ).grid(row=0, column=2)

        # ── Левая панель: категории ──
        cat_scroll = ctk.CTkScrollableFrame(tab, width=180, fg_color="#0f1a26")
        cat_scroll.grid(row=1, column=0, sticky="ns", padx=(4, 0), pady=2)

        ctk.CTkLabel(cat_scroll, text="Категории",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#5a7a9a").pack(pady=(4, 2))

        btn_all = ctk.CTkButton(
            cat_scroll, text="Все симптомы",
            command=lambda: self._select_category(""),
            fg_color="#1a4a6a", hover_color="#2a5a7a",
            height=28, anchor="w"
        )
        btn_all.pack(fill="x", padx=4, pady=2)
        self._cat_buttons[""] = btn_all

        for name, emoji, _ in CATALOG:
            b = ctk.CTkButton(
                cat_scroll, text=f"{emoji} {name}",
                command=lambda n=name: self._select_category(n),
                fg_color="#1e2d3d", hover_color="#2a3d50",
                height=28, anchor="w"
            )
            b.pack(fill="x", padx=4, pady=1)
            self._cat_buttons[name] = b

        # Мои симптомы
        if self._custom:
            b = ctk.CTkButton(
                cat_scroll, text="🔧 Мои симптомы",
                command=lambda: self._select_category("__custom__"),
                fg_color="#2a3a2a", hover_color="#3a4a3a",
                height=28, anchor="w"
            )
            b.pack(fill="x", padx=4, pady=2)
            self._cat_buttons["__custom__"] = b

        # ── Правая панель: чекбоксы ──
        self._cb_frame = ctk.CTkScrollableFrame(tab, fg_color="#0d1820")
        self._cb_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 4), pady=2)

        # Нижняя строка
        bot = ctk.CTkFrame(tab, fg_color="transparent")
        bot.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 4))
        ctk.CTkCheckBox(
            bot, text="⚡ Острая боль / спазм (добавить Xi-точки)",
            variable=self._acute_var, command=self._recompute,
            font=ctk.CTkFont(size=12), text_color="#f39c12"
        ).pack(side="left")
        self._sel_label = ctk.CTkLabel(
            bot, text="Выбрано: 0",
            font=ctk.CTkFont(size=12), text_color="#5a7a9a"
        )
        self._sel_label.pack(side="right", padx=10)

        # Инициализация
        self._init_symptom_vars()
        self._select_category("")

    def _init_symptom_vars(self):
        """Создаёт BooleanVar для каждого симптома (500 + кастомные)."""
        all_names = set()
        for _, _, syms in CATALOG:
            all_names.update(syms)
        all_names.update(self._custom.keys())

        for name in all_names:
            if name not in self._symptom_vars:
                var = ctk.BooleanVar(value=False)
                var.trace_add("write", lambda *_, n=name: self._on_checkbox(n))
                self._symptom_vars[name] = var

    def _select_category(self, cat_name: str):
        self._current_category = cat_name
        # Подсветка активной кнопки
        for k, b in self._cat_buttons.items():
            b.configure(fg_color="#1a4a6a" if k == cat_name else "#1e2d3d")
        if "" in self._cat_buttons:
            self._cat_buttons[""].configure(
                fg_color="#1a4a6a" if cat_name == "" else "#1e2d3d"
            )
        self._search_var.set("")
        self._render_checkboxes(self._symptoms_for_category(cat_name))

    def _symptoms_for_category(self, cat_name: str) -> list[str]:
        if cat_name == "":
            result = []
            for _, _, syms in CATALOG:
                result.extend(syms)
            result.extend(self._custom.keys())
            return result
        if cat_name == "__custom__":
            return list(self._custom.keys())
        for name, _, syms in CATALOG:
            if name == cat_name:
                return list(syms)
        return []

    def _render_checkboxes(self, symptoms: list[str]):
        for w in self._cb_frame.winfo_children():
            w.destroy()

        if not symptoms:
            ctk.CTkLabel(self._cb_frame, text="Нет симптомов",
                         text_color="#3a5a7a").pack(pady=20)
            return

        cols = 3
        for i, name in enumerate(symptoms):
            row, col = divmod(i, cols)
            if col == 0:
                row_f = ctk.CTkFrame(self._cb_frame, fg_color="transparent")
                row_f.pack(fill="x", padx=4, pady=1)

            var = self._symptom_vars.get(name)
            if var is None:
                var = ctk.BooleanVar(value=False)
                var.trace_add("write", lambda *_, n=name: self._on_checkbox(n))
                self._symptom_vars[name] = var

            is_selected = name in self._selected
            cb = ctk.CTkCheckBox(
                row_f, text=name,
                variable=var,
                font=ctk.CTkFont(size=12),
                text_color="#aad4f5" if is_selected else "#c0c8d0",
                checkbox_width=16, checkbox_height=16,
                width=230,
            )
            cb.pack(side="left", padx=6, pady=2)

    def _on_symptom_search(self, *_):
        q = self._search_var.get().strip().lower()
        if not q:
            self._render_checkboxes(self._symptoms_for_category(self._current_category))
            return
        all_syms = [n for _, _, s in CATALOG for n in s] + list(self._custom.keys())
        matches = [s for s in all_syms if q in s.lower()]
        self._render_checkboxes(matches)

    def _on_checkbox(self, name: str):
        var = self._symptom_vars.get(name)
        if var is None:
            return
        if var.get():
            if name not in self._selected:
                self._selected.append(name)
        else:
            if name in self._selected:
                self._selected.remove(name)
        self._sel_label.configure(text=f"Выбрано: {len(self._selected)}")
        self._recompute()

    def _clear_symptoms(self):
        for name in list(self._selected):
            v = self._symptom_vars.get(name)
            if v:
                v.set(False)
        self._selected.clear()
        self._acute_var.set(False)
        self._sel_label.configure(text="Выбрано: 0")
        self._recompute()

    # ─────────────────────── Добавить свой симптом ───────────────────────────

    def _add_custom_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("Добавить симптом")
        win.geometry("500x420")
        win.grab_set()

        ctk.CTkLabel(win, text="Название симптома:",
                     font=ctk.CTkFont(size=13)).pack(pady=(14, 2))
        name_var = ctk.StringVar()
        ctk.CTkEntry(win, textvariable=name_var, width=360, height=34).pack()

        ctk.CTkLabel(win, text="Связанные меридианы (вес 1–3):",
                     font=ctk.CTkFont(size=12), text_color="#8ab0cc").pack(pady=(10, 4))

        mer_frame = ctk.CTkFrame(win, fg_color="#0f1a26")
        mer_frame.pack(fill="x", padx=14)

        mer_vars: dict[str, tuple[ctk.BooleanVar, ctk.StringVar]] = {}
        order = ["P", "GI", "E", "RP", "C", "IG", "V", "R", "MC", "TR", "VB", "F"]
        for i, code in enumerate(order):
            r, c = divmod(i, 4)
            cell = ctk.CTkFrame(mer_frame, fg_color="transparent")
            cell.grid(row=r, column=c, padx=6, pady=3, sticky="w")
            chk = ctk.BooleanVar()
            wt  = ctk.StringVar(value="2")
            ctk.CTkCheckBox(cell, text=f"{code} {MERIDIANS[code]['name'][:6]}",
                            variable=chk, width=130,
                            font=ctk.CTkFont(size=11)).pack(side="left")
            ctk.CTkOptionMenu(cell, variable=wt, values=["1", "2", "3"],
                              width=48, height=22).pack(side="left", padx=2)
            mer_vars[code] = (chk, wt)

        def save():
            name = name_var.get().strip()
            if not name:
                return
            weights = {code: int(wt.get()) for code, (chk, wt) in mer_vars.items() if chk.get()}
            self._custom[name] = weights
            _save_custom(self._custom)
            # добавить BooleanVar
            if name not in self._symptom_vars:
                var = ctk.BooleanVar(value=False)
                var.trace_add("write", lambda *_, n=name: self._on_checkbox(n))
                self._symptom_vars[name] = var
            # обновить движок
            from engine import _ALL_SYMPTOMS
            _ALL_SYMPTOMS[name] = weights
            win.destroy()
            # добавить кнопку категории если нет
            if "__custom__" not in self._cat_buttons:
                b = ctk.CTkButton(
                    list(self._cat_buttons.values())[0].master,
                    text="🔧 Мои симптомы",
                    command=lambda: self._select_category("__custom__"),
                    fg_color="#2a3a2a", hover_color="#3a4a3a",
                    height=28, anchor="w"
                )
                b.pack(fill="x", padx=4, pady=2)
                self._cat_buttons["__custom__"] = b
            self._select_category("__custom__")

        ctk.CTkButton(win, text="Сохранить", command=save,
                      fg_color="#1a4a2a", width=140, height=34).pack(pady=14)

    # ─────────────────────── Вкладка Риодораку ───────────────────────────────

    def _build_ryodoraku_tab(self):
        tab = self._tabs.tab("📊 Риодораку")
        tab.grid_columnconfigure(0, weight=0)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        input_frame = ctk.CTkFrame(tab, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=4)

        ctk.CTkLabel(input_frame, text="Показатели (мкА):",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#aac4e0"
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 6))

        for col, txt in enumerate(["Меридиан", "Лево", "Право"]):
            ctk.CTkLabel(input_frame, text=txt,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#7a9bb5"
                         ).grid(row=1, column=col, padx=4, pady=2)

        for i, code in enumerate(RYO_ORDER):
            name = MERIDIANS[code]["name"]
            lv, rv = ctk.StringVar(), ctk.StringVar()
            self._ryo_vars[code] = (lv, rv)
            row = i + 2
            ctk.CTkLabel(input_frame, text=f"{name} ({code})",
                         font=ctk.CTkFont(size=12), anchor="w", width=180
                         ).grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
            ctk.CTkEntry(input_frame, textvariable=lv,
                         width=60, justify="center"
                         ).grid(row=row, column=1, padx=3, pady=2)
            ctk.CTkEntry(input_frame, textvariable=rv,
                         width=60, justify="center"
                         ).grid(row=row, column=2, padx=3, pady=2)

        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.grid(row=14, column=0, columnspan=3, pady=(10, 4))
        ctk.CTkButton(btn_row, text="Анализировать",
                      command=self._update_ryodoraku, width=140
                      ).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Очистить",
                      command=self._clear_ryo,
                      fg_color="#3a4a5a", hover_color="#4a5a6a", width=80
                      ).pack(side="left", padx=4)

        graph_frame = ctk.CTkFrame(tab, fg_color="#0f1a26")
        graph_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=4)
        graph_frame.grid_rowconfigure(0, weight=1)
        graph_frame.grid_columnconfigure(0, weight=1)
        self._ryo_graph_frame = graph_frame
        self._ryo_canvas = None
        ctk.CTkLabel(graph_frame,
                     text="График появится после анализа",
                     text_color="#3a5a7a", font=ctk.CTkFont(size=13)
                     ).place(relx=0.5, rely=0.5, anchor="center")

    # ─────────────────────── Вкладка Диагнозы ────────────────────────────────

    def _build_diagnoses_tab(self):
        tab = self._tabs.tab("🏥 Диагнозы")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        top.grid_columnconfigure(0, weight=1)

        self._diag_search_var = ctk.StringVar()
        self._diag_search_var.trace_add("write", self._on_diag_search)
        ctk.CTkEntry(
            top, textvariable=self._diag_search_var,
            placeholder_text="Найти диагноз...",
            font=ctk.CTkFont(size=13), height=32
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(
            top,
            text=f"({len(DIAGNOSES)} диагнозов)",
            font=ctk.CTkFont(size=11), text_color="#5a7a9a"
        ).grid(row=0, column=1)

        self._diag_frame = ctk.CTkScrollableFrame(tab, fg_color="#0d1820")
        self._diag_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))

        self._render_diagnoses(list(DIAGNOSES.keys()))

    def _on_diag_search(self, *_):
        q = self._diag_search_var.get().strip().lower()
        names = [n for n in DIAGNOSES if q in n.lower()] if q else list(DIAGNOSES.keys())
        self._render_diagnoses(names)

    def _render_diagnoses(self, names: list[str]):
        for w in self._diag_frame.winfo_children():
            w.destroy()
        cols = 3
        for i, name in enumerate(sorted(names)):
            if i % cols == 0:
                row_f = ctk.CTkFrame(self._diag_frame, fg_color="transparent")
                row_f.pack(fill="x", padx=4, pady=2)
            ctk.CTkButton(
                row_f, text=name, anchor="w",
                font=ctk.CTkFont(size=12),
                fg_color="#1e2d3d", hover_color="#2a4a6a",
                height=32, width=380,
                command=lambda n=name: self._apply_diagnosis(n)
            ).pack(side="left", padx=4, pady=1)

    def _apply_diagnosis(self, name: str):
        scores = DIAGNOSES[name]
        self._last_scores = scores
        self._last_protocol = build_protocol(scores, False)
        self._priority_label.configure(
            text=f"Диагноз: {name}  |  " + priority_text(scores).split("\n")[0],
            text_color="#e8f0fe"
        )
        for w in self._result_frame.winfo_children():
            w.destroy()
        for p in self._last_protocol:
            self._add_card(p)
        self._tabs.set("🩺 По жалобам")

    # ─────────────────────────── Логика ──────────────────────────────────────

    def _recompute(self):
        scores = analyze_symptoms(self._selected)
        self._last_scores = scores
        self._last_protocol = build_protocol(scores, self._acute_var.get())
        self._show_result(scores, self._last_protocol)

    def _update_ryodoraku(self):
        values = {}
        for code, (lv, rv) in self._ryo_vars.items():
            try:
                values[code] = (
                    float(lv.get().replace(",", ".")),
                    float(rv.get().replace(",", "."))
                )
            except ValueError:
                pass
        if not values:
            self._priority_label.configure(
                text="Введите показатели Риодораку", text_color="#c0392b")
            return
        scores, details = analyze_ryodoraku(values)
        self._last_scores = scores
        self._last_protocol = build_protocol(scores, False)
        self._draw_ryodoraku_chart(details)
        self._show_result(scores, self._last_protocol)

    def _draw_ryodoraku_chart(self, details: dict):
        if self._ryo_canvas:
            self._ryo_canvas.get_tk_widget().destroy()
            plt.close("all")
        ordered = [c for c in RYO_ORDER if c in details]
        names  = [f"{MERIDIANS[c]['name']} ({c})" for c in ordered]
        devs   = [details[c][1] for c in ordered]
        colors = ["#e74c3c" if d > 0 else "#3498db" for d in devs]

        fig, ax = plt.subplots(figsize=(5.5, 4.2))
        fig.patch.set_facecolor("#0f1a26")
        ax.set_facecolor("#0f1a26")
        bars = ax.barh(names, devs, color=colors, height=0.6)
        ax.axvline(0, color="#556677", linewidth=1)
        for bar, dev in zip(bars, devs):
            x = bar.get_width()
            ax.text(x + (0.3 if x >= 0 else -0.3),
                    bar.get_y() + bar.get_height() / 2,
                    f"{dev:+.1f}", va="center",
                    ha="left" if x >= 0 else "right",
                    color="white", fontsize=8)
        ax.set_xlabel("Отклонение от среднего (мкА)", color="#8899aa", fontsize=9)
        ax.tick_params(colors="#aac4e0", labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#223344")
        ax.invert_yaxis()
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(color="#e74c3c", label="Избыток"),
                           Patch(color="#3498db", label="Недостаток")],
                  loc="lower right", facecolor="#1a2d3d",
                  labelcolor="white", fontsize=8, framealpha=0.7)
        fig.tight_layout(pad=0.8)
        canvas = FigureCanvasTkAgg(fig, master=self._ryo_graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._ryo_canvas = canvas

    def _show_result(self, scores: dict, protocol: list):
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

        ptype = p.get("point_type", "")
        if ptype:
            ctk.CTkLabel(top, text=f"[{ptype}]",
                         font=ctk.CTkFont(size=11),
                         text_color="#f0a500").pack(side="left", padx=(0, 6), pady=5)

        ctk.CTkLabel(top,
                     text=f"{p['name']} ({p['code']})   ·   {p['action'].upper()}",
                     font=ctk.CTkFont(size=13),
                     text_color="#aac4e0").pack(side="left", padx=4, pady=5)

        ctk.CTkLabel(card, text=f"  {p['rule']}",
                     font=ctk.CTkFont(size=12), text_color="#7a9bb5",
                     justify="left", wraplength=1100
                     ).pack(anchor="w", padx=10, pady=(0, 3))

        pdesc = p.get("point_desc", "")
        if pdesc:
            ctk.CTkLabel(card, text=f"  ℹ {pdesc}",
                         font=ctk.CTkFont(size=11, slant="italic"),
                         text_color="#5a8aaa", justify="left", wraplength=1100
                         ).pack(anchor="w", padx=10, pady=(0, 6))

    # ───────────────── Принципы ТКМ / Сохранить / Печать ────────────────────

    def _expand_protocol(self):
        """Открывает протокол в отдельном большом окне."""
        win = ctk.CTkToplevel(self)
        win.title("Протокол точек")
        win.geometry("1000x700")
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)

        self._priority_label_exp = ctk.CTkLabel(
            win, text=self._priority_label.cget("text"),
            font=ctk.CTkFont(size=14), text_color="#e8f0fe",
            justify="left", wraplength=940
        )
        self._priority_label_exp.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        sf = ctk.CTkScrollableFrame(win, fg_color="#131c28", label_text="Протокол")
        sf.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        for p in self._last_protocol:
            color = ACTION_COLOR.get(p["action"], "#888")
            card = ctk.CTkFrame(sf, fg_color="#1e2d3d", corner_radius=10)
            card.pack(fill="x", padx=4, pady=4)
            top = ctk.CTkFrame(card, fg_color="#243547", corner_radius=8)
            top.pack(fill="x", padx=6, pady=(6, 2))
            ctk.CTkLabel(top, text=f"  {p['point']}",
                         font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=color).pack(side="left", padx=8, pady=6)
            if p.get("point_type"):
                ctk.CTkLabel(top, text=f"[{p['point_type']}]",
                             font=ctk.CTkFont(size=12), text_color="#f0a500"
                             ).pack(side="left", padx=(0, 8), pady=6)
            ctk.CTkLabel(top,
                         text=f"{p['name']} ({p['code']})   ·   {p['action'].upper()}",
                         font=ctk.CTkFont(size=14), text_color="#aac4e0"
                         ).pack(side="left", padx=4, pady=6)
            ctk.CTkLabel(card, text=f"  {p['rule']}",
                         font=ctk.CTkFont(size=12), text_color="#7a9bb5",
                         justify="left", wraplength=900
                         ).pack(anchor="w", padx=12, pady=(0, 4))
            if p.get("point_desc"):
                ctk.CTkLabel(card, text=f"  ℹ {p['point_desc']}",
                             font=ctk.CTkFont(size=11, slant="italic"),
                             text_color="#5a8aaa", justify="left", wraplength=900
                             ).pack(anchor="w", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.grid(row=2, column=0, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📄 Сохранить Word",
                      command=self._save_word, fg_color="#1a4a2a", width=160
                      ).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Закрыть",
                      command=win.destroy, fg_color="#3a2a2a", width=100
                      ).pack(side="left", padx=6)

    def _save_word(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word документ", "*.docx"), ("Все файлы", "*.*")],
            initialfile="протокол_ТКМ.docx", title="Сохранить Word"
        )
        if not path:
            return
        tcm_text = generate_tcm_explanation(
            self._last_scores, self._last_protocol, self._selected)
        generate_word(
            self._last_scores, self._last_protocol,
            self._selected, tcm_text, filename=path
        )

    def _build_report_text(self) -> str:
        scores   = self._last_scores
        protocol = self._last_protocol
        lines = ["=" * 60, "  ПРОТОКОЛ АКУПУНКТУРНЫХ ТОЧЕК (ТКМ)", "=" * 60, ""]
        if self._selected:
            lines.append(f"Жалобы: {', '.join(self._selected)}\n")
        if not protocol:
            lines.append("Протокол не построен.")
            return "\n".join(lines)
        lines.append("РЕКОМЕНДОВАННЫЕ ТОЧКИ:")
        lines.append("-" * 60)
        for i, p in enumerate(protocol, 1):
            lines.append(f"{i}. Точка {p['point']}  [{p['name']} / {p['code']}]")
            if p.get("point_type"):
                lines.append(f"   Тип: {p['point_type']}")
            lines.append(f"   Действие: {p['action'].upper()}")
            lines.append(f"   Правило: {p['rule']}")
            if p.get("point_desc"):
                lines.append(f"   {p['point_desc']}")
            lines.append("")
        lines += ["=" * 60, "  ПРИНЦИПЫ ТКМ", "=" * 60,
                  generate_tcm_explanation(scores, protocol, self._selected)]
        return "\n".join(lines)

    def _save_protocol(self):
        text = self._build_report_text()
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
            initialfile="протокол_ТКМ.txt", title="Сохранить протокол"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def _print_protocol(self):
        text = self._build_report_text()
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".txt",
            delete=False, prefix="tkm_"
        )
        tmp.write(text)
        tmp.close()
        subprocess.Popen(["notepad", "/p", tmp.name])

    def _show_tcm_principles(self):
        text = generate_tcm_explanation(
            self._last_scores, self._last_protocol, self._selected)
        win = ctk.CTkToplevel(self)
        win.title("Принципы ТКМ")
        win.geometry("800x640")
        win.grab_set()
        ctk.CTkLabel(win, text="Объяснение принципов ТКМ",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#aad4f5").pack(pady=(14, 4))
        txt = ctk.CTkTextbox(win, fg_color="#0f1a26", text_color="#d0e8ff",
                             font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        txt.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        txt.insert("end", text)
        txt.configure(state="disabled")
        ctk.CTkButton(win, text="Закрыть", command=win.destroy,
                      width=100).pack(pady=(0, 12))

    def _clear_ryo(self):
        for lv, rv in self._ryo_vars.values():
            lv.set(""); rv.set("")
        for w in self._result_frame.winfo_children():
            w.destroy()
        self._priority_label.configure(
            text="Введите показатели Риодораку", text_color="#5a7a9a")


if __name__ == "__main__":
    App().mainloop()
