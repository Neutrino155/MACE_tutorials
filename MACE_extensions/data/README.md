# Extension teaching data

Regenerate the deterministic datasets from the repository root:

```bash
python MACE_extensions/scripts/prepare_teaching_data.py
```

These analytic labels make each training example runnable without external quantum-chemistry calculations. They are not DFT, experimental or production data.

| Files | Structures and labels | Label model |
|---|---|---|
| `atomicdipoles_water_*.extxyz` | Neutral water; `REF_energy`, `REF_forces`, `REF_dipoles` | Harmonic O–H and H–O–H terms with fixed-charge dipoles (`q(O)=-0.8e`, `q(H)=+0.4e`) |
| `magnetic_fe2_*.extxyz` | Fe dimer; energy, forces, `REF_magmom`, `REF_magforces` | Exponential pair repulsion and exchange `J(r) m1·m2` |
| `macefield_batio3_toy_*.extxyz` | Periodic five-atom BaTiO₃-like cell; electric field, `REF_energy`, `REF_forces`, `REF_polarization` | Fixed-cell one-coordinate Landau double well with linear field–dipole coupling |
| `maceles_water_dimer_*.extxyz` | Two rigid water molecules; `REF_energy`, `REF_forces` | Fixed-charge Coulomb energy plus short-range O–O repulsion |

The MACEField data contain **345 training** and **132 validation** structures. The cell is fixed at 3.90 × 3.90 × 4.10 Å throughout. Only the Ti displacement along z varies. Training fields are z-directed and span −0.12 to +0.12 V/Å, including points near the model's switching fields. The validation set uses different displacements and field values from training. It checks interpolation within this analytic surface; it is not an independent physical test set.

The target electric enthalpy is

\[
H(d,E_z)=B\left[\left(d/d_0\right)^2-1\right]^2-E_z Z d,
\]

with `d0=0.12 Å`, `B=0.025 eV/cell`, and a constant pedagogical mode charge `Z=5.8 e`. Energy, Ti force, and polarization `Pz=Zd/Ω` are derivatives of this same expression.

The toy shows how a field can tilt a double well and produce a history-dependent switching loop when a local minimum is followed through a field cycle. It does not model BaTiO₃ quantitatively, domain walls, thermal activation or an experimental coercive field.

AtomicDipolesMACE uses dipole labels for its dipole-only loss; energy and force labels are also provided for energy-force model variants. The teaching checkpoints demonstrate loading and plotting, not chemical accuracy or transferability. For research, use well-converged reference calculations and preserve units and provenance.
