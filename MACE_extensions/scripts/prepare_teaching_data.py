#!/usr/bin/env python3
"""Generate small, deterministic teaching datasets for the extension labs.

The energy, force, polarization and response surfaces are analytic teaching
models, not DFT or experimental data. The BaTiO3-like toy anchors its active
soft-mode charge to published cubic and tetragonal values, then adds explicit
mode- and strain-dependent terms so response derivatives can be followed.
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
EPS0_E_PER_V_ANGSTROM = 8.8541878128e-12 * 1.0e-10 / 1.602176634e-19

# Representative zero-temperature tetragonal P4mm BaTiO3 Born effective
# charge tensors from Table VI of Masuki et al., Phys. Rev. B 106, 224104
# (2022), DOI: 10.1103/PhysRevB.106.224104.  The oxygen order below follows
# the five-atom teaching cell: O3 is axial, O2 bridges along y, O1 along x.
# These are the fixed base tensors in the analytic toy. The active Ti/Ba zz
# entries receive an explicitly differentiated mode/strain correction below.
BTO_TETRAGONAL_BECS = np.array(
    [
        np.diag([2.726, 2.726, 2.804]),       # Ba
        np.diag([7.021, 7.021, 5.823]),       # Ti
        np.diag([-2.043, -2.043, -4.661]),    # O3, axial
        np.diag([-2.098, -5.606, -1.983]),    # O2, y bridge
        np.diag([-5.606, -2.098, -1.983]),    # O1, x bridge
    ],
    dtype=float,
)
BTO_MODE_CHARGE_Z = float(BTO_TETRAGONAL_BECS[1, 2, 2])
BTO_CUBIC_MODE_CHARGE_Z = 7.068  # Ti Z*zz, cubic reference; Masuki et al., Table IV
if not np.allclose(BTO_TETRAGONAL_BECS.sum(axis=0), 0.0, atol=1e-12):
    raise ValueError("The reference BaTiO3 BEC tensors must satisfy the acoustic sum rule")

# DFT clamped-ion optical dielectric tensor for tetragonal BaTiO3, reported by
# Hermet, Veithen and Ghosez (J. Phys.: Condens. Matter 21, 215901 (2009)).
# MACEField's reported polarizability is chi_e = dP/dE / eps0, so the energy
# coupling below uses eps0 * (epsilon_infinity - I) as the SI-scaled response.
BTO_EPSILON_INFINITY = np.diag([5.19, 5.19, 5.05])
BTO_ELECTRONIC_SUSCEPTIBILITY = BTO_EPSILON_INFINITY - np.eye(3)

# The coefficients below define a deliberately transparent nonlinear response
# surface. The published cubic/tetragonal Ti charges anchor the displacement
# dependence; strain, piezoelectric, dielectric-nonlinearity, elastic and
# electrostrictive coefficients are pedagogical parameters, not fitted BaTiO3
# measurements. Strain is the diagonal infinitesimal strain (eta_xx,eta_yy,
# eta_zz), and eta_perp means eta_xx + eta_yy.
BTO_MODE_D0 = 0.12  # Angstrom
BTO_REFERENCE_VOLUME = 3.90 * 3.90 * 4.10
BTO_LANDAU_BARRIER = 0.025  # eV per five-atom cell
BTO_MODE_CHARGE_STRAIN_Z = 2.0  # e per unit eta_zz
BTO_MODE_CHARGE_STRAIN_PERP = -0.5  # e per unit (eta_xx + eta_yy)
BTO_MODE_CHARGE_STRAIN_MODE_Z = 0.6  # e per unit eta_zz multiplying (d / d0)^2
BTO_MODE_CHARGE_STRAIN_MODE_PERP = -0.2  # e per unit eta_perp multiplying (d / d0)^2
BTO_CHI_MODE_COEFF = 0.18
BTO_CHI_STRAIN_Z = 2.0
BTO_CHI_STRAIN_PERP = -0.75
BTO_CHI_MODE_STRAIN_COEFF = 0.8
BTO_ELASTIC_C_PERP = 0.55  # eV / Angstrom^3
BTO_ELASTIC_C_Z = 0.65  # eV / Angstrom^3
BTO_ELECTROSTRICTIVE_COEFF = 5.0  # eV / Angstrom^2, multiplying eta_zz * d^2


def bto_mode_charge(displacement: float, strain: np.ndarray | tuple[float, ...] = (0, 0, 0)) -> float:
    """Analytic soft-mode Born charge, before finite-field dielectric terms."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    q2 = (float(displacement) / BTO_MODE_D0) ** 2
    eta_perp = eta_x + eta_y
    return float(
        BTO_CUBIC_MODE_CHARGE_Z
        + (BTO_MODE_CHARGE_Z - BTO_CUBIC_MODE_CHARGE_Z) * q2
        + BTO_MODE_CHARGE_STRAIN_Z * eta_z
        + BTO_MODE_CHARGE_STRAIN_PERP * eta_perp
        + (BTO_MODE_CHARGE_STRAIN_MODE_Z * eta_z
           + BTO_MODE_CHARGE_STRAIN_MODE_PERP * eta_perp) * q2
    )


