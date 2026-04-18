from __future__ import annotations

from src.services.text_normalization import chunk_text, cleanup_html, extract_ru_xml_value


def test_cleanup_html_removes_tags_and_keeps_breaks() -> None:
    raw = "<p>Проверьте <b>UniVPN</b><br/>и 2MFA</p>"

    assert cleanup_html(raw) == "Проверьте UniVPN\nи 2MFA"


def test_extract_ru_xml_value_returns_russian_branch() -> None:
    raw = "<Root><Ru>Удаленный доступ</Ru><En>Remote access</En></Root>"

    assert extract_ru_xml_value(raw) == "Удаленный доступ"


def test_chunk_text_splits_long_text() -> None:
    text = " ".join(["удаленка"] * 200)

    chunks = chunk_text(text, max_chars=120, overlap_chars=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
