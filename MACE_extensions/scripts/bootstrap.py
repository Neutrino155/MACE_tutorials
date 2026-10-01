#!/usr/bin/env python3
"""Install optional dependencies for the MACE extension notebooks."""
from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def has(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def install(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", *args], check=True)
    importlib.invalidate_caches()


def _source_root(feature: str, requested: str | Path | None) -> Path:
    if requested is not None:
        return Path(requested).expanduser().resolve()
    if feature == "field":
        explicit = os.environ.get("MACEFIELD_ROOT")
        default = ROOT.parent / "mace-field-develop"
    else:
        explicit = os.environ.get("MACE_ROOT")
        default = ROOT.parent / "mace-upstream-tutorial"
    return Path(explicit).expanduser().resolve() if explicit else default.resolve()


def _is_importing_from(source: Path) -> bool:
    spec = importlib.util.find_spec("mace")
    return bool(
        spec
        and spec.origin
        and Path(spec.origin).resolve().is_relative_to(source)
    )


def _check_loaded_module(source: Path) -> None:
    module = sys.modules.get("mace")
    origin = getattr(module, "__file__", None)
    if origin and not Path(origin).resolve().is_relative_to(source):
        raise RuntimeError(
            f"This kernel already imported MACE from {Path(origin).resolve()}. "
            f"Restart the kernel to switch to {source}."
        )


def _has_sphericart_v2() -> bool:
    try:
        from packaging.version import Version

        return Version(importlib.metadata.version("sphericart-torch")) >= Version("2.0")
    except (importlib.metadata.PackageNotFoundError, ValueError):
        return False


def ensure(feature: str, source_root: str | Path | None = None) -> None:
    """Put the selected MACE checkout first and install its optional extension."""
    if feature == "base":
        feature = "upstream"
    if feature not in {"field", "upstream", "magnetic", "les"}:
        raise ValueError("feature must be 'field', 'upstream', 'magnetic', or 'les'")

    source = _source_root(feature, source_root)
    if not (source / "mace/cli/run_train.py").is_file():
        raise FileNotFoundError(f"MACE source is missing at {source}; rerun the notebook setup cell.")
    sys.path.insert(0, str(source))
    importlib.invalidate_caches()
    _check_loaded_module(source)
    if not _is_importing_from(source):
        install("--editable", str(source))
        importlib.invalidate_caches()
    if not _is_importing_from(source):
        raise ImportError(f"Python is not importing MACE from {source}")

    if feature == "magnetic" and not _has_sphericart_v2():
        install("sphericart-torch>=2.0", "torch-geometric")
    if feature == "les" and not has("les"):
        requirements = source / "requirements" / "les.txt"
        if not requirements.is_file():
            raise FileNotFoundError(f"LES requirements file not found: {requirements}")
        install("--requirement", str(requirements))

    print(f"MACE source ready: {source}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", default="upstream", help="upstream, magnetic, les, or field")
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    ensure(args.feature, args.source_root)


if __name__ == "__main__":
    main()