def bto_mode_dipole(
    displacement: float,
    strain: np.ndarray | tuple[float, ...] = (0, 0, 0),
) -> float:
    """Cell dipole along z (e Angstrom) from the active mode and strain."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    return float(
        BTO_CUBIC_MODE_CHARGE_Z * d
        + (BTO_MODE_CHARGE_Z - BTO_CUBIC_MODE_CHARGE_Z) * d**3 / (3.0 * BTO_MODE_D0**2)
        + (BTO_MODE_CHARGE_STRAIN_Z * eta_z
           + BTO_MODE_CHARGE_STRAIN_PERP * (eta_x + eta_y)) * d
        + (BTO_MODE_CHARGE_STRAIN_MODE_Z * eta_z
           + BTO_MODE_CHARGE_STRAIN_MODE_PERP * (eta_x + eta_y))
        * d**3 / (3.0 * BTO_MODE_D0**2)
    )


def bto_electronic_susceptibility(
    displacement: float,
    strain: np.ndarray | tuple[float, ...] = (0, 0, 0),
) -> np.ndarray:
    """Clamped-ion dimensionless susceptibility chi_e(d, eta)."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    q2 = (float(displacement) / BTO_MODE_D0) ** 2
    mode_softening = 1.0 - q2
    chi = BTO_ELECTRONIC_SUSCEPTIBILITY.copy()
    chi[2, 2] += (
        BTO_CHI_MODE_COEFF * mode_softening
        + BTO_CHI_STRAIN_Z * eta_z
        + BTO_CHI_STRAIN_PERP * (eta_x + eta_y)
        + BTO_CHI_MODE_STRAIN_COEFF * eta_z * mode_softening
    )
    return chi


def bto_electronic_susceptibility_mode_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...] = (0, 0, 0),
) -> float:
    """Derivative d chi_e,zz / d d for the active soft mode."""
    _, _, eta_z = np.asarray(strain, dtype=float)
    return float(
        -2.0 * float(displacement) / BTO_MODE_D0**2
        * (BTO_CHI_MODE_COEFF + BTO_CHI_MODE_STRAIN_COEFF * eta_z)
    )


def bto_electronic_susceptibility_strain_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    axis: int,
) -> float:
    """Derivative d chi_e,zz / d eta_axis at fixed soft-mode displacement."""
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    if axis == 2:
        q2 = (float(displacement) / BTO_MODE_D0) ** 2
        return float(BTO_CHI_STRAIN_Z + BTO_CHI_MODE_STRAIN_COEFF * (1.0 - q2))
    return float(BTO_CHI_STRAIN_PERP)


