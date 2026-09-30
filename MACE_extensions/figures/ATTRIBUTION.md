# Figure attribution

`mace_theory_architecture.png` is the original MACE architecture schematic from ACEsuit’s `mace-tutorials/T03_MACE_Theory.ipynb`:

- Source: <https://github.com/ACEsuit/mace-tutorials/blob/main/T03_MACE_Theory.ipynb>
- Source repository license: MIT, copyright (c) 2023 Ilyes Batatia.

The four `architecture_*.png` diagrams are adaptations of that source figure. Each keeps the original MACE trunk and integrates the extension data flow:

- **MACEField:** a global electric-field input, a field-conditioned equivariant product after the MACE product stage, and response quantities derived from energy.
- **AtomicDipolesMACE:** layerwise equivariant vector readouts and molecular-dipole aggregation.
- **Magnetic MACE:** site moment features entering the interaction and product stages, with magnetic forces from energy derivatives.
- **MACELES:** latent multipole readouts feeding a long-range solver and total-energy branch.

The thin dark capture frame has been cropped from the diagrams. They are teaching schematics; the model code and notebook explanations define implementation details.
