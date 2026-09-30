# MACE extensions

This folder contains a theory overview and runnable examples showing several ways to adapt a MACE model for different physical inputs, outputs and interactions. It is written for first-year PhD students in computational chemistry and supports the Lennard-Jones Centre and Thomas Young Centre Summer School on Atomic-Scale Modelling.

The **main workshop** is the hands-on route in [`../MACE_in_practice_I/`](../MACE_in_practice_I/) and [`../MACE_in_practice_II/`](../MACE_in_practice_II/), taught together by Bradley Martin, Joe Hart and Isaac Parker. Students who are ready for more can choose a notebook from [`../MACE_advanced/`](../MACE_advanced/). Bradley leads the extension examples individually as a **30–45 minute demonstration near the end** of the Thursday 1 October 2026 session (14:00–17:00), with a ten-minute break each hour. MACEField is the lead example, followed by selected short comparisons with the other adaptations.

## Start with the notebooks in this repository

No external tutorial collection is required. If you want to review the foundations first, use:

1. [MACE Practice I](../MACE_in_practice_I/T01-MACE-Practice-I.ipynb) for dataset inspection, fitting and evaluation.
2. [MACE Practice II](../MACE_in_practice_II/T02-MACE-Practice-II.ipynb) for iterative training, active learning and fine-tuning.
3. [MACE Theory](../MACE_advanced/T03-MACE-Theory.ipynb) as an optional deeper look at the architecture and implementation.

Then use the extension notebooks as a guided comparison. You do not need to run every training job during the live demonstration.

## Notebook route

1. **[T00 · Extending MACE](T00-Extending-MACE.ipynb)** — compare four adaptation patterns and trace changes through a MACE architecture.
2. **[T01 · MACEField](T01-MACEField.ipynb)** — condition energy and response on an external electric field; inspect a double-well surface and a quasi-static model switching loop.
3. **[T02 · AtomicDipolesMACE](T02-AtomicDipolesMACE.ipynb)** — add an equivariant vector-property readout and check rotation covariance.
4. **[T03 · Magnetic MACE](T03-MagneticMACE.ipynb)** — include local magnetic moments in energy and force predictions.
5. **[T04 · MACELES](T04-MACELES.ipynb)** — combine a learned short-range model with an explicit long-range electrostatic energy branch.

T00 is a compact map for discussion. T01 is the first detailed example and the central live demonstration; the remaining examples can be introduced briefly or explored later according to the group’s interests.

## Repository map

- `T00`–`T04` are notebooks. The theory overview contains the architecture comparison; each model notebook explains the adaptation, implementation path, training data and diagnostics.
- `figures/` contains the original MACE architecture image and four adapted architecture diagrams. Each PNG integrates the extension input, operation or output into the original MACE data flow. Notebooks load these images by relative path.
- `data/` contains deterministic analytic training and validation examples in ExtXYZ format. See [`data/README.md`](data/README.md) for labels, units and limitations.
- `models/pretrained_models.zip` contains small demonstration checkpoints for the AtomicDipolesMACE, Magnetic MACE and MACELES examples. T01 trains its MACEField model from the included toy data.
- `scripts/` contains Colab/local setup, the structure viewer, deterministic data generation, model-specific training commands and the MACEField surface audit.
- `config/` contains a compact MACELES model configuration example.