def bto_mode_charge_strain_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    axis: int,
) -> float:
    """Mixed derivative d² D_z / (d d d eta_axis)."""
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    q2 = (float(displacement) / BTO_MODE_D0) ** 2
    if axis == 2:
        return float(BTO_MODE_CHARGE_STRAIN_Z + BTO_MODE_CHARGE_STRAIN_MODE_Z * q2)
    return float(BTO_MODE_CHARGE_STRAIN_PERP + BTO_MODE_CHARGE_STRAIN_MODE_PERP * q2)


def bto_mode_dipole_strain_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    axis: int,
) -> float:
    """Derivative d D_z / d eta_axis at fixed soft-mode displacement."""
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    d = float(displacement)
    q2 = (d / BTO_MODE_D0) ** 2
    if axis == 2:
        return float((BTO_MODE_CHARGE_STRAIN_Z + BTO_MODE_CHARGE_STRAIN_MODE_Z * q2 / 3.0) * d)
    return float((BTO_MODE_CHARGE_STRAIN_PERP + BTO_MODE_CHARGE_STRAIN_MODE_PERP * q2 / 3.0) * d)


def bto_field_mode_charge(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field_z: float,
    volume: float,
) -> float:
    """Finite-field mode BEC including the position derivative of chi_e."""
    return float(
        bto_mode_charge(displacement, strain)
        + float(volume) * EPS0_E_PER_V_ANGSTROM * float(field_z)
        * bto_electronic_susceptibility_mode_derivative(displacement, strain)
    )


def bto_field_mode_charge_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field_z: float,
    volume: float,
) -> float:
    """d Z*_mode(E) / d d, including the field-dependent dielectric term."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    delta = (
        BTO_MODE_CHARGE_Z - BTO_CUBIC_MODE_CHARGE_Z
        + BTO_MODE_CHARGE_STRAIN_MODE_Z * eta_z
        + BTO_MODE_CHARGE_STRAIN_MODE_PERP * (eta_x + eta_y)
    )
    d_mode_charge = 2.0 * delta * d / BTO_MODE_D0**2
    d2_chi = -2.0 / BTO_MODE_D0**2 * (
        BTO_CHI_MODE_COEFF + BTO_CHI_MODE_STRAIN_COEFF * eta_z
    )
    return float(
        d_mode_charge
        + float(volume) * EPS0_E_PER_V_ANGSTROM * float(field_z) * d2_chi
    )


def bto_enthalpy(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field: np.ndarray | tuple[float, ...],
    volume: float,
) -> float:
    """Scalar analytic electric enthalpy for the one-mode teaching cell."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    electric_field = np.asarray(field, dtype=float)
    q2 = (d / BTO_MODE_D0) ** 2
    short_range = (
        BTO_LANDAU_BARRIER * (q2 - 1.0) ** 2
        + 0.5 * BTO_REFERENCE_VOLUME * (
            BTO_ELASTIC_C_PERP * (eta_x**2 + eta_y**2)
            + BTO_ELASTIC_C_Z * eta_z**2
        )
        - BTO_ELECTROSTRICTIVE_COEFF * eta_z * d**2
    )
    dipole = np.zeros(3)
    dipole[2] = bto_mode_dipole(d, strain)
    chi_e = bto_electronic_susceptibility(d, strain)
    return float(
        short_range - electric_field @ dipole
        - 0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM * (electric_field @ chi_e @ electric_field)
    )


