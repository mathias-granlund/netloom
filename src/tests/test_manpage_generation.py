from pathlib import Path

from netloom import generate_manpages


def test_generated_manpages_are_current():
    assert generate_manpages.check_manpages() == []


def test_rendered_manpages_cover_all_bundled_roff_targets():
    rendered = generate_manpages.rendered_manpages()
    repo_root = Path(__file__).resolve().parents[2]
    expected = {
        Path("src/netloom/data/man/netloom.1"),
        Path("src/netloom/data/man/netloom-clearpass.7"),
    }
    actual = {path.relative_to(repo_root) for path in rendered}
    assert actual == expected
