# MACE_tutorials

Written for first-year PhD students in computational chemistry, this repository brings together hands-on and advanced notebooks for learning, applying and extending MACE-based machine-learning interatomic potentials. The main workshop route is practical: inspect data, fit and evaluate a model, then improve it through iterative training and active learning. Advanced theory and applications are optional routes for students who want to go further. The MACE extension examples form a short demonstration near the end of the session.

## Choose a notebook route

### Core workshop: work through these in order

1. [**MACE Practice I**](MACE_in_practice_I/T01-MACE-Practice-I.ipynb) — inspect atomistic data, configure and train a MACE model, and evaluate its predictions.
2. [**MACE Practice II**](MACE_in_practice_II/T02-MACE-Practice-II.ipynb) — improve a model using iterative training and active learning, then explore foundation models and fine-tuning.

### Optional: continue into advanced material

Open a notebook from [`MACE_advanced/`](MACE_advanced/) when you are ready for more theory or applications:

| Notebook | Focus |
|---|---|
| [T03 · MACE Theory](MACE_advanced/T03-MACE-Theory.ipynb) | Inspect MACE architecture and code-level operations. |
| [T04 · MLIP applications](MACE_advanced/T04-MLIP-Apps.ipynb) | Apply MLIPs to lithium diffusion and nudged elastic band workflows. |
| [T05 · Molecular NEB](MACE_advanced/T05-MACE-neb.ipynb) | Explore a molecular reaction pathway with an MLIP. |

### Closing demonstration: examples of extending MACE

[`MACE_extensions/`](MACE_extensions/) contains a short architecture overview followed by focused examples. During the workshop, these form a **30–45 minute demonstration near the end**; the notebooks are also available for later self-study:

| Notebook | Adaptation illustrated |
|---|---|
| [T00 · Extending MACE](MACE_extensions/T00-Extending-MACE.ipynb) | Compare where additional inputs, outputs and physical terms can enter a MACE model. |
| [T01 · MACEField](MACE_extensions/T01-MACEField.ipynb) | Condition energy and response on an external electric field. |
| [T02 · AtomicDipolesMACE](MACE_extensions/T02-AtomicDipolesMACE.ipynb) | Predict an equivariant vector property. |
| [T03 · Magnetic MACE](MACE_extensions/T03-MagneticMACE.ipynb) | Include magnetic moments when predicting energies and forces. |
| [T04 · MACELES](MACE_extensions/T04-MACELES.ipynb) | Add an explicit long-range electrostatic energy contribution. |

## Lennard-Jones Centre summer school

These materials support the Lennard-Jones Centre and Thomas Young Centre Summer School on Atomic-Scale Modelling, held in Cambridge from **28 September to 2 October 2026**. The tutorial session is on **Thursday 1 October, 14:00–17:00**, led by Bradley Martin, Joe Hart and Isaac Parker.

## Notebook credits and provenance

The notebooks in this repository are the workshop materials; use the links above to navigate between them without needing another tutorial collection. The source notebooks for Practice I, Practice II, the two advanced application examples, and the [MACE Theory notebook](MACE_advanced/T03-MACE-Theory.ipynb) were made by Ioan Magdău, Ilyes Batatia and Will Baldwin, and further refined by Ioan Magdău and Alin Elena. 

## Running the notebooks

Open notebooks in Jupyter or use their **Open in Colab** links. You can launch Jupyter from the repository root or the notebook folder; setup cells select the notebook folder and use the datasets included here. Install each notebook's Python dependencies in your local environment before running it. The extension examples include local/Colab setup and training scripts; see [`MACE_extensions/README.md`](MACE_extensions/README.md) and [`MACE_extensions/data/README.md`](MACE_extensions/data/README.md) for their source and data requirements.

The extension datasets are small analytic teaching targets, not DFT or experimental data. The model-specific notebooks explain what each example demonstrates and the limits of its scientific interpretation.
