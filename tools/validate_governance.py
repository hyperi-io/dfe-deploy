#!/usr/bin/env python3
#  Project:      dfe-deploy
#  File:         tools/validate_governance.py
#  Purpose:      Structural validation of the governance/ tree (actions + policies)
#  Language:     Python
#
#  License:      BUSL-1.1
#  Copyright:    (c) 2026 HYPERI PTY LIMITED
"""Validate governance/actions/*.yaml and governance/policies/*.yaml.

Mirrors dfe-engine's structural rules (governance/models.py +
gitcrud/commit_policy.py) so a broken action is caught at PR time, before the
engine ever loads it. Deliberately dependency-light: stdlib + PyYAML only.
Chart-path drift is out of scope here - dfe-infra's chart validation owns the
charts these paths point into.

Usage:
    python3 tools/validate_governance.py            # validate ./governance
    python3 tools/validate_governance.py --root x/  # validate x/governance
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# Mirror of dfe-engine gitcrud/commit_policy.py _NAME_RE + validate_name.
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Mirror of the engine registry's governance-prefixed classes (gitcrud/registry.py):
# a defined action may never change these - privilege-escalation guard.
_GOVERNANCE_CLASSES = {
    "accounts",
    "groups",
    "roles",
    "actions",
    "policies",
    "ch_tiers",
    "ch_service_roles",
    "gov_settings",
}

_PARAM_TYPES = {"enum", "int", "float"}


def _name_ok(name: object) -> bool:
    return isinstance(name, str) and bool(name) and ".." not in name and bool(_NAME_RE.fullmatch(name))


def _check_param_spec(pname: str, spec: object, errors: list[str], where: str) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{where}: param '{pname}' must be a mapping")
        return
    ptype = spec.get("type")
    if ptype not in _PARAM_TYPES:
        errors.append(f"{where}: param '{pname}' type must be one of {sorted(_PARAM_TYPES)}")
        return
    values = spec.get("values")
    low, high = spec.get("min"), spec.get("max")
    if ptype == "enum":
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            errors.append(f"{where}: enum param '{pname}' needs a non-empty list of string values")
        if low is not None or high is not None:
            errors.append(f"{where}: enum param '{pname}' may not carry numeric bounds")
    else:
        numeric = (int, float)
        if not isinstance(low, numeric) or not isinstance(high, numeric) or isinstance(low, bool) or isinstance(high, bool):
            errors.append(f"{where}: {ptype} param '{pname}' needs BOTH numeric min and max")
            return
        if low > high:
            errors.append(f"{where}: param '{pname}' bounds are inverted (min > max)")
        if ptype == "int" and (low != int(low) or high != int(high)):
            errors.append(f"{where}: int param '{pname}' bounds must be whole numbers")
        if values is not None:
            errors.append(f"{where}: {ptype} param '{pname}' may not carry enum values")
    default = spec.get("default")
    if default is not None:
        if ptype == "enum" and (not isinstance(values, list) or default not in values):
            errors.append(f"{where}: param '{pname}' default {default!r} is outside its enum values")
        if ptype in ("int", "float") and (
            isinstance(default, bool)
            or not isinstance(default, (int, float))
            or (isinstance(low, (int, float)) and isinstance(high, (int, float)) and not (low <= default <= high))
        ):
            errors.append(f"{where}: param '{pname}' default {default!r} is outside [{low}, {high}]")


def _check_change(idx: int, change: object, params: dict, errors: list[str], where: str) -> None:
    w = f"{where}: changes[{idx}]"
    if not isinstance(change, dict):
        errors.append(f"{w}: must be a mapping")
        return
    for key in ("cls", "name", "path"):
        if not _name_ok(change.get(key)) and key != "path":
            errors.append(f"{w}: '{key}' must be a safe non-empty name")
    cls, path, value = change.get("cls"), change.get("path"), change.get("value")
    if not isinstance(path, str) or not path:
        errors.append(f"{w}: 'path' must be a non-empty dot-path")
        path = ""
    if "value" not in change:
        errors.append(f"{w}: missing 'value'")
    if cls in _GOVERNANCE_CLASSES:
        errors.append(f"{w}: actions may not change the governance class ('{cls}')")
    # Mirror of commit_policy.validate_change: controller-owned + floating refs.
    if path == "replicaCount" or path.endswith(".replicaCount"):
        errors.append(f"{w}: replicaCount is controller-owned (KEDA); use keda.* dials")
    leaf = path.rsplit(".", 1)[-1]
    if leaf in {"tag", "image"} and isinstance(value, str):
        v = value.strip()
        if v == "" or v == "latest" or v.endswith(":latest"):
            errors.append(f"{w}: unpinned/floating image ref {value!r}")
    # Param references: whole-value only, declared, map covers the enum exactly.
    if isinstance(value, dict) and "$param" in value:
        if set(value) - {"$param", "map"}:
            errors.append(f"{w}: a param reference may only carry '$param' and 'map'")
        pname = value.get("$param")
        if pname not in params:
            errors.append(f"{w}: references undeclared param {pname!r}")
        else:
            mapping = value.get("map")
            if mapping is not None:
                spec = params[pname] if isinstance(params[pname], dict) else {}
                if spec.get("type") != "enum":
                    errors.append(f"{w}: 'map' requires an enum param ('{pname}')")
                elif not isinstance(mapping, dict) or set(mapping) != set(spec.get("values") or []):
                    errors.append(f"{w}: 'map' must cover exactly the enum values of '{pname}'")


def _check_action(path: Path, errors: list[str]) -> None:
    where = str(path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        errors.append(f"{where}: not a YAML mapping")
        return
    name = doc.get("name")
    if not _name_ok(name):
        errors.append(f"{where}: 'name' must be a safe non-empty name")
    elif name != path.stem:
        errors.append(f"{where}: name '{name}' must match the filename '{path.stem}'")
    ra = doc.get("required_action")
    if ra is not None and (not isinstance(ra, str) or not ra):
        errors.append(f"{where}: 'required_action' must be a non-empty string when present")
    params = doc.get("params") or {}
    if not isinstance(params, dict):
        errors.append(f"{where}: 'params' must be a mapping")
        params = {}
    for pname, spec in params.items():
        _check_param_spec(str(pname), spec, errors, where)
    changes = doc.get("changes")
    if not isinstance(changes, list) or not changes:
        errors.append(f"{where}: 'changes' must be a non-empty list")
        return
    for idx, change in enumerate(changes):
        _check_change(idx, change, params, errors, where)


def _check_policy(path: Path, errors: list[str]) -> None:
    where = str(path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        errors.append(f"{where}: not a YAML mapping")
        return
    if not _name_ok(doc.get("name")):
        errors.append(f"{where}: 'name' must be a safe non-empty name")
    elif doc["name"] != path.stem:
        errors.append(f"{where}: name '{doc['name']}' must match the filename '{path.stem}'")
    protected = doc.get("protected")
    if not isinstance(protected, list) or not protected:
        errors.append(f"{where}: 'protected' must be a non-empty list")
        return
    for pat in protected:
        if not isinstance(pat, str) or pat.count(":") != 2:
            errors.append(f"{where}: pattern {pat!r} must be 'cls:name:path' (fnmatch globs)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        # NOT cwd. Defaulting to "." meant running this from anywhere but the
        # repo root found no files and printed "OK: 0 action(s)" -- a validator
        # reporting success having checked nothing, which is the exact failure
        # this script exists to catch.
        default=str(Path(__file__).resolve().parent.parent),
        help="repo root holding governance/ (default: this script's repo)",
    )
    args = parser.parse_args()

    gov = Path(args.root) / "governance"
    errors: list[str] = []
    action_files = sorted((gov / "actions").glob("*.yaml")) if (gov / "actions").is_dir() else []
    policy_files = sorted((gov / "policies").glob("*.yaml")) if (gov / "policies").is_dir() else []

    # Nothing to validate is a FAILURE, not a pass. An empty result means the
    # tree moved, the path is wrong, or the files never landed -- all of which
    # must be loud. Silence here would let a broken CI wiring read as green.
    if not action_files and not policy_files:
        print(f"ERROR: no governance files found under {gov}")
        print("Expected governance/actions/*.yaml and/or governance/policies/*.yaml.")
        return 1

    for f in action_files:
        _check_action(f, errors)
    for f in policy_files:
        _check_policy(f, errors)

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\n{len(errors)} error(s) across {len(action_files) + len(policy_files)} file(s)")
        return 1
    print(f"OK: {len(action_files)} action(s) + {len(policy_files)} policy(ies) validate clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
