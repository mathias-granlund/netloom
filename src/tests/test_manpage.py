from pathlib import Path

from netloom import install_manpage


def test_resolve_target_dir_defaults_to_user_man1(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = install_manpage.resolve_target_dir(None)
    assert target == tmp_path / ".local" / "share" / "man" / "man1"


def test_resolve_target_dir_appends_man1_when_needed(tmp_path):
    target = install_manpage.resolve_target_dir(str(tmp_path / "docs"))
    assert target == tmp_path / "docs" / "man1"


def test_resolve_target_dir_switches_section_when_given_existing_man_dir(tmp_path):
    target = install_manpage.resolve_target_dir(
        str(tmp_path / "docs" / "man1"),
        section="man7",
    )
    assert target == tmp_path / "docs" / "man7"


def test_install_manpage_copies_requested_bundled_file(monkeypatch, tmp_path):
    source = tmp_path / "netloom.1"
    source.write_text(".TH NETLOOM 1\n", encoding="utf-8")
    monkeypatch.setattr(
        install_manpage,
        "bundled_manpage",
        lambda name="netloom.1": source,
    )
    destination = install_manpage.install_manpage(tmp_path)
    assert destination == tmp_path / "man1" / "netloom.1"
    assert destination.read_text(encoding="utf-8") == ".TH NETLOOM 1\n"


def test_install_manpages_copies_all_bundled_files(monkeypatch, tmp_path):
    sources = {
        "netloom.1": tmp_path / "netloom.1",
        "netloom-clearpass.7": tmp_path / "netloom-clearpass.7",
    }
    sources["netloom.1"].write_text(".TH NETLOOM 1\n", encoding="utf-8")
    sources["netloom-clearpass.7"].write_text(
        ".TH NETLOOM-CLEARPASS 7\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        install_manpage,
        "bundled_manpage",
        lambda name="netloom.1": sources[name],
    )
    installed = install_manpage.install_manpages(tmp_path)

    assert installed == [
        tmp_path / "man1" / "netloom.1",
        tmp_path / "man7" / "netloom-clearpass.7",
    ]
    assert (tmp_path / "man7" / "netloom-clearpass.7").read_text(encoding="utf-8") == (
        ".TH NETLOOM-CLEARPASS 7\n"
    )
