# Figure attribution

`mace_theory_architecture.png` is the original MACE architecture schematic from ACEsuit's `mace-tutorials/T03_MACE_Theory.ipynb`:

- Source: <https://github.com/ACEsuit/mace-tutorials/blob/main/T03_MACE_Theory.ipynb>
- Source repository license: MIT, copyright (c) 2023 Ilyes Batatia.

The four `architecture_*.png` figures are separate image-generator adaptations of that source image. Each keeps the original MACE trunk as its scaffold and adds the extension's data inputs, modules, and outputs:

- AtomicDipolesMACE: layerwise vector readouts and system-dipole aggregation.
- Magnetic MACE: per-atom moment features entering magnetic interaction and product blocks, with magnetic forces from energy derivatives.
- MACEField: a field-conditioned equivariant correction on intermediate hidden features and derivative-based response outputs.
- MACELES: a latent-multipole branch and long-range energy addition after the shared representation.

These diagrams are teaching schematics. The model code and the accompanying notebook explanations define the exact implementation details.
