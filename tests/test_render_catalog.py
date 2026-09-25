"""The public CATALOG must only link repos that are known to be public."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render_catalog.py"


def load():
    spec = importlib.util.spec_from_file_location("render_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def entry(slug, url, visibility):
    return {"slug": slug, "lifecycle": "active", "sync_status": "published", "tags": [],
            "github_url": url, "visibility": visibility}


def row(table, slug):
    return next(line for line in table.splitlines() if line.startswith(f"| `{slug}` |"))


def test_only_public_repos_get_a_link():
    table = load().render_table([
        entry("pub", "https://github.com/joneshong-skills/pub", "public"),
        entry("priv", "https://github.com/joneshong-skills/cc-skill-priv", "private"),
        entry("unk", "https://github.com/joneshong-skills/unk", "unknown"),
        entry("none", None, None),
    ])
    assert "(https://github.com/joneshong-skills/pub)" in row(table, "pub")
    assert "cc-skill-priv" not in table
    assert "private" in row(table, "priv")
    assert "github.com" not in row(table, "unk")
    assert "github.com" not in row(table, "none")


def test_an_entry_without_visibility_is_not_linked():
    old = {"slug": "legacy", "lifecycle": "active", "sync_status": "published", "tags": [],
           "github_url": "https://github.com/joneshong-skills/cc-skill-legacy"}
    assert "cc-skill-legacy" not in load().render_table([old])


def test_upstream_has_a_badge():
    e = entry("vend", "https://github.com/browser-use/vend", "unknown")
    e["sync_status"] = "upstream"
    assert "| upstream |" not in row(load().render_table([e]), "vend")
