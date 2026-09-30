#!/usr/bin/env python3
"""Check a fitted teaching MACEField model for a double well and path hysteresis.

Example:
    MACEFIELD_ROOT=../mace-field-develop python MACE_extensions/scripts/audit_macefield_surface.py \
        --model /tmp/macefield-energy-force/MACEField-Landau_run-23.model \
        --head Default --out /tmp/macefield-audit

This checks the analytic one-mode teaching system only. A loop with shifted
switching fields is reported as a diagnostic warning, not a script failure.
It is not a BaTiO3 reference-data benchmark.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import root
from ase import Atoms
from scipy.optimize import brentq
from mace.calculators import MACECalculator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from MACE_extensions.scripts.prepare_teaching_data import (
    BTO_LANDAU_BARRIER,
    BTO_MODE_D0,
    BTO_REFERENCE_VOLUME,
    bto_field_stationary_derivatives,
)

CELL_A = 3.90
CELL_C = 4.10
D0 = BTO_MODE_D0
BARRIER_EV = BTO_LANDAU_BARRIER
POLARIZATION_CONVERSION = 1602.176634  # e / A^2 -> microC / cm^2


def bto_probe(displacement: float) -> Atoms:
    scaled = [
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.5],
        [0.5, 0.5, 0.0],
        [0.5, 0.0, 0.5],
        [0.0, 0.5, 0.5],
    ]
    atoms = Atoms("BaTiO3", scaled_positions=scaled, cell=[CELL_A, CELL_A, CELL_C], pbc=True)
    atoms.positions[1, 2] += displacement
    return atoms


def nearest_stable_mode_root(calculator, previous_d: float, bounds=(-0.22, 0.22)) -> float:
    """Continue the nearest stable Ti-mode force root in the trained domain.

    This audit cell has exactly one mobile coordinate. Root continuation avoids
    an unconstrained optimizer jumping into spurious minima outside the toy
    model's displacement range.
    """
    lower, upper = bounds

    def mode_force(displacement: float) -> float:
        atoms = bto_probe(float(displacement))
        atoms.calc = calculator
        return float(atoms.get_forces()[1, 2])

    # Prefer the root nearest the current branch, expanding only as the mode
    # softens and approaches a spinodal.
    widths = (0.005, 0.01, 0.02, 0.04, 0.08, 0.12, 0.18, upper - lower)
    for width in widths:
        left = max(lower, previous_d - width)
        right = min(upper, previous_d + width)
        f_left, f_right = mode_force(left), mode_force(right)
        if f_left == 0.0:
            return left
        if f_right == 0.0:
            return right
        if f_left > 0.0 and f_right < 0.0:
            return float(brentq(mode_force, left, right, xtol=1e-8))

    # If this metastable branch vanished, find all stable roots in the
    # physical training interval and switch to the closest remaining well.
    grid = np.linspace(lower, upper, 45)
    forces = np.array([mode_force(value) for value in grid])
    stable_roots = []
    for index in range(len(grid) - 1):
        if forces[index] > 0.0 and forces[index + 1] < 0.0:
            stable_roots.append(
                float(brentq(mode_force, grid[index], grid[index + 1], xtol=1e-8))
            )
    if not stable_roots:
        raise RuntimeError(
            f"No stable Ti-mode force root inside the training interval {bounds} "
            f"at E={calculator.electric_field[2]:+.5f} V/A"
        )
    return min(stable_roots, key=lambda root: abs(root - previous_d))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--head", default="Default")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", default="float64", choices=("float32", "float64"))
    parser.add_argument("--max-force-rmse-mev", type=float, default=30.0)
    parser.add_argument("--spinodal-tolerance", type=float, default=0.035,
                        help="Report switching-field deviations larger than this as a warning (V/A).")
    parser.add_argument("--out", type=Path, default=Path("macefield-audit"))
    args = parser.parse_args()
    if not args.model.is_file():
        raise FileNotFoundError(args.model)
    args.out.mkdir(parents=True, exist_ok=True)

    zero_calc = MACECalculator(
        model_paths=str(args.model), model_type="MACEField", head=args.head,
        device=args.device, default_dtype=args.dtype,
        electric_field=[0.0, 0.0, 0.0], compute_polarization=False,
        compute_becs=False, compute_polarizability=False,
    )
    d_scan = np.linspace(-0.22, 0.22, 89)
    energy, ti_force = [], []
    for d in d_scan:
        atoms = bto_probe(float(d))
        atoms.calc = zero_calc
        energy.append(float(atoms.get_potential_energy()))
        ti_force.append(float(atoms.get_forces()[1, 2]))
    energy = np.asarray(energy)
    ti_force = np.asarray(ti_force)
    minima_idx = np.where((energy[1:-1] < energy[:-2]) & (energy[1:-1] < energy[2:]))[0] + 1
    minima = d_scan[minima_idx]
    if len(minima) != 2:
        raise RuntimeError(f"Expected two zero-field minima, found {minima.tolist()}")
    central_idx = int(np.argmin(np.abs(d_scan)))
    barrier_mev = float((energy[central_idx] - energy[minima_idx].mean()) * 1000.0)
    target_relative = BARRIER_EV * ((d_scan**2 / D0**2) - 1.0) ** 2
    predicted_relative = energy - energy.min()
    energy_curve_rmse_mev = float(np.sqrt(np.mean((predicted_relative - target_relative) ** 2)) * 1000.0)
    target_force = -4.0 * BARRIER_EV * d_scan * (d_scan**2 - D0**2) / D0**4
    force_curve_rmse_mev = float(np.sqrt(np.mean((ti_force - target_force) ** 2)) * 1000.0)
    if max(abs(float(minima[0]) + D0), abs(float(minima[1]) - D0)) > 0.035:
        raise RuntimeError(f"Double-well minima are displaced from the teaching targets: {minima.tolist()}")
    if abs(barrier_mev - BARRIER_EV * 1000.0) > 8.0 or energy_curve_rmse_mev > 5.0:
        raise RuntimeError(
            f"Double-well energy fit is poor: barrier={barrier_mev:.2f} meV, "
            f"relative-curve RMSE={energy_curve_rmse_mev:.2f} meV/cell"
        )
    if force_curve_rmse_mev > args.max_force_rmse_mev:
        raise RuntimeError(
            f"Soft-mode force RMSE {force_curve_rmse_mev:.2f} meV/A exceeds "
            f"the audit limit {args.max_force_rmse_mev:.2f} meV/A"
        )

    fields_up = np.linspace(-0.16, 0.16, 65)
    field_cycle = np.concatenate([fields_up, fields_up[-2::-1]])
    relaxed_d = -D0
    root_calc = MACECalculator(
        model_paths=str(args.model), model_type="MACEField", head=args.head,
        device=args.device, default_dtype=args.dtype,
        electric_field=[0.0, 0.0, float(field_cycle[0])],
        compute_forces=True, compute_polarization=False,
        compute_becs=False, compute_polarizability=False,
    )
    loop_calc = MACECalculator(
        model_paths=str(args.model), model_type="MACEField", head=args.head,
        device=args.device, default_dtype=args.dtype,
        electric_field=[0.0, 0.0, float(field_cycle[0])],
        compute_forces=True, compute_polarization=True,
        compute_becs=False, compute_polarizability=False,
    )
    branch_d, branch_p = [], []
    for index, ez in enumerate(field_cycle):
        root_calc.electric_field = [0.0, 0.0, float(ez)]
        root_calc.reset()
        relaxed_d = nearest_stable_mode_root(root_calc, relaxed_d)

        loop_calc.electric_field = [0.0, 0.0, float(ez)]
        loop_calc.reset()
        relaxed = bto_probe(relaxed_d)
        relaxed.calc = loop_calc
        relaxed.get_forces()
        branch_d.append(float(relaxed_d))
        branch_p.append(float(loop_calc.results["polarization"][2]))
    branch_d = np.asarray(branch_d)
    branch_p = np.asarray(branch_p)
    n_up = len(fields_up)
    zero_up = int(np.argmin(np.abs(fields_up)))
    zero_down = n_up + (len(fields_up) - 2 - zero_up)
    remanent_gap = float(abs(branch_p[zero_down] - branch_p[zero_up]))
    up_jump = int(np.argmax(np.abs(np.diff(branch_d[:n_up]))) + 1)
    down_jump = int(np.argmax(np.abs(np.diff(branch_d[n_up - 1:]))) + n_up)
    def spinodal(initial_displacement: float, initial_field: float) -> np.ndarray:
        solution = root(
            lambda values: bto_field_stationary_derivatives(
                float(values[0]), (0.0, 0.0, 0.0), float(values[1]), BTO_REFERENCE_VOLUME
            ),
            x0=[initial_displacement, initial_field],
        )
        if not solution.success:
            raise RuntimeError(f"Could not solve the analytic spinodal: {solution.message}")
        return np.asarray(solution.x, dtype=float)

    up_spinodal = spinodal(-D0 / np.sqrt(3.0), 0.05)
    down_spinodal = spinodal(D0 / np.sqrt(3.0), -0.05)
    critical_field_up = float(up_spinodal[1])
    critical_field_down = float(down_spinodal[1])
    up_spinodal_error = abs(float(field_cycle[up_jump]) - critical_field_up)
    down_spinodal_error = abs(float(field_cycle[down_jump]) - critical_field_down)
    spinodals_within_tolerance = max(up_spinodal_error, down_spinodal_error) <= args.spinodal_tolerance
    max_d_jump = float(max(
        np.max(np.abs(np.diff(branch_d[:n_up]))),
        np.max(np.abs(np.diff(branch_d[n_up - 1:]))),
    ))
    if barrier_mev <= 0.0:
        raise RuntimeError(f"Predicted central barrier is not positive: {barrier_mev:.3f} meV")
    if remanent_gap < 1e-4 or max_d_jump < 0.025 or field_cycle[up_jump] <= 0 or field_cycle[down_jump] >= 0:
        raise RuntimeError(
            "The model does not show a resolvable path-dependent loop with "
            "switches on the expected field branches: "
            f"remanent polarization gap={remanent_gap:.4g} e/A^2, "
            f"largest displacement jump={max_d_jump:.4g} A, "
            f"increasing-branch jump at {field_cycle[up_jump]:+.4f} V/A "
            f"(d={branch_d[up_jump - 1]:+.4f}->{branch_d[up_jump]:+.4f} A), "
            f"decreasing-branch jump at {field_cycle[down_jump]:+.4f} V/A "
            f"(d={branch_d[down_jump - 1]:+.4f}->{branch_d[down_jump]:+.4f} A)"
        )
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].plot(d_scan, (energy - energy.min()) * 1000.0, color="#276b91", lw=2)
    axes[0].scatter(minima, (energy[minima_idx] - energy.min()) * 1000.0,
                    color="#e0a126", edgecolor="black", zorder=4, label="Local minima")
    axes[0].set(xlabel="Ti displacement d (A)", ylabel="Relative energy (meV/cell)",
                title=f"Zero-field double well · barrier {barrier_mev:.1f} meV")
    axes[0].legend(frameon=False)
    axes[1].plot(field_cycle[:n_up], branch_p[:n_up] * POLARIZATION_CONVERSION,
                 color="#b5483a", lw=2.4, label="Increasing field")
    axes[1].plot(field_cycle[n_up - 1:], branch_p[n_up - 1:] * POLARIZATION_CONVERSION,
                 color="#276b91", lw=2.4, label="Decreasing field")
    axes[1].scatter(field_cycle[[up_jump, down_jump]],
                    branch_p[[up_jump, down_jump]] * POLARIZATION_CONVERSION,
                    marker="*", s=90, color="#e0a126", edgecolor="black", zorder=4)
    axes[1].set(xlabel="Applied field Ez (V/A)", ylabel="Polarization Pz (microC/cm2)",
                title="MACEField metastable switching loop")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=0.22)
    figure.tight_layout()
    figure.savefig(args.out / "macefield-surface-and-loop.png", dpi=180)
    plt.close(figure)

    if spinodals_within_tolerance:
        status = "PASS: two zero-field minima, positive barrier, loop and spinodal tracking"
    else:
        status = (
            "WARNING: double-well and path-dependent loop criteria pass, but model switching "
            "fields are shifted from the analytic spinodals"
        )
    result = {
        "model": str(args.model.resolve()), "head": args.head, "device": args.device,
        "double_well": {
            "minima_displacement_A": [float(x) for x in minima],
            "central_barrier_meV_per_cell": barrier_mev,
            "relative_energy_curve_rmse_meV_per_cell": energy_curve_rmse_mev,
            "force_rmse_meV_per_A_on_scan_vs_analytic_target": force_curve_rmse_mev,
        },
        "switching_loop": {
            "field_range_V_per_A": [float(fields_up[0]), float(fields_up[-1])],
            "analytic_spinodal_V_per_A": [critical_field_up, critical_field_down],
            "increasing_field_jump_V_per_A": float(field_cycle[up_jump]),
            "decreasing_field_jump_V_per_A": float(field_cycle[down_jump]),
            "spinodal_deviation_V_per_A": [up_spinodal_error, down_spinodal_error],
            "spinodal_tracking_within_tolerance": spinodals_within_tolerance,
            "max_soft_mode_jump_A": max_d_jump,
            "remanent_polarization_gap_e_per_A2": remanent_gap,
            "up_branch_d_A": [float(x) for x in branch_d[:n_up]],
            "down_branch_d_A": [float(x) for x in branch_d[n_up - 1:]],
            "fields_V_per_A": [float(x) for x in fields_up],
        },
        "reference_fixture": {
            "target_minima_A": [-D0, D0],
            "target_barrier_meV_per_cell": BARRIER_EV * 1000,
            "data_source": "analytic one-mode Landau model; not DFT or experiment",
        },
        "acceptance_thresholds": {
            "max_soft_mode_force_rmse_meV_per_A": args.max_force_rmse_mev,
            "spinodal_warning_tolerance_V_per_A": args.spinodal_tolerance,
        },
        "status": status,
    }
    (args.out / "macefield-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "status": result["status"],
        "minima_A": result["double_well"]["minima_displacement_A"],
        "barrier_meV_per_cell": barrier_mev,
        "switching_fields_V_per_A": [field_cycle[up_jump], field_cycle[down_jump]],
        "analytic_spinodal_V_per_A": [critical_field_up, critical_field_down],
        "spinodal_deviation_V_per_A": [up_spinodal_error, down_spinodal_error],
        "max_displacement_jump_A": max_d_jump,
        "remanent_P_gap_e_per_A2": remanent_gap,
        "output": str(args.out.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
