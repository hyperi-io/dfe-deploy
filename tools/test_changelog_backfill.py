#  Project:      dfe-deploy
#  File:         tools/test_changelog_backfill.py
#  Purpose:      Hold changelog_backfill.py to the entries semantic-release writes
#  Language:     Python
#
#  License:      BUSL-1.1
#  Copyright:    (c) 2026 HYPERI PTY LIMITED
"""A tag with no CHANGELOG.md entry gets one, and a changelog that is complete is left alone.

Run from the repo root:

    python3 -m unittest discover -s tools
"""

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "changelog_backfill", Path(__file__).resolve().parent / "changelog_backfill.py"
)
cb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cb)

REPO = "hyperi-io/dfe-deploy"
SHA = "09a4e56" + "0" * 33
PREAMBLE = "# Changelog\n\nRendered by CI.\n\n"


def _entry(version: str, prev: str, date: str, body: str = "") -> str:
    link = f"https://github.com/{REPO}/compare/v{prev}...v{version}"
    return f"## [{version}]({link}) ({date})\n\n{body}"


NINE = _entry("1.0.9", "1.0.8", "2026-10-31", "### Bug Fixes\n\n* nine\n\n")
SEVEN = _entry("1.0.7", "1.0.6", "2026-10-06", "### Bug Fixes\n\n* seven\n\n")
FIX = {"sha": SHA, "subject": "fix(hunts): pause the secret group too (#10)"}
DOCS = {"sha": "b" * 40, "subject": "docs: reword the readme"}
FEAT = {"sha": "c" * 40, "subject": "feat: add a dial"}


def _backfill(text: str, tags: list[str], commits: dict[str, list[dict]]) -> str:
    return cb.backfill(
        text,
        REPO,
        tags,
        commits_for=lambda prev, tag: commits.get(tag, []),
        date_for=lambda tag: "2026-10-11",
    )


class BackfillMatchesTheRenderedChangelog(unittest.TestCase):
    def test_missing_entry_lands_between_its_neighbours(self) -> None:
        text = PREAMBLE + NINE + SEVEN
        out = _backfill(text, ["v1.0.6", "v1.0.7", "v1.0.8", "v1.0.9"], {"v1.0.8": [FIX, DOCS]})
        self.assertLess(out.index("## [1.0.9]"), out.index("## [1.0.8]"))
        self.assertLess(out.index("## [1.0.8]"), out.index("## [1.0.7]"))
        self.assertIn(
            f"## [1.0.8](https://github.com/{REPO}/compare/v1.0.7...v1.0.8) (2026-10-11)",
            out,
        )
        self.assertIn(
            f"* **hunts:** pause the secret group too ([#10](https://github.com/{REPO}/issues/10))"
            f" ([09a4e56](https://github.com/{REPO}/commit/{SHA}))",
            out,
        )
        self.assertNotIn("reword the readme", out)

    def test_complete_changelog_is_left_alone(self) -> None:
        text = PREAMBLE + NINE + SEVEN
        self.assertEqual(_backfill(text, ["v1.0.6", "v1.0.7", "v1.0.9"], {}), text)

    def test_second_run_adds_nothing(self) -> None:
        text = PREAMBLE + NINE + SEVEN
        tags = ["v1.0.6", "v1.0.7", "v1.0.8", "v1.0.9"]
        once = _backfill(text, tags, {"v1.0.8": [FIX]})
        self.assertEqual(_backfill(once, tags, {"v1.0.8": [FIX]}), once)

    def test_newest_tag_goes_above_the_rest(self) -> None:
        out = _backfill(PREAMBLE + SEVEN, ["v1.0.6", "v1.0.7", "v1.0.8"], {"v1.0.8": [FEAT]})
        self.assertLess(out.index("# Changelog"), out.index("## [1.0.8]"))
        self.assertLess(out.index("## [1.0.8]"), out.index("## [1.0.7]"))
        self.assertIn("### Features\n\n* add a dial", out)

    def test_the_first_tag_has_no_range_to_render(self) -> None:
        out = _backfill(PREAMBLE, ["v1.0.0"], {"v1.0.0": [FIX]})
        self.assertEqual(out, PREAMBLE)

    def test_versions_compare_as_numbers(self) -> None:
        text = PREAMBLE + _entry("1.0.9", "1.0.8", "2026-10-31") + _entry("1.0.2", "1.0.1", "x")
        out = _backfill(text, ["v1.0.1", "v1.0.2", "v1.0.9", "v1.0.10"], {"v1.0.10": [FIX]})
        self.assertLess(out.index("## [1.0.10]"), out.index("## [1.0.9]"))


if __name__ == "__main__":
    unittest.main()
