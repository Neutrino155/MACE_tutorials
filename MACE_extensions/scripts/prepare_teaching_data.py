#!/usr/bin/env python3
"""Generate deterministic teaching datasets for the extension labs.

The BaTiO3-like MACEField data describe fixed-cell electric-field switching
with a one-coordinate Landau energy. All labels are analytic teaching data,
not DFT or experimental data.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
missing = [name for name in ("numpy", "ase") if importlib.util.find_spec(name) is None]
if missing:
    raise RuntimeError(f"Install the data-generation dependencies first: pip install {' '.join(missing)}")

import numpy as np
from ase import Atoms
from ase.io import write


DATA = ROOT / "MACE_extensions" / "data"
KCOULOMB = 14.3996454784255  # eV Å / e^2
BTO_MODE_D0 = 0.12  # Angstrom
BTO_REFERENCE_CELL = np.diag([3.90, 3.90, 4.10])
BTO_REFERENCE_VOLUME = float(np.linalg.det(BTO_REFERENCE_CELL))
BTO_LANDAU_BARRIER = 0.025  # eV per five-atom cell
BTO_MODE_CHARGE_Z = 5.8  # e; pedagogical constant effective mode charge


def bto_landau_energy(displacement: float) -> float:
    """Zero-field double-well energy in eV per primitive cell."""
    q = float(displacement) / BTO_MODE_D0
    return float(BTO_LANDAU_BARRIER * (q * q - 1.0) ** 2)


def bto_mode_dipole(displacement: float) -> float:
    """Cell dipole along z in e Angstrom for the constant-charge toy mode."""
    return float(BTO_MODE_CHARGE_Z * float(displacement))


def bto_enthalpy(displacement: float, field_z: float) -> float:
    """Fixed-cell electric enthalpy H(d, Ez) in eV per primitive cell."""
    return float(bto_landau_energy(displacement) - field_z * bto_mode_dipole(displacement))


def bto_field_stationary_derivatives(
    displacement: float, field_z: float
) -> tuple[float, float]:
    """First and second derivatives of H with respect to Ti displacement."""
    d = float(displacement)
    first = (
        4.0 * BTO_LANDAU_BARRIER * d * (d * d - BTO_MODE_D0**2) / BTO_MODE_D0**4
        - float(field_z) * BTO_MODE_CHARGE_Z
    )
    second = 4.0 * BTO_LANDAU_BARRIER * (3.0 * d * d - BTO_MODE_D0**2) / BTO_MODE_D0**4
    return float(first), float(second)


def bto_stationary_displacements(field_z: float) -> list[float]:
    """Stable stationary Ti displacements for a longitudinal field."""
    coefficients = [
        4.0 * BTO_LANDAU_BARRIER / BTO_MODE_D0**4,
        0.0,
        -4.0 * BTO_LANDAU_BARRIER / BTO_MODE_D0**2,
        -float(field_z) * BTO_MODE_CHARGE_Z,
    ]
    roots = np.roots(coefficients)
    return sorted(
        float(root.real)
        for root in roots
        if abs(root.imag) < 1e-9
        and bto_field_stationary_derivatives(root.real, field_z)[1] > 0.0
    )


def evaluate_bto_toy_state(
    displacement: float,
    field: np.ndarray | tuple[float, ...],
    volume: float,
) -> dict[str, np.ndarray | float]:
    """Return energy, force and polarization labels from the same enthalpy."""
    electric_field = np.asarray(field, dtype=float)
    if not np.allclose(electric_field[:2], 0.0):
        raise ValueError("The fixed-cell switching toy uses only a z-directed field")
    energy = bto_enthalpy(float(displacement), float(electric_field[2]))
    mode_force = -bto_field_stationary_derivatives(
        float(displacement), float(electric_field[2])
    )[0]
    forces = np.zeros((5, 3), dtype=float)
    forces[1, 2] = mode_force
    polarization = np.array([0.0, 0.0, bto_mode_dipole(displacement) / float(volume)])
    return {"energy": energy, "forces": forces, "polarization": polarization}

def random_rotation(rng: np.random.Generator) -> np.ndarray:
    """Uniform random proper rotation from a unit quaternion."""
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def water(angle_deg: float, bond: float = 0.9572) -> np.ndarray:
    angle = np.deg2rad(angle_deg)
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [bond, 0.0, 0.0],
            [bond * np.cos(angle), bond * np.sin(angle), 0.0],
        ]
    )


def water_intramolecular_energy_forces(
    xyz: np.ndarray,
    *,
    bond_length: float = 0.9572,
    angle_deg: float = 104.52,
    bond_stiffness: float = 20.0,
    angle_stiffness: float = 0.5,
) -> tuple[float, np.ndarray]:
    """Simple bonded water labels in eV and eV/Angstrom.

    The training conformers use fixed-charge dipoles and a harmonic O-H/O-H
    angle potential. This lightweight reference makes the data reusable for
    energy/force-capable dipole models as well as the dipole-only model below.
    """
    xyz = np.asarray(xyz, dtype=float)
    vectors = xyz[1:] - xyz[0]
    lengths = np.linalg.norm(vectors, axis=1)
    unit = vectors / lengths[:, None]
    cosine = float(np.clip(np.dot(unit[0], unit[1]), -1.0, 1.0))
    angle = float(np.arccos(cosine))
    target_angle = np.deg2rad(angle_deg)

    bond_delta = lengths - bond_length
    angle_delta = angle - target_angle
    energy = 0.5 * bond_stiffness * float(np.dot(bond_delta, bond_delta))
    energy += 0.5 * angle_stiffness * angle_delta**2

    gradient = bond_stiffness * bond_delta[:, None] * unit
    sine = max(float(np.sin(angle)), 1.0e-12)
    d_angle_dv1 = -(unit[1] - cosine * unit[0]) / (lengths[0] * sine)
    d_angle_dv2 = -(unit[0] - cosine * unit[1]) / (lengths[1] * sine)
    gradient[0] += angle_stiffness * angle_delta * d_angle_dv1
    gradient[1] += angle_stiffness * angle_delta * d_angle_dv2

    forces = np.zeros_like(xyz)
    forces[1:] = -gradient
    forces[0] = gradient.sum(axis=0)
    return float(energy), forces


def write_frames(name: str, train: list[Atoms], valid: list[Atoms]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for split, frames in (("train", train), ("valid", valid)):
        path = DATA / f"{name}_{split}.extxyz"
        write(path, frames, format="extxyz")
        print(f"{path.relative_to(ROOT)}: {len(frames)} frames")


def dipole_frames(rng: np.random.Generator) -> tuple[list[Atoms], list[Atoms]]:
    """Neutral fixed-charge water labels in e Å; all configurations are molecules."""
    train, valid = [], []
    charges = np.array([-0.8, 0.4, 0.4])
    for split, target in (("train", train), ("valid", valid)):
        angles = np.linspace(78.0, 126.0, 17 if split == "train" else 7)
        bonds = (0.92, 0.9572, 0.99) if split == "train" else (0.94, 0.98)
        for ia, angle in enumerate(angles):
            for ib, bond in enumerate(bonds):
                xyz = water(angle, bond)
                rotation = random_rotation(rng)
                xyz = xyz @ rotation.T + rng.uniform(-1.5, 1.5, size=3)
                atoms = Atoms("OHH", positions=xyz, pbc=False)
                atoms.info["REF_dipoles"] = np.sum(charges[:, None] * xyz, axis=0)
                energy, forces = water_intramolecular_energy_forces(xyz)
                atoms.info["REF_energy"] = energy
                atoms.new_array("REF_forces", forces)
                atoms.info["label_source"] = (
                    "analytic fixed-charge dipole and harmonic water energy/forces; "
                    "e Angstrom, eV, eV/Angstrom"
                )
                atoms.info["config_type"] = f"water_angle_{ia}_bond_{ib}"
                target.append(atoms)
    return train, valid


def magnetic_frames() -> tuple[list[Atoms], list[Atoms]]:
    """Two-site exchange toy with exact position and moment derivatives."""
    train, valid = [], []
    train_rs = np.linspace(2.25, 4.20, 17)
    valid_rs = np.linspace(2.32, 4.12, 9)
    cosines = np.linspace(-1.0, 1.0, 7)
    magnitudes = ((1.5, 1.5), (2.0, 2.5), (3.0, 2.0))
    for split, target, rs in (("train", train, train_rs), ("valid", valid, valid_rs)):
        for ir, distance in enumerate(rs):
            for ic, cosine in enumerate(cosines):
                m1, m2 = magnitudes[(ir + ic) % len(magnitudes)]
                sine = np.sqrt(max(0.0, 1.0 - cosine * cosine))
                moments = np.array([[m1, 0.0, 0.0], [m2 * cosine, m2 * sine, 0.0]])
                atoms = Atoms("Fe2", positions=[[0, 0, 0], [distance, 0, 0]], pbc=False)
                v = 0.40 * np.exp(-2.5 * (distance - 2.60))
                j = 0.025 * np.exp(-1.0 * (distance - 2.60))
                dv = -2.5 * v
                dj = -1.0 * j
                dot = float(np.dot(moments[0], moments[1]))
                atoms.info["REF_energy"] = v + j * dot
                force_i = (dv + dj * dot) * np.array([1.0, 0.0, 0.0])
                forces = np.stack([force_i, -force_i])
                magforces = -j * moments[::-1]
                atoms.new_array("REF_forces", forces)
                atoms.new_array("REF_magmom", moments)
                atoms.new_array("REF_magforces", magforces)
                atoms.info["label_source"] = "analytic Fe2 pair potential; eV and mu_B"
                atoms.info["config_type"] = f"r_{ir}_spin_{ic}"
                target.append(atoms)
    return train, valid


def field_frames(rng: np.random.Generator) -> tuple[list[Atoms], list[Atoms]]:
    """Fixed-cell BaTiO3-like field-switching data with E/F/P labels."""
    train, valid = [], []
    a, c = 3.90, 4.10
    reference_positions = np.array([
        [0.0, 0.0, 0.0],
        [a / 2, a / 2, c / 2],
        [a / 2, a / 2, 0.0],
        [a / 2, 0.0, c / 2],
        [0.0, a / 2, c / 2],
    ])
    d_train = np.unique(np.concatenate((
        np.linspace(-0.22, 0.22, 19),
        np.array([-BTO_MODE_D0, -BTO_MODE_D0 / np.sqrt(3.0),
                  BTO_MODE_D0 / np.sqrt(3.0), BTO_MODE_D0]),
    )))
    d_valid = ((d_train[:-1] + d_train[1:]) / 2.0)[::2]
    fields_train = np.array([
        -0.12, -0.10, -0.08, -0.06, -0.05, -0.04, -0.02, 0.0,
         0.02, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12,
    ])
    fields_valid = np.linspace(-0.11, 0.11, 12)
    cell = np.diag([a, a, c])
    volume = float(np.linalg.det(cell))

    for split, target, displacements, fields in (
        ("train", train, d_train, fields_train),
        ("valid", valid, d_valid, fields_valid),
    ):
        for idisplacement, displacement in enumerate(displacements):
            for ifield, ez in enumerate(fields):
                positions = reference_positions.copy()
                positions[1, 2] += float(displacement)
                atoms = Atoms(
                    ["Ba", "Ti", "O", "O", "O"],
                    positions=positions,
                    cell=cell,
                    pbc=True,
                )
                field = np.array([0.0, 0.0, float(ez)])
                labels = evaluate_bto_toy_state(float(displacement), field, volume)
                atoms.info["REF_energy"] = labels["energy"]
                atoms.info["REF_electric_field"] = field
                atoms.info["REF_polarization"] = labels["polarization"]
                atoms.info["REF_mode_displacement"] = float(displacement)
                atoms.info["label_source"] = (
                    "fixed-cell analytic Landau field-switching toy; not DFT or experiment"
                )
                atoms.info["config_type"] = (
                    f"{split}_d_{idisplacement}_ez_{ifield}"
                )
                atoms.new_array("REF_forces", labels["forces"])
                target.append(atoms)
    return train, valid

def water_dimer_frames(rng: np.random.Generator) -> tuple[list[Atoms], list[Atoms]]:
    """Rigid water dimers labelled by fixed-charge Coulomb + O-O repulsion."""
    train, valid = [], []
    charges = np.array([-0.834, 0.417, 0.417] * 2)
    for split, target, n in (("train", train, 72), ("valid", valid, 18)):
        for idx in range(n):
            distance = float(rng.uniform(2.75, 7.0))
            first = water(104.52)
            second = water(104.52) @ random_rotation(rng).T
            first = first @ random_rotation(rng).T
            second += np.array([distance, 0.0, 0.0])
            xyz = np.concatenate([first, second])
            atoms = Atoms("OHHOHH", positions=xyz, pbc=False)
            energy = 0.0
            forces = np.zeros_like(xyz)
            for i in range(len(atoms)):
                for j in range(i + 1, len(atoms)):
                    delta = xyz[j] - xyz[i]
                    r = float(np.linalg.norm(delta))
                    prefactor = KCOULOMB * charges[i] * charges[j]
                    energy += prefactor / r
                    fij = -prefactor * delta / r**3
                    forces[i] += fij
                    forces[j] -= fij
            # A simple short-range oxygen-oxygen repulsion avoids unphysical
            # close contacts while leaving the long-range label Coulombic.
            io, jo = 0, 3
            delta = xyz[jo] - xyz[io]
            r = float(np.linalg.norm(delta))
            amp, rho = 3.0, 0.32
            erep = amp * np.exp(-r / rho)
            dEdr = -erep / rho
            energy += erep
            frep_i = dEdr * delta / r
            forces[io] += frep_i
            forces[jo] -= frep_i
            atoms.info["REF_energy"] = float(energy)
            atoms.info["label_source"] = "analytic fixed-charge Coulomb + O-O repulsion"
            atoms.info["config_type"] = f"water_dimer_{split}_{idx}"
            atoms.new_array("REF_forces", forces)
            target.append(atoms)
    return train, valid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    write_frames("atomicdipoles_water", *dipole_frames(rng))
    write_frames("magnetic_fe2", *magnetic_frames())
    write_frames("macefield_batio3_toy", *field_frames(rng))
    write_frames("maceles_water_dimer", *water_dimer_frames(rng))


if __name__ == "__main__":
    main()
