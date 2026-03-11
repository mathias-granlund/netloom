from pathlib import Path

from arapy import install_manpage


def test_resolve_target_dir_defaults_to_user_man1(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = install_manpage.resolve_target_dir(None)
    assert target == tmp_path / ".local" / "share" / "man" / "man1"


def test_resolve_target_dir_appends_man1_when_needed(tmp_path):
    target = install_manpage.resolve_target_dir(str(tmp_path / "docs"))
    assert target == tmp_path / "docs" / "man1"


def test_install_manpage_copies_bundled_file(monkeypatch, tmp_path):
    source = tmp_path / "arapy.1"
    source.write_text(".TH ARAPY 1\n", encoding="utf-8")
    monkeypatch.setattr(install_manpage, "bundled_manpage", lambda: source)
    destination = install_manpage.install_manpage(tmp_path)
    assert destination == tmp_path / "man1" / "arapy.1"
    assert destination.read_text(encoding="utf-8") == ".TH ARAPY 1\n"
