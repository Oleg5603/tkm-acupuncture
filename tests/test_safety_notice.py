import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from docx import Document
from word_export import SAFETY_NOTICE, generate_word


def test_docx_contains_professional_review_notice():
    payload = generate_word({}, [], [], "")
    document = Document(payload)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert SAFETY_NOTICE in text
    assert "не заменяет диагностику" in text
    assert "проверку квалифицированным специалистом" in text


def test_desktop_ui_contains_same_safety_boundary():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "Справочно-расчётный черновик" in source
    assert "не заменяет диагностику" in source
