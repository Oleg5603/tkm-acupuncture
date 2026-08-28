import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

import main as legacy
from engine import recommend_herbs
from tkmp_safety import evaluate_safety
from tkmp_storage import TkmpStorage
from trial import activate_demo, check_trial


def _data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TKMP"
    base.mkdir(parents=True, exist_ok=True)
    return base


class ProfessionalApp(legacy.App):
    def __init__(self):
        self.storage = TkmpStorage(_data_dir() / "tkmp.sqlite3")
        self._patient_by_label = {}
        self._patient_id = None
        self._clinical = {}
        self._safety = evaluate_safety({})
        super().__init__()
        self.title("ТКМП — профессиональный протокол ТКМ")
        self.geometry("1380x940")
        self._install_professional_header()

    def _install_professional_header(self):
        for widget in self.grid_slaves():
            row = int(widget.grid_info().get("row", 0))
            widget.grid_configure(row=row + 1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=2)

        header = ctk.CTkFrame(self, fg_color="#102432", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            header, text="ТКМП", font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#7dd3a7",
        ).grid(row=0, column=0, padx=12, pady=8)
        self._patient_var = ctk.StringVar(value="Пациент не выбран")
        self._patient_menu = ctk.CTkOptionMenu(
            header, variable=self._patient_var, values=["Пациент не выбран"],
            command=self._select_patient, width=300,
        )
        self._patient_menu.grid(row=0, column=1, sticky="w", padx=6)
        for column, (text, command, color) in enumerate((
            ("+ Пациент", self._new_patient, "#17603a"),
            ("Данные случая", self._edit_clinical, "#24506b"),
            ("Травы", self._show_herbs, "#35613e"),
            ("Править протокол", self._edit_protocol, "#2d5263"),
            ("Сохранить визит", self._save_visit, "#614b18"),
            ("История", self._show_history, "#493b63"),
            ("Резервная копия", self._backup, "#3c4650"),
        ), start=2):
            ctk.CTkButton(
                header, text=text, command=command, fg_color=color,
                hover_color="#496170", height=30,
            ).grid(row=0, column=column, padx=3, pady=8)
        self._status = ctk.CTkLabel(
            header, text="Создайте или выберите пациента",
            text_color="#f0c674", anchor="w",
        )
        self._status.grid(row=1, column=0, columnspan=8, sticky="ew", padx=12, pady=(0, 7))
        self._refresh_patients()

    def _refresh_patients(self, select_id=None):
        self._patient_by_label.clear()
        for patient in self.storage.patients():
            label = f"{patient['full_name']} · {patient['age']} лет · #{patient['id']}"
            self._patient_by_label[label] = patient
        values = list(self._patient_by_label) or ["Пациент не выбран"]
        self._patient_menu.configure(values=values)
        if select_id:
            label = next((k for k, v in self._patient_by_label.items() if v["id"] == select_id), values[0])
            self._patient_var.set(label)
            self._select_patient(label)

    def _new_patient(self):
        name = simpledialog.askstring("ТКМП — пациент", "ФИО пациента:", parent=self)
        if not name:
            return
        contact = simpledialog.askstring("ТКМП — пациент", "Телефон или email:", parent=self) or ""
        age = simpledialog.askinteger("ТКМП — пациент", "Возраст:", parent=self, minvalue=1, maxvalue=120)
        if not age:
            return
        consent = messagebox.askyesno(
            "Информированное согласие",
            "Пациент согласен на локальное хранение данных и понимает, что результат — черновик для специалиста?",
            parent=self,
        )
        if not consent:
            messagebox.showwarning("ТКМП", "Без согласия карточка не создаётся.", parent=self)
            return
        patient_id = self.storage.add_patient(name, contact, age)
        self._refresh_patients(patient_id)
        self._edit_clinical()

    def _select_patient(self, label):
        patient = self._patient_by_label.get(label)
        self._patient_id = patient["id"] if patient else None
        if patient:
            self._status.configure(text=f"Пациент: {patient['full_name']}. Заполните данные текущего случая.")

    def _edit_clinical(self):
        if not self._patient_id:
            messagebox.showwarning("ТКМП", "Сначала выберите пациента.", parent=self)
            return
        complaints = simpledialog.askstring(
            "ТКМП — данные случая", "Жалобы и анамнез:",
            initialvalue=self._clinical.get("complaints", ""), parent=self,
        )
        if complaints is None:
            return
        self._clinical["complaints"] = complaints
        for key, question, detail_prompt in (
            ("allergies", "Есть аллергии?", "Перечислите аллергии:"),
            ("medications", "Пациент принимает лекарства?", "Перечислите лекарства:"),
            ("red_flags", "Есть острые состояния или красные флаги?", "Опишите опасные симптомы:"),
        ):
            answer = messagebox.askyesno("ТКМП — данные случая", question, parent=self)
            if answer:
                detail = simpledialog.askstring(
                    "ТКМП — уточнение", detail_prompt,
                    initialvalue="" if self._clinical.get(key) == "нет" else self._clinical.get(key, ""),
                    parent=self,
                )
                if detail is None:
                    return
                self._clinical[key] = detail.strip() or "не уточнено"
            else:
                self._clinical[key] = "нет"
        self._clinical["pregnancy"] = messagebox.askyesno(
            "ТКМП — безопасность", "Есть беременность или лактация?", parent=self,
        )
        self._safety = evaluate_safety(self._clinical)
        if self._safety["blocked"]:
            self._status.configure(
                text="СТОП: обнаружены красные флаги — требуется медицинская оценка.",
                text_color="#ff7777",
            )
        else:
            herbs = "разрешён" if self._safety["herbs_allowed"] else "заблокирован: неполные данные"
            self._status.configure(
                text=f"Данные случая заполнены. Блок трав: {herbs}.", text_color="#8fd19e",
            )
        if self._last_scores:
            self._on_point_count()

    def _show_herbs(self):
        if not self._last_scores:
            messagebox.showinfo(
                "ТКМП — травы", "Сначала выполните анализ и сформируйте протокол.", parent=self,
            )
            return
        self._safety = evaluate_safety(self._clinical)
        if not self._safety.get("herbs_allowed"):
            messagebox.showwarning(
                "ТКМП — травы",
                "Блок трав недоступен: заполните данные случая и исключите красные флаги.",
                parent=self,
            )
            return
        herbs = recommend_herbs(self._last_scores)
        if not herbs:
            messagebox.showinfo("ТКМП — травы", "Для текущего результата травы не найдены.", parent=self)
            return
        lines = []
        for item in herbs:
            lines.extend((
                f"{item['name']} · {item['meridian']}",
                f"Состав: {item['herbs']}",
                f"Важно: {item['caution']}", "",
            ))
        lines.append(
            "Справочная информация. Применение подтверждает специалист после проверки противопоказаний и взаимодействий."
        )
        win = ctk.CTkToplevel(self)
        win.title("ТКМП — рекомендуемые травы")
        win.geometry("820x600")
        win.grab_set()
        text = ctk.CTkTextbox(win, wrap="word", font=ctk.CTkFont(size=13))
        text.pack(fill="both", expand=True, padx=14, pady=14)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")
        ctk.CTkButton(win, text="Закрыть", command=win.destroy).pack(pady=(0, 14))

    def _show_result(self, scores, protocol):
        if not self._patient_id or not self._clinical:
            self._last_protocol = []
            super()._show_result({}, [])
            self._priority_label.configure(text="Сначала выберите пациента и заполните данные случая")
            return
        self._safety = evaluate_safety(self._clinical)
        if self._safety["blocked"]:
            self._last_protocol = []
            super()._show_result({}, [])
            self._priority_label.configure(
                text="СТОП: " + ", ".join(self._safety["detected"]), text_color="#ff6666"
            )
            return
        super()._show_result(scores, protocol)

    def _add_herbs_section(self):
        if self._safety.get("herbs_allowed"):
            super()._add_herbs_section()
        elif self._last_herbs:
            ctk.CTkLabel(
                self._result_frame,
                text="Травы скрыты: заполните аллергии и принимаемые лекарства.",
                text_color="#f0c674",
            ).pack(anchor="w", padx=8, pady=10)
            self._last_herbs = []

    def _save_visit(self):
        if not self._patient_id or not self._last_protocol:
            messagebox.showwarning("ТКМП", "Нет готового протокола для сохранения.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "Подтверждение специалиста",
            "Вы проверили точки, противопоказания и подтверждаете этот протокол?",
            parent=self,
        )
        visit_id = self.storage.save_visit(
            self._patient_id, self._clinical, self._last_scores,
            self._last_protocol, self._last_herbs, confirmed,
        )
        messagebox.showinfo("ТКМП", f"Визит #{visit_id} сохранён.", parent=self)

    def _edit_protocol(self):
        if not self._last_protocol:
            messagebox.showwarning("ТКМП", "Сначала сформируйте протокол.", parent=self)
            return
        items = list(self._last_protocol)
        win = ctk.CTkToplevel(self)
        win.title("ТКМП — ручная проверка протокола")
        win.geometry("760x520")
        win.grab_set()
        box = tk.Listbox(win, font=("Segoe UI", 11), selectmode=tk.SINGLE)
        box.pack(fill="both", expand=True, padx=14, pady=14)

        def redraw(selected=0):
            box.delete(0, "end")
            for i, item in enumerate(items, 1):
                box.insert("end", f"{i}. {item['point']} · {item['name']} · {item['action']}")
            if items:
                box.selection_set(min(selected, len(items) - 1))

        def move(delta):
            if not box.curselection():
                return
            index = box.curselection()[0]
            target = index + delta
            if 0 <= target < len(items):
                items[index], items[target] = items[target], items[index]
                redraw(target)

        def remove():
            if box.curselection() and len(items) > 1:
                index = box.curselection()[0]
                items.pop(index)
                redraw(max(0, index - 1))

        def apply_changes():
            self._last_protocol = items
            self._show_result(self._last_scores, self._last_protocol)
            win.destroy()

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(pady=(0, 12))
        for label, command in (("↑ Выше", lambda: move(-1)), ("↓ Ниже", lambda: move(1)),
                               ("Удалить", remove), ("Применить", apply_changes)):
            ctk.CTkButton(row, text=label, command=command, width=120).pack(side="left", padx=5)
        redraw()

    def _save_word(self):
        if not self._patient_id:
            messagebox.showwarning("ТКМП", "Пациент не выбран.", parent=self)
            return
        from engine import generate_tcm_explanation
        from word_export import generate_word
        patient = next(v for v in self._patient_by_label.values() if v["id"] == self._patient_id)
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".docx", initialfile="протокол_ТКМП.docx",
            filetypes=[("Word документ", "*.docx")],
        )
        if path:
            generate_word(
                self._last_scores, self._last_protocol, self._selected,
                generate_tcm_explanation(self._last_scores, self._last_protocol, self._selected),
                herbs=self._last_herbs, patient=patient, clinical=self._clinical,
                filename=path,
            )

    def _build_report_text(self):
        base = super()._build_report_text()
        if not self._patient_id:
            return base
        patient = next(v for v in self._patient_by_label.values() if v["id"] == self._patient_id)
        header = [
            "ТКМП · ПРОФЕССИОНАЛЬНЫЙ ЧЕРНОВИК",
            f"Пациент: {patient['full_name']} · возраст: {patient['age']}",
            f"Жалобы/анамнез: {self._clinical.get('complaints', '')}",
            f"Аллергии: {self._clinical.get('allergies', '')}",
            f"Лекарства: {self._clinical.get('medications', '')}",
            "Версии: tkmp-engine-1.0 / tkmp-knowledge-1.0",
            "",
        ]
        return "\n".join(header) + base

    def _show_history(self):
        if not self._patient_id:
            return
        visits = self.storage.visits(self._patient_id)
        text = "\n".join(
            f"#{v['id']} · {v['created_at']} · {'подтверждён' if v['confirmed'] else 'черновик'}"
            for v in visits
        ) or "История пуста"
        messagebox.showinfo("ТКМП — история визитов", text, parent=self)

    def _backup(self):
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".sqlite3",
            initialfile="TKMP-backup.sqlite3",
            filetypes=[("Резервная копия ТКМП", "*.sqlite3")],
        )
        if path:
            self.storage.backup(Path(path))
            messagebox.showinfo("ТКМП", "Резервная копия создана.", parent=self)


def run():
    valid, days_left = check_trial()
    if not valid:
        root = ctk.CTk()
        root.withdraw()
        code = simpledialog.askstring(
            "ТКМП — продление",
            "Пробный период 10 дней завершён.\nВведите код активации владельца:",
            show="*", parent=root,
        )
        if not code or not activate_demo(code):
            messagebox.showerror("ТКМП", "Код активации неверен.", parent=root)
            root.destroy()
            return
        root.destroy()
        valid, days_left = check_trial()
    app = ProfessionalApp()
    if days_left == -1:
        app.title(f"{app.title()} — бессрочная лицензия")
    else:
        app.title(f"{app.title()} — осталось {days_left} дн.")
    app.mainloop()


if __name__ == "__main__":
    run()
