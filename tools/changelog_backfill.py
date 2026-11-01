#!/usr/bin/env python3
#  Project:      dfe-deploy
#  File:         tools/changelog_backfill.py
#  Purpose:      Write the CHANGELOG.md entry for any release tag that has none
#  Language:     Python
#
#  License:      BUSL-1.1
#  Copyright:    (c) 2026 HYPERI PTY LIMITED
"""Add a CHANGELOG.md entry for every release tag the file does not mention.

semantic-release prepends only the release it is cutting, so a release that tagged
but never committed its changelog (the push lost a race, the job died) stays
missing for good. The release workflow runs this after semantic-release: a
complete changelog is left byte for byte as it was, and a gap is filled in the
same shape semantic-release writes. The first tag has no range to render and is
skipped.

Usage:
    python3 tools/changelog_backfill.py --repo hyperi-io/dfe-deploy
"""

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

_HEADING_RE = re.compile(r"^## \[(\d+(?:\.\d+)*)\]", re.MULTILINE)
_SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<text>.+)$")
_PR_RE = re.compile(r" \(#(\d+)\)$")
_GROUPS = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance Improvements",
    "revert": "Reverts",
}
_TAG_RE = re.compile(r"^v(\d+(?:\.\d+)*)$")


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def _line(repo: str, commit: dict) -> str:
    match = _SUBJECT_RE.match(commit["subject"])
    text = match["text"]
    pr = _PR_RE.search(text)
    if pr:
        text = text[: pr.start()]
    scope = f"**{match['scope']}:** " if match["scope"] else ""
    line = f"* {scope}{text}"
    if pr:
        line += f" ([#{pr[1]}](https://github.com/{repo}/issues/{pr[1]}))"
    sha = commit["sha"]
    return f"{line} ([{sha[:7]}](https://github.com/{repo}/commit/{sha}))"


def render_entry(repo: str, prev: str, tag: str, date: str, commits: list[dict]) -> str:
    """One changelog entry, in the layout semantic-release writes."""
    version = tag.removeprefix("v")
    link = f"https://github.com/{repo}/compare/{prev}...{tag}"
    out = [f"## [{version}]({link}) ({date})\n\n"]
    for kind, title in _GROUPS.items():
        lines = [
            _line(repo, c)
            for c in commits
            if (m := _SUBJECT_RE.match(c["subject"])) and m["type"] == kind
        ]
        if lines:
            out.append(f"### {title}\n\n" + "\n".join(lines) + "\n\n")
    return "".join(out)


def _insert(text: str, version: str, entry: str) -> str:
    """Place ``entry`` above the first heading with a lower version, else at the end."""
    for match in _HEADING_RE.finditer(text):
        if _key(match[1]) < _key(version):
            return text[: match.start()] + entry + text[match.start() :]
    return text + ("" if text.endswith("\n\n") else "\n") + entry


def backfill(
    text: str,
    repo: str,
    tags: list[str],
    commits_for: Callable[[str, str], list[dict]],
    date_for: Callable[[str], str],
) -> str:
    """``text`` with an entry added for each tag after the first that it lacks."""
    ordered = sorted((t for t in tags if _TAG_RE.match(t)), key=lambda t: _key(t[1:]))
    for prev, tag in zip(ordered, ordered[1:]):
        version = tag.removeprefix("v")
        if version in {m[1] for m in _HEADING_RE.finditer(text)}:
            continue
        entry = render_entry(repo, prev, tag, date_for(tag), commits_for(prev, tag))
        text = _insert(text, version, entry)
    return text


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def _commits(prev: str, tag: str) -> list[dict]:
    out = _git("log", "--no-merges", "--format=%H%x1f%s", f"{prev}..{tag}")
    rows = (line.split("\x1f", 1) for line in out.splitlines() if line)
    return [{"sha": sha, "subject": subject} for sha, subject in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name, for the links")
    parser.add_argument("--file", default="CHANGELOG.md")
    args = parser.parse_args()

    path = Path(args.file)
    old = path.read_text(encoding="utf-8")
    new = backfill(
        old,
        args.repo,
        _git("tag", "--list", "v[0-9]*").split(),
        commits_for=_commits,
        date_for=lambda tag: _git("log", "-1", "--format=%cs", tag).strip(),
    )
    if new != old:
        path.write_text(new, encoding="utf-8", newline="\n")
        print(f"added missing entries to {path}")
    else:
        print(f"{path} has an entry for every release tag")
    return 0


if __name__ == "__main__":
    sys.exit(main())
