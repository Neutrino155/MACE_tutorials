#!/usr/bin/env python3
"""Install only the optional dependencies needed by an extension notebook or training script."""
from __future__ import annotations
import argparse
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT.parent / "mace-field-develop"
if not (DEFAULT_SOURCE / "mace/cli/run_train.py").is_file():
    DEFAULT_SOURCE = ROOT.parent / "mace-field"
SOURCE_ROOT = Path(os.environ.get("MACEFIELD_ROOT", DEFAULT_SOURCE)).expanduser().resolve()

def has(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False

def install(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", *args], check=True)
    importlib.invalidate_caches()

def install_editable() -> None:
    if shutil.which("uv") is None:
        install("uv")
    subprocess.run(
        ["uv", "pip", "install", "--system", "--editable", str(SOURCE_ROOT)],
        check=True,
    )
    importlib.invalidate_caches()


def install_les() -> None:
    requirements = SOURCE_ROOT / "requirements" / "les.txt"
    if not requirements.is_file():
        raise FileNotFoundError(f"LES requirements file not found: {requirements}")
    if shutil.which("uv") is None:
        install("uv")
    subprocess.run(
        ["uv", "pip", "install", "--system", "--requirement", str(requirements)],
        check=True,
    )
    importlib.invalidate_caches()
    if not has("les"):
        raise ImportError(
            f"LES requirements installed, but Python cannot import 'les' from {requirements}"
        )

def ensure(feature: str) -> None:
    features = {item.strip().lower() for item in feature.split(",") if item.strip()}
    if "all" in features:
        features = {"base", "magnetic", "les"}
    unknown = features - {"base", "magnetic", "les"}
    if unknown:
        raise ValueError(f"Unknown feature(s): {sorted(unknown)}")
    if "base" in features:
        if not (SOURCE_ROOT / "mace/cli/run_train.py").is_file():
            raise FileNotFoundError(f"Set MACEFIELD_ROOT to the MACE-Field checkout; not found at {SOURCE_ROOT}")
        sys.path.insert(0, str(SOURCE_ROOT))
        importlib.invalidate_caches()
        module_spec = importlib.util.find_spec("mace")
        source_import = bool(
            module_spec and module_spec.origin
            and Path(module_spec.origin).resolve().is_relative_to(SOURCE_ROOT)
        )
        if not source_import:
            install_editable()
    if "magnetic" in features and not has("sphericart"):
        install("sphericart-torch==1.0.9")
    if "les" in features and not has("les"):
        install_les()
    print("Dependencies ready for:", ", ".join(sorted(features)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", default="base", help="base, magnetic, les, or all")
    ensure(parser.parse_args().feature)
if __name__ == "__main__": main()
