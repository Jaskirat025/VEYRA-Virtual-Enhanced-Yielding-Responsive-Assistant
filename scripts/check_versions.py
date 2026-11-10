#!/usr/bin/env python3
"""Check that every version manifest agrees and optionally matches a release tag."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_VERSION = re.compile(r'__version__\s*=\s*"([^"]+)"')


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_cargo_lock_version() -> str:
    data = tomllib.loads((ROOT / "src-tauri/Cargo.lock").read_text(encoding="utf-8"))
    package = next((item for item in data["package"] if item["name"] == "veyra"), None)
    if package is None:
        raise ValueError("src-tauri/Cargo.lock does not contain the veyra package")
    return str(package["version"])


def collect_versions() -> dict[str, str]:
    backend_source = (ROOT / "backend/__init__.py").read_text(encoding="utf-8")
    match = BACKEND_VERSION.search(backend_source)
    if match is None:
        raise ValueError("backend/__init__.py does not define __version__")
    cargo = tomllib.loads((ROOT / "src-tauri/Cargo.toml").read_text(encoding="utf-8"))
    return {
        "package.json": str(load_json("package.json")["version"]),
        "package-lock.json": str(load_json("package-lock.json")["version"]),
        "package-lock.json (root package)": str(
            load_json("package-lock.json")["packages"][""]["version"]
        ),
        "ui/package.json": str(load_json("ui/package.json")["version"]),
        "ui/package-lock.json": str(load_json("ui/package-lock.json")["version"]),
        "ui/package-lock.json (root package)": str(
            load_json("ui/package-lock.json")["packages"][""]["version"]
        ),
        "src-tauri/Cargo.toml": str(cargo["package"]["version"]),
        "src-tauri/Cargo.lock": load_cargo_lock_version(),
        "src-tauri/tauri.conf.json": str(
            load_json("src-tauri/tauri.conf.json")["version"]
        ),
        "backend/__init__.py": match.group(1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="expected Git tag, for example v1.0.0")
    args = parser.parse_args()

    try:
        versions = collect_versions()
    except (KeyError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"Could not read release versions: {exc}", file=sys.stderr)
        return 1

    if len(set(versions.values())) != 1:
        details = "\n".join(
            f"  {path}: {version}" for path, version in versions.items()
        )
        print(f"Version mismatch:\n{details}", file=sys.stderr)
        return 1

    version = next(iter(versions.values()))
    if args.tag is not None and args.tag != f"v{version}":
        print(
            f"Release tag {args.tag!r} does not match version {version!r} (expected v{version})",
            file=sys.stderr,
        )
        return 1

    print(f"Release version: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