def bto_field_stationary_derivatives(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field_z: float,
    volume: float,
) -> tuple[float, float]:
    """First and second mode derivatives of the field enthalpy H(d, Ez)."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    ez = float(field_z)
    d_landau = (
        4.0 * BTO_LANDAU_BARRIER * d * (d**2 - BTO_MODE_D0**2) / BTO_MODE_D0**4
        - 2.0 * BTO_ELECTROSTRICTIVE_COEFF * eta_z * d
    )
    d_chi = bto_electronic_susceptibility_mode_derivative(d, strain)
    dh_dd = (
        d_landau - ez * bto_mode_charge(d, strain)
        - 0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM * ez**2 * d_chi
    )
    d2h_dd2 = bto_field_mode_curvature(d, strain, ez, volume)
    return float(dh_dd), float(d2h_dd2)


def bto_stationary_displacements(
    field_z: float,
    strain: np.ndarray | tuple[float, ...],
    volume: float,
) -> list[float]:
    """Stable stationary soft-mode roots for a longitudinal field."""
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    eta_perp = eta_x + eta_y
    ez = float(field_z)
    chi_mode = BTO_CHI_MODE_COEFF + BTO_CHI_MODE_STRAIN_COEFF * eta_z
    modecharge_delta = (
        BTO_MODE_CHARGE_Z - BTO_CUBIC_MODE_CHARGE_Z
        + BTO_MODE_CHARGE_STRAIN_MODE_Z * eta_z
        + BTO_MODE_CHARGE_STRAIN_MODE_PERP * eta_perp
    )
    mode_charge_strain = (
        BTO_MODE_CHARGE_STRAIN_Z * eta_z
        + BTO_MODE_CHARGE_STRAIN_PERP * eta_perp
    )
    # H'(d) is cubic because D(d) is cubic and chi_e(d) is quadratic.
    coefficients = [
        4.0 * BTO_LANDAU_BARRIER / BTO_MODE_D0**4,
        -ez * modecharge_delta / BTO_MODE_D0**2,
        -4.0 * BTO_LANDAU_BARRIER / BTO_MODE_D0**2
        - 2.0 * BTO_ELECTROSTRICTIVE_COEFF * eta_z
        + float(volume) * EPS0_E_PER_V_ANGSTROM * ez**2 * chi_mode / BTO_MODE_D0**2,
        -ez * (BTO_CUBIC_MODE_CHARGE_Z + mode_charge_strain),
    ]
    roots = np.roots(coefficients)
    return sorted(
        float(root.real) for root in roots
        if abs(root.imag) < 1e-8
        and bto_field_stationary_derivatives(root.real, strain, ez, volume)[1] > 0.0
    )


def bto_mode_curvature(displacement: float, strain: np.ndarray | tuple[float, ...] = (0, 0, 0)) -> float:
    """Second derivative of the zero-field analytic energy with respect to d."""
    _, _, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    return float(
        4.0 * BTO_LANDAU_BARRIER * (3.0 * d * d - BTO_MODE_D0**2) / BTO_MODE_D0**4
        - 2.0 * BTO_ELECTROSTRICTIVE_COEFF * eta_z
    )


def bto_field_mode_curvature(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field_z: float,
    volume: float,
) -> float:
    """Second derivative d²H/dd² at finite field and fixed strain."""
    d = float(displacement)
    ez = float(field_z)
    chi_second = -2.0 / BTO_MODE_D0**2 * (
        BTO_CHI_MODE_COEFF
        + BTO_CHI_MODE_STRAIN_COEFF * float(np.asarray(strain, dtype=float)[2])
    )
    return float(
        bto_mode_curvature(d, strain)
        - ez * bto_field_mode_charge_derivative(d, strain, 0.0, volume)
        - 0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM * ez**2 * chi_second
    )


def bto_relaxed_susceptibility(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    volume: float,
    field_z: float = 0.0,
) -> float:
    """Longitudinal chi including relaxation of the single soft mode.

    This is a differential susceptibility about a stable stationary state.
    It diverges as the field-dependent mode curvature approaches zero.
    """
    d = float(displacement)
    chi_mode_derivative = bto_electronic_susceptibility_mode_derivative(d, strain)
    mode_charge = bto_mode_charge(d, strain)
    chi_zz = float(bto_electronic_susceptibility(d, strain)[2, 2])
    curvature = bto_field_mode_curvature(d, strain, field_z, volume)
    effective_mode_coupling = mode_charge + float(volume) * EPS0_E_PER_V_ANGSTROM * field_z * chi_mode_derivative
    if curvature <= 0.0:
        return float("nan")
    return float(
        chi_zz
        + effective_mode_coupling**2
        / (float(volume) * EPS0_E_PER_V_ANGSTROM * curvature)
    )


def bto_clamped_piezoelectric(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    volume: float,
    axis: int = 2,
    field_z: float = 0.0,
) -> float:
    """dPz/deta_axis at fixed mode, including the explicit field response."""
    eta = np.asarray(strain, dtype=float)
    d = float(displacement)
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    field = float(field_z)
    ionic_pz = bto_mode_dipole(d, strain) / float(volume)
    return float(
        bto_mode_dipole_strain_derivative(d, strain, axis) / float(volume)
        + EPS0_E_PER_V_ANGSTROM * field
        * bto_electronic_susceptibility_strain_derivative(d, strain, axis)
        - ionic_pz / (1.0 + eta[axis])
    )


def bto_field_mode_strain_derivative(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field_z: float,
    volume: float,
    axis: int,
) -> float:
    """Mixed derivative d²H/(dd deta_axis), including dielectric and volume terms."""
    eta = np.asarray(strain, dtype=float)
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    d = float(displacement)
    ez = float(field_z)
    chi_d = bto_electronic_susceptibility_mode_derivative(d, eta)
    chi_d_eta = (
        -2.0 * d / BTO_MODE_D0**2 * BTO_CHI_MODE_STRAIN_COEFF
        if axis == 2 else 0.0
    )
    elastic_mode_mixed = -2.0 * BTO_ELECTROSTRICTIVE_COEFF * d if axis == 2 else 0.0
    return float(
        elastic_mode_mixed
        - ez * bto_mode_charge_strain_derivative(d, eta, axis)
        - 0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM * ez**2
        * (chi_d / (1.0 + eta[axis]) + chi_d_eta)
    )


def bto_relaxed_piezoelectric(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    volume: float,
    axis: int = 2,
    field_z: float = 0.0,
) -> float:
    """dPz/deta_axis including equilibrium relaxation of the soft mode."""
    d = float(displacement)
    ez = float(field_z)
    curvature = bto_field_mode_curvature(d, strain, ez, volume)
    if curvature <= 0.0:
        return float("nan")
    dd_deta = -bto_field_mode_strain_derivative(d, strain, ez, volume, axis) / curvature
    mode_charge = bto_field_mode_charge(d, strain, ez, volume)
    e_clamped = bto_clamped_piezoelectric(
        d, strain, volume, axis=axis, field_z=ez
    )
    return float(e_clamped + mode_charge * dd_deta / float(volume))


def evaluate_bto_toy_state(
    displacement: float,
    strain: np.ndarray | tuple[float, ...],
    field: np.ndarray | tuple[float, ...],
    atomic_displacements: np.ndarray,
    volume: float,
) -> dict[str, np.ndarray | float]:
    """Evaluate one field/strain state and exact derivatives of its toy energy.

    The response model is generated from one scalar enthalpy. In particular,
    the field-dependent BEC includes the coordinate derivative of chi_e, while
    forces use the derivative of the -1/2 E chi E energy term (which carries
    a factor of one half).
    """
    eta_x, eta_y, eta_z = np.asarray(strain, dtype=float)
    d = float(displacement)
    electric_field = np.asarray(field, dtype=float)
    q = d / BTO_MODE_D0
    q2 = q * q
    eta_perp = eta_x + eta_y
    chi_e = bto_electronic_susceptibility(d, strain)

    dipole = np.einsum("iab,ib->a", BTO_TETRAGONAL_BECS, atomic_displacements)
    mode_dipole = bto_mode_dipole(d, strain)
    # Replace the fixed tetragonal linear soft-mode term with its integrated
    # cubic-to-tetragonal polynomial, then add the strain polarization.
    dipole[2] += mode_dipole - BTO_MODE_CHARGE_Z * d

    landau_energy = BTO_LANDAU_BARRIER * (q2 - 1.0) ** 2
    elastic_energy = 0.5 * BTO_REFERENCE_VOLUME * (
        BTO_ELASTIC_C_PERP * (eta_x**2 + eta_y**2) + BTO_ELASTIC_C_Z * eta_z**2
    )
    electrostrictive_energy = -BTO_ELECTROSTRICTIVE_COEFF * eta_z * d**2
    energy = (
        landau_energy + elastic_energy + electrostrictive_energy
        - float(electric_field @ dipole)
        - 0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM * float(electric_field @ chi_e @ electric_field)
    )
    polarization = dipole / float(volume) + EPS0_E_PER_V_ANGSTROM * (chi_e @ electric_field)

    mode_charge = bto_mode_charge(d, strain)
    finite_field_charge_shift = (
        bto_field_mode_charge(d, strain, electric_field[2], volume) - mode_charge
    )
    becs = BTO_TETRAGONAL_BECS.copy()
    bec_delta = mode_charge - BTO_MODE_CHARGE_Z + finite_field_charge_shift
    becs[1, 2, 2] += bec_delta
    becs[0, 2, 2] -= bec_delta

    forces = np.einsum("iab,a->ib", BTO_TETRAGONAL_BECS, electric_field)
    landau_derivative = (
        4.0 * BTO_LANDAU_BARRIER * d * (d**2 - BTO_MODE_D0**2) / BTO_MODE_D0**4
        - 2.0 * BTO_ELECTROSTRICTIVE_COEFF * eta_z * d
    )
    dielectric_mode_derivative = (
        0.5 * float(volume) * EPS0_E_PER_V_ANGSTROM
        * electric_field[2] ** 2
        * bto_electronic_susceptibility_mode_derivative(d, strain)
    )
    mode_force_correction = (
        -landau_derivative
        + (mode_charge - BTO_MODE_CHARGE_Z) * electric_field[2]
        + dielectric_mode_derivative
    )
    forces[1, 2] += mode_force_correction
    forces[0, 2] -= mode_force_correction

    return {
        "energy": float(energy),
        "forces": forces,
        "polarization": polarization,
        "becs": becs,
        "polarizability": chi_e,
        "mode_charge": float(mode_charge),
        "mode_curvature": bto_mode_curvature(d, strain),
        "mode_dipole": float(mode_dipole),
        "clamped_piezo_z": bto_clamped_piezoelectric(
            d, strain, volume, axis=2, field_z=electric_field[2]
        ),
        "relaxed_piezo_z": bto_relaxed_piezoelectric(
            d, strain, volume, axis=2, field_z=electric_field[2]
        ),
        "relaxed_susceptibility_zz": bto_relaxed_susceptibility(d, strain, volume),
    }


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
                atoms.info["label_source"] = "analytic neutral fixed charges; e Angstrom"
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
    """Nonlinear mode/strain ferroelectric toy with exact E/F/P/response labels.

    It is not a DFT reference for BaTiO3. Its active mode charge interpolates
    between published cubic and tetragonal values; strain and dielectric
    nonlinearities are explicitly pedagogical.
    """
    train, valid = [], []
    a, c = 3.90, 4.10
    # Axial and biaxial strains expose both eta_zz and eta_xx + eta_yy terms.
    # Zero strain appears only once; all strains remain in a small-strain range.
    strain_states = [
        np.array([0.0, 0.0, -0.02]),
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.02]),
        np.array([-0.01, -0.01, 0.0]),
        np.array([0.01, 0.01, 0.0]),
    ]
    d_train = np.linspace(-0.22, 0.22, 11)
    # Interleave validation displacements with the training grid without
    # repeating d=0 (or any full structure/field/strain combination).
    d_valid = np.linspace(-0.21, 0.21, 8)
    if np.intersect1d(np.round(d_train, 10), np.round(d_valid, 10)).size:
        raise ValueError("MACEField train/validation displacement grids must be disjoint")
    # Cover the field-driven switching region (the nonlinear analytic spinodal
    # is about +/-0.048 V/A), retain outer-field probes, and add transverse fields so
    # the full anisotropic dielectric tensor is identified by the labels.
    longitudinal_fields = (-0.16, -0.06, 0.0, 0.06, 0.16)
    field_grid = [np.array([0.0, 0.0, ez]) for ez in longitudinal_fields]
    # A small set of transverse probes identifies the diagonal response while
    # keeping the one-mode energy/force training compact.
    for axis in (0, 1):
        for value in (-0.12, 0.12):
            transverse = np.zeros(3)
            transverse[axis] = value
            field_grid.append(transverse)

    reference_positions = np.array([
        [0.0, 0.0, 0.0],
        [a / 2, a / 2, c / 2],
        [a / 2, a / 2, 0.0],
        [a / 2, 0.0, c / 2],
        [0.0, a / 2, c / 2],
    ])
    for split, target, mode_displacements in (
        ("train", train, d_train),
        ("valid", valid, d_valid),
    ):
        fields = field_grid if split == "train" else [
            np.array([0.0, 0.0, ez]) for ez in longitudinal_fields
        ] + [
            np.array([value if axis == 0 else 0.0, value if axis == 1 else 0.0, 0.0])
            for axis in (0, 1)
            for value in (-0.10, 0.10)
        ]
        for istrain, strain in enumerate(strain_states):
            deformation = np.diag(1.0 + strain)
            reference_strained = reference_positions @ deformation
            cell = np.diag(np.array([a, a, c]) * (1.0 + strain))
            volume = float(np.linalg.det(cell))
            for idisplacement, d in enumerate(mode_displacements):
                for ifield, field in enumerate(fields):
                    symbols = ["Ba", "Ti", "O", "O", "O"]
                    positions = reference_strained.copy()
                    positions[1, 2] += float(d)
                    atoms = Atoms(symbols, positions=positions, cell=cell, pbc=True)
                    atomic_displacements = positions - reference_strained
                    labels = evaluate_bto_toy_state(
                        displacement=float(d), strain=strain, field=field,
                        atomic_displacements=atomic_displacements, volume=volume,
                    )
                    atoms.info["REF_energy"] = labels["energy"]
                    atoms.info["REF_electric_field"] = field
                    atoms.info["REF_polarization"] = labels["polarization"]
                    atoms.info["REF_polarizability"] = labels["polarizability"].reshape(-1)
                    atoms.info["REF_strain"] = strain
                    atoms.info["REF_mode_displacement"] = float(d)
                    atoms.info["REF_mode_charge"] = labels["mode_charge"]
                    atoms.info["label_source"] = (
                        "analytic nonlinear soft-mode/strain Landau toy; response coefficients are pedagogical; "
                        "energy surface is not DFT"
                    )
                    atoms.info["bec_reference"] = (
                        "Cubic Ti Z*zz 7.068 e and tetragonal Ti Z*zz 5.823 e anchored to "
                        "Masuki et al., Phys. Rev. B 106, 224104 (2022), Tables IV and VI; "
                        "DOI: 10.1103/PhysRevB.106.224104"
                    )
                    atoms.info["electronic_susceptibility_reference"] = (
                        "Tetragonal BaTiO3 epsilon_infinity from Hermet et al., "
                        "J. Phys.: Condens. Matter 21, 215901 (2009); displacement/strain corrections are pedagogical; "
                        "DOI: 10.1088/0953-8984/21/21/215901"
                    )
                    atoms.info["config_type"] = (
                        f"ferroelectric_{split}_strain_{istrain}_d_{idisplacement}_e_{ifield}"
                    )
                    atoms.new_array("REF_forces", labels["forces"])
                    atoms.new_array("REF_becs", labels["becs"].reshape(5, 9))
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
