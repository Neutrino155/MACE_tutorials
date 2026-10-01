"""Prepare Colab or local paths for the MACE extension notebooks."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


TUTORIAL_URL = "https://github.com/Neutrino155/MACE_tutorials.git"
MACE_URL = "https://github.com/ACEsuit/mace.git"
MACE_BRANCH = "develop"
MACEFIELD_URL = "https://github.com/mdi-group/mace-field.git"
MACEFIELD_BRANCH = "develop"


def _is_colab() -> bool:
    try:
        return importlib.util.find_spec("google.colab") is not None
    except (ImportError, ValueError):
        # find_spec("google.colab") raises ModuleNotFoundError when the
        # parent `google` package is not installed, which is normal locally.
        return False


def _find_tutorial_root() -> Path:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "MACE_extensions").is_dir():
            return candidate.resolve()
    raise FileNotFoundError("Open this notebook from the MACE_tutorials checkout.")


def _source_is_compatible(source: Path, feature: str) -> bool:
    if feature == "field":
        extensions = source / "mace/modules/extensions.py"
        return extensions.is_file() and "class MACEField" in extensions.read_text()

    models = source / "mace/modules/models.py"
    extensions = source / "mace/modules/extensions.py"
    return (
        models.is_file()
        and "class AtomicDipolesMACE" in models.read_text()
        and extensions.is_file()
        and "class MagneticScaleShiftMACE" in extensions.read_text()
        and "class MACELES" in extensions.read_text()
    )


def _clone_source(source: Path, feature: str) -> None:
    if feature == "field":
        url, branch = MACEFIELD_URL, MACEFIELD_BRANCH
    else:
        url, branch = MACE_URL, MACE_BRANCH
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, str(source)],
        check=True,
    )


def _clone_colab_sources(feature: str) -> tuple[Path, Path]:
    tutorial = Path("/content/MACE_tutorials")
    if not (tutorial / "MACE_extensions").is_dir():
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", "main", TUTORIAL_URL, str(tutorial)],
            check=True,
        )

    source = Path("/content/mace-field-develop" if feature == "field" else "/content/mace-upstream")
    if not _source_is_compatible(source, feature):
        if source.exists():
            raise RuntimeError(
                f"Found an incompatible MACE checkout at {source}; remove it and rerun setup."
            )
        _clone_source(source, feature)
    return tutorial.resolve(), source.resolve()


def _find_local_source(tutorial: Path, feature: str) -> Path:
    if feature == "field":
        explicit = os.environ.get("MACEFIELD_ROOT")
        candidates = [Path(explicit)] if explicit else []
        candidates.extend((tutorial.parent / "mace-field-develop", tutorial.parent / "mace-field"))
        clone_target = tutorial.parent / "mace-field-develop"
    else:
        explicit = os.environ.get("MACE_ROOT")
        candidates = [Path(explicit)] if explicit else []
        candidates.extend((tutorial.parent / "mace-upstream-tutorial", tutorial.parent / "MACE"))
        clone_target = tutorial.parent / "mace-upstream-tutorial"

    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        if _source_is_compatible(candidate, feature):
            return candidate
        if explicit and candidate == Path(explicit).expanduser().resolve():
            raise RuntimeError(
                f"{candidate} does not provide the required {'MACE-Field' if feature == 'field' else 'upstream MACE'} model classes."
            )

    if clone_target.exists():
        raise RuntimeError(
            f"Found an incompatible MACE checkout at {clone_target}; set {'MACEFIELD_ROOT' if feature == 'field' else 'MACE_ROOT'} to a compatible source tree."
        )
    _clone_source(clone_target, feature)
    if not _source_is_compatible(clone_target, feature):
        raise RuntimeError(f"The cloned source does not contain the required models: {clone_target}")
    return clone_target.resolve()


def _install_colab(source: Path, feature: str) -> None:
    if shutil.which("uv") is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
    subprocess.run(["uv", "pip", "install", "--system", "--editable", str(source)], check=True)

    if feature == "magnetic":
        subprocess.run(
            ["uv", "pip", "install", "--system", "sphericart-torch>=2.0", "torch-geometric"],
            check=True,
        )
    if feature == "les":
        requirements = source / "requirements" / "les.txt"
        if not requirements.is_file():
            raise FileNotFoundError(f"LES requirements file not found: {requirements}")
        subprocess.run(
            ["uv", "pip", "install", "--system", "--requirement", str(requirements)],
            check=True,
        )


def _extract_teaching_models(tutorial: Path) -> Path:
    asset_root = tutorial / "MACE_extensions"
    model_root = asset_root / "models" / "pretrained_models"
    archive = asset_root / "models" / "pretrained_models.zip"
    needed = (
        model_root / "models" / "macefield" / "MACEField-toy.model",
        model_root / "models" / "atomicdipoles" / "AtomicDipolesMACE-toy.model",
        model_root / "models" / "magnetic" / "MagneticMACE-toy.model",
        model_root / "models" / "maceles" / "MACELES-toy.model",
        model_root / "models" / "maceles_short_range" / "MACELES-short-range-control.model",
    )
    if not archive.is_file():
        raise FileNotFoundError(f"Pretrained teaching models are missing: {archive}")
    if any(not path.is_file() or archive.stat().st_mtime > path.stat().st_mtime for path in needed):
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(model_root)
    return model_root


def setup(feature: str = "upstream") -> dict[str, Path | str]:
    """Select the appropriate source and return data/model paths.

    ``field`` selects MACE-Field. ``upstream`` (also accepted as ``base``),
    ``magnetic`` and ``les`` select ACEsuit/MACE on its ``develop`` branch.
    """
    aliases = {"base": "upstream"}
    feature = aliases.get(feature, feature)
    if feature not in {"field", "upstream", "magnetic", "les"}:
        raise ValueError("feature must be 'field', 'upstream', 'magnetic', or 'les'")

    if _is_colab():
        tutorial, source = _clone_colab_sources(feature)
        _install_colab(source, feature)
    else:
        tutorial = _find_tutorial_root()
        source = _find_local_source(tutorial, feature)

    sys.path.insert(0, str(source))
    sys.path.insert(0, str(tutorial))
    models = _extract_teaching_models(tutorial)
    output: dict[str, Path | str] = {
        "tutorial_root": tutorial,
        "source_root": source,
        "asset_root": tutorial / "MACE_extensions",
        "model_root": models,
        "macefield_model": models / "models/macefield/MACEField-toy.model",
        "dipoles_model": models / "models/atomicdipoles/AtomicDipolesMACE-toy.model",
        "magnetic_model": models / "models/magnetic/MagneticMACE-toy.model",
        "les_model": models / "models/maceles/MACELES-toy.model",
        "les_local_control": models / "models/maceles_short_range/MACELES-short-range-control.model",
    }
    label = "MACE-Field" if feature == "field" else "upstream MACE"
    print(f"{label} source: {source} · Colab: {_is_colab()}")
    return output