The structure views used in T01–T04 are a notebook-focused adaptation of the interactive visualizer in [Bradley Martin's MP Ferroelectrics explorer](https://github.com/Neutrino155/Neutrino155.github.io/tree/main/public/mp-ferroelectrics/explorer). They carry over its 3D and lattice-face views, atom inspection, frame playback, bonds, coordination polyhedra and property overlays. The renderer is bundled in `scripts/structure_viewer.js` and emitted directly as JavaScript in notebook output, so local JupyterLab and Colab need no website assets or network access. Dataset selection and frame playback do not use ipywidgets or Plotly. Run the viewer cells in JupyterLab to activate the interactive controls.

## Running the notebooks

Open a notebook in Jupyter or use its **Open in Colab** badge from this repository checkout. The setup cells handle a missing `google.colab` module as a normal local-Jupyter case; a Google package is not required locally. Colab setup installs the required packages and obtains the MACE-Field implementation needed by these examples. Local Jupyter uses a nearby MACE-Field checkout; set `MACEFIELD_ROOT` to choose one explicitly. Install the notebook's Python dependencies in the active local environment. The setup cells check for the optional Magnetic MACE and LES dependencies. T01 defaults to CPU in local Jupyter and selects CUDA in Colab when a GPU runtime is active; set `MACE_TUTORIAL_DEVICE=cpu` to choose CPU explicitly. The structure selectors, vector controls and animation sliders use the bundled JavaScript viewer in both JupyterLab and Colab. The notebooks do not require ipywidgets or Plotly for these interactions.

The extension code reads implementations from the MACE-Field source project; that source is a software dependency, not a prerequisite tutorial. MACEField, AtomicDipolesMACE and MACELES use `mdi-group/mace-field` from `origin/develop`; Magnetic MACE uses `MagneticScaleShiftMACE` at revision `1bd205048383a0cae6982cccd687e1837aea717a`. T01's primary model trains energy, forces and all field-response labels jointly from random initialization; it does not require a published foundation checkpoint. An optional staged path demonstrates adding response labels to a fitted energy/force model. For research work, check compatibility between a checkpoint and the source revision used to load it.

## Data, checkpoints and training

Regenerate the deterministic analytic teaching datasets from the repository root:

```bash
python MACE_extensions/scripts/prepare_teaching_data.py
```

Train a MACEField model jointly on energy, forces, polarization, Born charges and clamped-ion susceptibility, then audit its double well and switching loop:

```bash
OUT_DIR=/tmp/macefield-joint DEVICE=cuda EPOCHS=160 \
  bash MACE_extensions/scripts/train_macefield_joint.sh
python MACE_extensions/scripts/audit_macefield_surface.py \
  --model /tmp/macefield-joint/MACEField-Landau_run-23.model \
  --head Default --max-force-rmse-mev 16 --out /tmp/macefield-audit
```

The alternative staged path trains an energy/force baseline first, then freezes its standard energy layers while fitting the field adapters to response labels:

```bash
OUT_DIR=/tmp/macefield-energy-force bash MACE_extensions/scripts/train_macefield.sh
INITIAL_MODEL=/tmp/macefield-energy-force/MACEField-Landau_run-23.model \
OUT_DIR=/tmp/macefield-response bash MACE_extensions/scripts/train_macefield_response_finetune.sh
python MACE_extensions/scripts/audit_macefield_surface.py \
  --model /tmp/macefield-response/MACEField-Landau_run-23.model \
  --head Default --max-force-rmse-mev 16 --out /tmp/macefield-response-audit
```

The MACEField fixture samples the soft-mode displacement and five small strain states (three axial, two biaxial). Its polynomial polarization surface makes the active Born charge vary with mode displacement and strain, while a state-dependent clamped-ion susceptibility gives a second changing response. The cubic and tetragonal Ti Z*zz anchors and unstrained tetragonal high-frequency dielectric tensor ε∞ = diag(5.19, 5.19, 5.05) are sourced from literature; other nonlinear coefficients are pedagogical. The response is derived from a shared scalar energy, including finite-field BEC, force, susceptibility and piezoelectric corrections. The analytic spinodals are near ±0.048 V/Å. T01 plots the response surfaces, distinguishes clamped-ion from mode-relaxed susceptibility, derives axial piezoelectric response across strain, and audits the trained field loop. The optional response fine-tune defaults to learning rate 5 × 10⁻⁵ and freeze level 7: it trains MACEField's field adapters while keeping the standard zero-field energy layers fixed. Inspect held-out errors for every target alongside aggregate loss, then run the surface audit. See [the data notes](data/README.md) for equations, coefficient status and limitations.

The other scripts train the dipole, magnetic and LES demonstrations. Set `MACEFIELD_ROOT` to a compatible source checkout; Magnetic MACE training requires revision `1bd205048383a0cae6982cccd687e1837aea717a`. Set `DEVICE`, `EPOCHS`, `BATCH_SIZE` and `OUT_DIR` as needed. Training outputs default to model-specific directories under `MACE_extensions/models/`; the default CPU route keeps the examples usable without a GPU.

## Scope of the examples

The ExtXYZ labels are analytic teaching targets, not quantum-chemistry calculations, DFT references or experimental data. They exercise data formats, model constructors, losses, calculators, symmetries and validation plots. The MACEField switching fields are results for a constrained five-atom BaTiO₃-like teaching probe, not measured coercive fields. The detailed notebooks identify these limits beside the relevant plots.

## Notebook acknowledgements

The source notebooks for Practice I, Practice II, the two advanced application examples and MACE Theory were made by **Ioan Magdău, Ilyes Batatia and Will Baldwin**, and further refined by **Ioan Magdău and Alin Elena**. The extension notebooks were made by **Bradley Martin**. The workshop team is **Bradley Martin, Isaac Parker and Joe Hart**; the team leads the core practical notebooks together, with Bradley leading the extension demonstration individually. See the [repository README](../README.md) for the workshop route and the [figure attribution](figures/ATTRIBUTION.md) for the architecture source.
