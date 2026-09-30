"""Prepare Colab or local paths for the MACE extension notebooks."""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import site
import subprocess
import sys
import zipfile
import ctypes
from pathlib import Path


TUTORIAL_URL = "https://github.com/Neutrino155/MACE_tutorials.git"
MACEFIELD_URL = "https://github.com/mdi-group/mace-field.git"
MAGNETIC_SOURCE_COMMIT = "1bd205048383a0cae6982cccd687e1837aea717a"
_CUDA_LIBRARY_HANDLES: list[ctypes.CDLL] = []
_CUDA_LIBRARY_DIRS: set[Path] = set()


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


def _clone_colab_sources(feature: str) -> tuple[Path, Path]:
    tutorial = Path("/content/MACE_tutorials")
    if not (tutorial / "MACE_extensions").is_dir():
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", "main", TUTORIAL_URL, str(tutorial)],
            check=True,
        )
    if feature == "magnetic":
        source = Path("/content/mace-field-magnetic")
        if not (source / "mace/modules/extensions.py").is_file():
            source.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "remote", "add", "origin", MACEFIELD_URL], check=True)
            subprocess.run(["git", "-C", str(source), "fetch", "--depth", "1", "origin", MAGNETIC_SOURCE_COMMIT], check=True)
            subprocess.run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"], check=True)
    else:
        source = Path("/content/mace-field-develop")
        if not (source / "mace/modules/extensions.py").is_file():
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", "develop", MACEFIELD_URL, str(source)],
                check=True,
            )
    return tutorial.resolve(), source.resolve()


def _find_local_source(tutorial: Path, feature: str) -> Path:
    candidates = []
    if os.environ.get("MACEFIELD_ROOT"):
        candidates.append(Path(os.environ["MACEFIELD_ROOT"]).expanduser())
    if feature == "magnetic":
        candidates.extend((tutorial.parent / "mace-field-develop", tutorial.parent / "mace-field"))
    else:
        candidates.extend((tutorial.parent / "mace-field-develop", tutorial.parent / "mace-field"))
    for candidate in candidates:
        candidate = candidate.resolve()
        source_file = candidate / "mace/modules/extensions.py"
        models_file = candidate / "mace/modules/models.py"
        if not (source_file.is_file() and models_file.is_file()):
            continue
        if feature == "magnetic" and "class MagneticScaleShiftMACE" not in source_file.read_text():
            continue
        if feature != "magnetic" and "class MACEField" not in source_file.read_text():
            continue
        return candidate
    raise FileNotFoundError(
        "MACE-Field source from origin/develop is required. Clone "
        "https://github.com/mdi-group/mace-field on develop and set MACEFIELD_ROOT to that checkout."
    )


def _install_colab(source: Path, feature: str) -> None:
    if shutil.which("uv") is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
    editable = str(source) + ("[les]" if feature == "les" else "")
    packages = ["--system", "--editable", editable]
    if feature == "magnetic":
        packages.append("sphericart-torch==1.0.9")
    subprocess.run(["uv", "pip", "install", *packages], check=True)


def _extract_teaching_models(tutorial: Path) -> Path:
    asset_root = tutorial / "MACE_extensions"
    model_root = asset_root / "models" / "pretrained_models"
    archive = asset_root / "models" / "pretrained_models.zip"
    needed = (model_root / "models" / "atomicdipoles" / "AtomicDipolesMACE-toy.model",)
    if any(not path.is_file() or archive.stat().st_mtime > path.stat().st_mtime for path in needed):
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(model_root)
    return model_root


def _torch_cuda_version() -> str | None:
    """Read Torch's CUDA build tag without importing Torch into the kernel."""
    try:
        spec = importlib.util.find_spec("torch")
    except (ImportError, ValueError):
        return None
    if not spec or not spec.submodule_search_locations:
        return None
    for package_root in spec.submodule_search_locations:
        version_file = Path(package_root) / "version.py"
        if not version_file.is_file():
            continue
        match = re.search(r"^cuda(?:\s*:\s*Optional\[str\])?\s*=\s*['\"]([^'\"]+)",
                          version_file.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return match.group(1)
    return None


def _prepare_cuda_runtime() -> Path | None:
    """Expose bundled NVRTC libraries to TorchScript JIT kernels.

    CUDA-enabled PyTorch wheels ship NVRTC and its built-ins below
    ``site-packages/nvidia/*/lib``. The NVRTC library may fail to locate its
    companion built-ins when a system CUDA directory takes precedence in
    ``LD_LIBRARY_PATH``. Preloading the matching pair fixes CUDA force and
    response derivatives in an already-running Jupyter kernel; prepending the
    path also gives training subprocesses the same libraries.
    """
    cuda_version = _torch_cuda_version()
    if not cuda_version:
        return None
    major, _, minor = cuda_version.partition(".")
    package_roots = {Path(path).expanduser() for path in site.getsitepackages()}
    package_roots.update(Path(path).expanduser() for path in sys.path if path)
    library_dirs = {
        path.resolve()
        for package_root in package_roots
        for path in (package_root / "nvidia").glob("*/lib")
        if path.is_dir()
    }
    expected_builtins = f"libnvrtc-builtins.so.{major}.{minor}"
    expected_nvrtc = f"libnvrtc.so.{major}"
    selected = next(
        (
            library_dir
            for library_dir in sorted(library_dirs)
            if (library_dir / expected_builtins).is_file()
            and (library_dir / expected_nvrtc).is_file()
        ),
        None,
    )
    if selected is None:
        return None

    current_entries = os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
    if str(selected) not in current_entries:
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(selected), *(entry for entry in current_entries if entry)]
        )
    mode = ctypes.RTLD_GLOBAL
    if selected not in _CUDA_LIBRARY_DIRS:
        _CUDA_LIBRARY_HANDLES.append(ctypes.CDLL(str(selected / expected_builtins), mode=mode))
        _CUDA_LIBRARY_HANDLES.append(ctypes.CDLL(str(selected / expected_nvrtc), mode=mode))
        _CUDA_LIBRARY_DIRS.add(selected)
    return selected


def setup(feature: str = "base") -> dict[str, Path | str]:
    """Set source/data paths, install Colab requirements, and return model paths."""
    if feature not in {"base", "magnetic", "les"}:
        raise ValueError("feature must be 'base', 'magnetic', or 'les'")
    if _is_colab():
        tutorial, source = _clone_colab_sources(feature)
        _install_colab(source, feature)
    else:
        tutorial = _find_tutorial_root()
        source = _find_local_source(tutorial, feature)
    sys.path.insert(0, str(tutorial))
    sys.path.insert(0, str(source))

    assets = tutorial / "MACE_extensions"
    models = _extract_teaching_models(tutorial)
    output: dict[str, Path | str] = {
        "tutorial_root": tutorial,
        "source_root": source,
        "asset_root": assets,
        "model_root": models,
        "dipoles_model": models / "models/atomicdipoles/AtomicDipolesMACE-toy.model",
        "magnetic_model": models / "models/magnetic/MagneticMACE-toy.model",
        "les_model": models / "models/maceles/MACELES-toy.model",
        "les_local_control": models / "models/maceles_short_range/MACELES-short-range-control.model",
    }
    cuda_library_dir = _prepare_cuda_runtime()
    if cuda_library_dir:
        output["cuda_nvrtc_library_dir"] = cuda_library_dir
    print(f"MACE-Field source: {source} · Colab: {_is_colab()}")
    if cuda_library_dir:
        print(f"CUDA NVRTC libraries prepared from: {cuda_library_dir}")
    return output
