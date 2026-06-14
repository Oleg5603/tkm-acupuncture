import os, sys, ctypes

# Добавляем папку Valeo чтобы найти gds32.dll
os.add_dll_directory("C:/Valeo_555")

import fdb

try:
    con = fdb.connect(
        dsn="C:/Valeo_555/DATA/valeo.fdb",
        user="SYSDBA",
        password="masterkey"
    )
    cur = con.cursor()

    # Список таблиц
    cur.execute("SELECT RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG=0")
    tables = [r[0].strip() for r in cur.fetchall()]
    print("Таблицы:", tables)

    # Ищем таблицы с жалобами
    for t in tables:
        if any(kw in t.upper() for kw in ["ZHAL", "SYMPTOM", "ZHALO", "COMPLAINT", "DIAGNOS"]):
            print(f"\n=== {t} ===")
            cur.execute(f'SELECT FIRST 20 * FROM "{t}"')
            cols = [d[0] for d in cur.description]
            print("Колонки:", cols)
            for row in cur.fetchall():
                print(row)

    con.close()
except Exception as e:
    print("Ошибка:", e)
