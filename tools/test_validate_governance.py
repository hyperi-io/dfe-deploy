#  Project:      dfe-deploy
#  File:         tools/test_validate_governance.py
#  Purpose:      Hold validate_governance.py to what the engine's loader refuses
#  Language:     Python
#
#  License:      BUSL-1.1
#  Copyright:    (c) 2026 HYPERI PTY LIMITED
"""Each row is an action file the engine refuses or mis-writes, and the error the validator owes it.

Run from the repo root:

    python3 -m unittest discover -s tools
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "validate_governance", Path(__file__).resolve().parent / "validate_governance.py"
)
vg = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vg)

_CHANGE = "{cls: helmvars, name: dfe-engine-default-values, path: %s, value: %s}"


def _action(
    path: str = "huntRunner.cap",
    value: str = "1",
    cls: str = "helmvars",
    params: str = "",
) -> str:
    change = _CHANGE % (path, value)
    return f"name: x\n{params}changes:\n  - {change.replace('helmvars', cls, 1)}\n"


# (label, action file text, substring the errors must carry, or None for a clean file)
ACTIONS = [
    ("a well-formed action", _action(), None),
    (
        "an int param whose default is not whole",
        _action(
            value="{$param: cap}",
            params="params:\n  cap: {type: int, min: 1, max: 32, default: 4.5}\n",
        ),
        "whole number",
    ),
    (
        "a float param whose default is a whole number",
        _action(
            value="{$param: r}",
            params="params:\n  r: {type: float, min: 0, max: 1, default: 1}\n",
        ),
        None,
    ),
    (
        "a repeated top-level key",
        _action() + "changes:\n  - " + _CHANGE % ("a.b", "1") + "\n",
        "duplicate key",
    ),
    (
        "a path with an empty segment",
        _action(path='"huntRunner..cap"'),
        "empty or padded segment",
    ),
    (
        "a path ending in a dot",
        _action(path='"huntRunner."'),
        "empty or padded segment",
    ),
    (
        "a class the engine does not register",
        _action(cls="helmvar"),
        "unknown resource class",
    ),
    ("an unset marker", _action(value="{$unset: true}"), None),
    (
        "an unset marker that is false",
        _action(value="{$unset: false}"),
        "unset marker is exactly",
    ),
    (
        "an unset marker with a second key",
        _action(value="{$unset: true, x: 1}"),
        "unset marker is exactly",
    ),
    (
        "an unset marker as one branch of a map",
        _action(
            value="{$param: lvl, map: {a: {$unset: true}, b: 4}}",
            params="params:\n  lvl: {type: enum, values: [a, b], default: a}\n",
        ),
        None,
    ),
    (
        "a malformed unset marker inside a map",
        _action(
            value="{$param: lvl, map: {a: {$unset: 1}, b: 4}}",
            params="params:\n  lvl: {type: enum, values: [a, b], default: a}\n",
        ),
        "unset marker is exactly",
    ),
    ("an infra overlay, which the engine registers", _action(cls="infravars"), None),
    ("YAML that does not parse", "name: x\nchanges: [\n", "not loadable YAML"),
    (
        "a merge key with an explicit override",
        (
            "name: x\nchanges:\n"
            "  - &base {cls: helmvars, name: a-default-values, path: a.b, value: 1}\n"
            "  - {<<: *base, path: a.c}\n"
        ),
        None,
    ),
]

POLICIES = [
    ("a well-formed policy", 'name: x\nprotected:\n  - "helmvars:*:image.*"\n', None),
    (
        "a repeated protected key",
        'name: x\nprotected:\n  - "a:b:c"\nprotected:\n  - "a:b:d"\n',
        "duplicate key",
    ),
]


class ValidatorMatchesTheEngineLoader(unittest.TestCase):
    def _errors(self, check, subdir: str, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governance" / subdir / "x.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
            errors: list[str] = []
            check(path, errors)
            return errors

    def test_actions(self) -> None:
        for label, text, owed in ACTIONS:
            with self.subTest(label):
                errors = self._errors(vg._check_action, "actions", text)
                if owed is None:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any(owed in e for e in errors), errors)

    def test_policies(self) -> None:
        for label, text, owed in POLICIES:
            with self.subTest(label):
                errors = self._errors(vg._check_policy, "policies", text)
                if owed is None:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any(owed in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
