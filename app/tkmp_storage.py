import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = 1


class TkmpStorage:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _init_db(self):
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    contact TEXT NOT NULL DEFAULT '',
                    age INTEGER NOT NULL,
                    consent_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL REFERENCES patients(id),
                    created_at TEXT NOT NULL,
                    complaints TEXT NOT NULL,
                    allergies TEXT NOT NULL,
                    medications TEXT NOT NULL,
                    pregnancy INTEGER NOT NULL DEFAULT 0,
                    red_flags TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    knowledge_version TEXT NOT NULL,
                    scores_json TEXT NOT NULL,
                    protocol_json TEXT NOT NULL,
                    herbs_json TEXT NOT NULL,
                    confirmed INTEGER NOT NULL DEFAULT 0
                );
            """)
            con.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )

    def add_patient(self, full_name: str, contact: str, age: int) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO patients(full_name,contact,age,consent_at,created_at) VALUES(?,?,?,?,?)",
                (full_name.strip(), contact.strip(), age, now, now),
            )
            return cur.lastrowid

    def patients(self):
        with self._connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT * FROM patients ORDER BY full_name, id"
            )]

    def save_visit(self, patient_id: int, clinical: dict, scores: dict,
                   protocol: list, herbs: list, confirmed: bool) -> int:
        with self._connect() as con:
            cur = con.execute("""
                INSERT INTO visits(
                    patient_id,created_at,complaints,allergies,medications,pregnancy,
                    red_flags,algorithm_version,knowledge_version,scores_json,
                    protocol_json,herbs_json,confirmed
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                patient_id, datetime.now().isoformat(timespec="seconds"),
                clinical.get("complaints", ""), clinical.get("allergies", ""),
                clinical.get("medications", ""), int(clinical.get("pregnancy", False)),
                clinical.get("red_flags", ""), "tkmp-engine-1.0", "tkmp-knowledge-1.0",
                json.dumps(scores, ensure_ascii=False),
                json.dumps(protocol, ensure_ascii=False),
                json.dumps(herbs, ensure_ascii=False), int(confirmed),
            ))
            return cur.lastrowid

    def visits(self, patient_id: int):
        with self._connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT * FROM visits WHERE patient_id=? ORDER BY id DESC", (patient_id,)
            )]

    def backup(self, target: Path):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, target)
