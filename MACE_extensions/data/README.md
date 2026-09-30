# Extension tutorial training data

Regenerate all deterministic teaching datasets from the repository root with:

```bash
python MACE_extensions/scripts/prepare_teaching_data.py
```

These **analytic teaching datasets** make the model, parser and training paths runnable without external quantum-chemistry calculations. They are not DFT, experimental or production data.

| Files | Structure and target | Analytic labels |
|---|---|---|
| `atomicdipoles_water_*.extxyz` | Neutral gas-phase water; `REF_dipoles` in e Å | Fixed charges `q(O)=-0.8e`, `q(H)=+0.4e` |
| `magnetic_fe2_*.extxyz` | Fe dimer; `REF_magmom`, `REF_magforces`, energy and forces | Exponential pair repulsion plus exchange `J(r) m1·m2`; analytic derivatives |
| `macefield_batio3_toy_*.extxyz` | Periodic five-atom BaTiO₃-like cell; field, energy, forces, polarization, Born charges, strain and dielectric susceptibility | One-coordinate Landau surface with polynomial mode, mode–strain and dielectric response; cubic/tetragonal Ti charge and unstrained clamped-ion dielectric anchors from literature.¹˒² |
| `maceles_water_dimer_*.extxyz` | Two rigid water molecules; energy and forces | Fixed-charge Coulomb energy plus a short-range O–O repulsion |

The MACEField toy keeps zero-strain minima at Ti displacements of ±0.12 Å and a 25 meV per-cell barrier. It has 495 training and 360 validation structures spanning 11 training and 8 interleaved validation soft-mode values, longitudinal and transverse fields, three axial strains (−2%, 0, +2%) and two biaxial strains (−1%, +1% on both in-plane axes). Validation displacements do not repeat any complete training structure. The longitudinal fields include the nonlinear analytic spinodals near ±0.0482 V/Å. This is an interpolation check over the same analytic model and strain/field families, not an independent physical test set.

At zero strain, the active Ti Z*zz varies quadratically with displacement between the cubic value 7.068e at d = 0 and the tetragonal value 5.823e at d = ±0.12 Å. Strain adds linear and mode–strain terms. A compensating, equal-and-opposite correction to Ba Z*zz preserves the acoustic sum rule; other anisotropic tensor entries retain the tetragonal reference values. The clamped-ion susceptibility uses the calculated tetragonal ε∞ = diag(5.19, 5.19, 5.05) at the FE minima and has pedagogical mode and strain corrections away from them. Its relaxed-ion counterpart is calculated from the soft-mode curvature and is shown separately. Only the cubic/tetragonal Ti charge anchors and unstrained dielectric tensor are literature reference values; the remaining response coefficients, elastic energy, and all generated energy/force labels are analytic teaching choices, not DFT or experimental data.

The energy, forces, polarization, BECs and clamped-ion susceptibility are derivatives of one shared scalar field enthalpy. The field-dependent BEC includes the derivative of the state-dependent susceptibility; the force includes the derivative of the corresponding quadratic field-energy term. The mode-relaxed susceptibility follows by differentiating the equilibrium condition, and the relaxed piezoelectric response adds the mode's strain-mediated contribution to the clamped value. This model isolates derivative consistency and symmetry constraints, not a quantitative BaTiO₃ fit.

The MACEField audit script checks both zero-field minima and follows the stable Ti-force root through a field cycle, staying inside the displacement interval sampled by training. This avoids letting an unconstrained optimizer escape into unsupported minima outside the toy data range. The response fine-tune adds polarization, Born-charge and susceptibility losses; re-run the audit after training to check that the double well and loop are preserved while held-out response errors improve. This one-coordinate model does not represent BaTiO₃ DFT, domains, thermal switching or an experimental coercive field.

¹ Masuki et al., *Phys. Rev. B* **106**, 224104 (2022), Tables IV and VI, [doi:10.1103/PhysRevB.106.224104](https://doi.org/10.1103/PhysRevB.106.224104). ² Hermet et al., *J. Phys.: Condens. Matter* **21**, 215901 (2009), calculated tetragonal dielectric tensor, [doi:10.1088/0953-8984/21/21/215901](https://doi.org/10.1088/0953-8984/21/21/215901).

The example checkpoints teach model loading and plotting; they are not evidence of chemical accuracy, transferability or uniquely interpretable latent charges. For research, use well-converged reference calculations, preserve units/provenance, and make structure-aware train/validation/test splits.
