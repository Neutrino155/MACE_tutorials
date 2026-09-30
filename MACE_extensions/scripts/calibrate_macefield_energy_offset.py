#!/usr/bin/env python3
"""Remove a constant per-atom energy offset from a fixed-composition MACEField fit.

This leaves forces and field-response derivatives unchanged. The teaching
BaTiO3-like dataset uses one five-atom composition, so its training-set mean
residual is an identifiable scalar baseline correction. Do not use this helper
for a mixed-composition production dataset without species-resolved references.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import os
import tempfile
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

_original_showwarning = warnings.showwarning


def _quiet_user_and_deprecation_warnings(message, category, filename, lineno,
                                         file=None, line=None):
    if issubclass(category, (UserWarning, DeprecationWarning)):
        return
    _original_showwarning(message, category, filename, lineno, file=file, line=line)


warnings.showwarning = _quiet_user_and_deprecation_warnings

import numpy as np
import torch
from ase.io import read
from mace.calculators import MACECalculator


def energy_errors(model_path: Path, frames) -> np.ndarray:
    calculator = MACECalculator(
        model_paths=str(model_path), model_type="MACEField", device="cpu",
        default_dtype="float64", compute_forces=False,
        compute_polarization=False, compute_becs=False,
        compute_polarizability=False,
    )
    errors = []
    for atoms in frames:
        atoms.calc = calculator
        errors.append(
            (atoms.get_potential_energy() - float(atoms.info["REF_energy"]))
            / len(atoms)
        )
    return np.asarray(errors, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--train-file", type=Path, required=True)
    args = parser.parse_args()
    model_path = args.model.resolve()
    frames = read(args.train_file, index=":")
    errors = energy_errors(model_path, frames)
    shift = float(errors.mean())
    rmse_before = float(np.sqrt(np.mean(errors**2)))
    # ScaleShiftBlock adds this scalar once per atom. After subtracting the
    # mean residual from it, every per-atom residual is therefore errors-shift.
    # Compute the corrected RMSE from that exact identity instead of running
    # the whole training set through the model a second time.
    calibrated_errors = errors - shift
    rmse_after = float(np.sqrt(np.mean(calibrated_errors**2)))

    model = torch.load(model_path, map_location="cpu", weights_only=False)
    if not hasattr(model, "scale_shift") or not hasattr(model.scale_shift, "shift"):
        raise TypeError("Expected a MACEField checkpoint with a scalar scale_shift.shift")
    if model.scale_shift.shift.numel() != 1:
        raise ValueError("This fixed-composition teaching correction expects one scalar energy shift")
    with torch.no_grad():
        model.scale_shift.shift.sub_(shift)

    fd, temp_name = tempfile.mkstemp(prefix=f".{model_path.name}.", suffix=".tmp", dir=model_path.parent)
    os.close(fd)
    try:
        torch.save(model, temp_name)
        os.replace(temp_name, model_path)
        os.chmod(model_path, 0o644)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    compiled_path = model_path.with_name(model_path.stem.split("_run-")[0] + "_compiled.model")
    if compiled_path.is_file():
        compiled_path.unlink()  # The CLI export predates this baseline correction.
    print(f"Training-set mean energy residual before correction: {shift:+.8f} eV/atom")
    print(f"Training-set energy RMSE before: {rmse_before*1000:.4f} meV/atom")
    print(f"Training-set energy RMSE after:  {rmse_after*1000:.4f} meV/atom")
    print("Applied correction only to the per-atom energy offset; forces and field derivatives are unchanged.")
    if not compiled_path.exists():
        print("Removed any stale compiled companion; the corrected raw .model is authoritative.")
    print("Model:", model_path)


if __name__ == "__main__":
    main()
