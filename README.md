## Voreen 5.2 - Stable Version for Graph Generation

This repository contains the modified source code and stable release of Voreen 5.2 that can be used for vessel extraction.
Adaptations have been made by Dominik Drees of Uni Müster, after email correspondance to Julian McGinnis (TUM).
Future Releases of Voreen will incorporate these source code changes as well.

This version contains bugfixes that mitigate scalability issues of the JSON Streaming Serializer of Voreen v5.2.0:

* `binaries/voreen-src-unix-nightly.tar.gz` – source code that can be built with CMake
* `binaries/VoreenVE-nightly.tar.gz` – pre-built Linux AppImage (GUI + headless tool)

---

## Step-by-Step CLI Guide: Segmentation Mask → nodes.csv + edges.csv

This guide walks you through running the **VesselGraph extraction pipeline** entirely from the command line.
Input: a binary segmentation mask (`.nii` or `.nii.gz`)
Output: `<stem>_b_<bulge>_nodes.csv` and `<stem>_b_<bulge>_edges.csv`

---

### Step 1 – Install Pixi

[Pixi](https://pixi.sh) manages all Python and C/C++ dependencies in a reproducible environment.

```bash
curl -fsSL https://pixi.sh/install.sh | bash
# Restart your shell or source the updated profile
```

### Step 2 – Clone the repository

```bash
git clone https://github.com/farhad-99/voreen_tools.git
cd voreen_tools
```

### Step 3 – Install the Python environment

```bash
pixi install
```

This creates a conda environment with Python, NumPy, pandas, matplotlib, and all C/C++ build libraries (CMake, Boost, GLEW, Qt5, HDF5, VTK, …) listed in `pixi.toml`.

### Step 4 – Obtain the `voreentool` binary

You have two options:

#### Option A – Use the pre-built AppImage (quickest)

```bash
cd binaries
tar -xzf VoreenVE-nightly.tar.gz
cd ..
# The headless binary is at: binaries/VoreenVE-nightly/bin/voreentool
VOREEN_BIN="$(pwd)/binaries/VoreenVE-nightly/bin"
```

#### Option B – Build from source

```bash
pixi run build-voreen
# After a successful build:
VOREEN_BIN="$(pwd)/voreen-src-unix-nightly/build/bin"
```

> The build script (`scripts/build_voreen.sh`) applies the exact CMake flags documented in `binaries/README.md`
> and uses the Pixi-managed compilers and libraries automatically.

### Step 5 – Create working directories

Voreen needs three scratch directories for intermediate data.

```bash
mkdir -p voreen_work voreen_temp voreen_cache output
```

### Step 6 – Run the pipeline

```bash
pixi run pipeline \
  --input_image  /path/to/your/segmentation.nii.gz \
  --bulge_size   2.7 \
  --voreen_tool_path "${VOREEN_BIN}" \
  --workspace_file   feature-vesselgraphextraction_customized_command_line.vws \
  --workdir  "$(pwd)/voreen_work" \
  --tempdir  "$(pwd)/voreen_temp" \
  --cachedir "$(pwd)/voreen_cache" \
  --output_dir "$(pwd)/output"
```

Or call the script directly inside the Pixi shell (`pixi shell`):

```bash
python parse_voreen.py \
  -i  /path/to/your/segmentation.nii.gz \
  -b  2.7 \
  -vp "${VOREEN_BIN}" \
  -wp feature-vesselgraphextraction_customized_command_line.vws \
  -wd "$(pwd)/voreen_work" \
  -td "$(pwd)/voreen_temp" \
  -cd "$(pwd)/voreen_cache" \
  -o  "$(pwd)/output"
```

**Key arguments**

| Argument | Short | Description |
|---|---|---|
| `--input_image` | `-i` | Path to the segmentation mask (`.nii` or `.nii.gz`) |
| `--bulge_size` | `-b` | Bulge-size pruning threshold (e.g. `2.7`). See paper for details. |
| `--voreen_tool_path` | `-vp` | Directory containing the `voreentool` binary |
| `--workspace_file` | `-wp` | Path to the `.vws` workspace file (default: repo root) |
| `--workdir` | `-wd` | Voreen working directory (intermediate files) |
| `--tempdir` | `-td` | Voreen temporary directory |
| `--cachedir` | `-cd` | Voreen cache directory |
| `--output_dir` | `-o` | Directory where `nodes.csv` and `edges.csv` are written (defaults to `--workdir`) |

### Step 7 – Inspect the outputs

After the pipeline finishes, the `--output_dir` folder contains:

```
output/
├── segmentation_b_2_7_nodes.csv   # node table: id, x, y, z, radius, …
├── segmentation_b_2_7_edges.csv   # edge table: id, node1id, node2id, length, …
└── segmentation_b_2_7_graph.vvg.gz
```

### Step 8 – (Optional) Post-process the edge list

```bash
pixi run post-process \
  --edge_list output/segmentation_b_2_7_edges.csv \
  --node_list output/segmentation_b_2_7_nodes.csv
```

---

### Choosing the right workspace

| Dataset size | Recommended workspace |
|---|---|
| MB – low GB (testing) | `vesselgraphextraction` (built-in, includes visualisation) |
| Large GB – TB (production) | `feature-vesselgraphextraction_customized_command_line.vws` (headless, no visualisation, more scalable) |

To switch Application Mode ↔ Network Mode in the GUI use **F4** / **F5**.

---

### Running on a cluster (Charliecloud / SLURM)

See `examples/job_voreen_slurm.cmd` for a SLURM job script.
Example Charliecloud invocation:

```bash
ch-run \
  -b /lrz/sys/.:/lrz/sys/ \
  -b $SCRATCH/.:/scratch \
  -w /path/to/docker_directory/voreen_without_bindings/ \
  sh /home/voreen-build/bin/run_voreen.sh --no-home
```

Reference: https://doku.lrz.de/display/PUBLIC/Charliecloud+at+LRZ

---

#### VTK-based visualisation of graphs

Use `visualization_scripts/voreen_graph_radius_to_vtk.py` to generate a VTK PolyData file (e.g. open in Paraview) from the graph that displays vessels as tubes, incorporating the average vessel diameter as tube diameter.

To display the tubular structures in ITK-Snap, convert the `.vtk` file using `visualization_scripts/vtk_to_nifti.py`.

### Graph Pruning

As mentioned in the paper by Drees et.al., the graphs are pruned by utilizing a "scale invariant, dimensionless property", the bulge size parameter. It is defined as:

"Intuitively, the bulge size measures how far a bump, bulge or branch has to extend from a parent vessel in order to be considered a separate vessel. This size is expressed relative to the radius of its parent vessel and itself, making it scale-independent. More formally, the bulge size is an edge feature, that is computed during the feature extraction, and is only defined for bulging edges, i.e., edges that connect a leaf node (degree 1) and a branching point (degree > 2)."

## Voreen Citation

If you use voreen, please cite:
```
@article{drees2021scalable,
  title={Scalable robust graph and feature extraction for arbitrary vessel networks in large volumetric datasets},
  author={Drees, Dominik and Scherzinger, Aaron and H{\"a}gerling, Ren{\'e} and Kiefer, Friedemann and Jiang, Xiaoyi},
  journal={BMC bioinformatics},
  volume={22},
  number={1},
  pages={1--28},
  year={2021},
  publisher={BioMed Central}
}
```

### Post-processing

For post-processing, as performed in our NeurIPS paper, please use the script provided in the post_processing section.
If you use our scripts for post-processing, please consider citing us:

```
@inproceedings{paetzold2021whole,
  title={Whole brain vessel graphs: A dataset and benchmark for graph learning and neuroscience},
  author={Paetzold, Johannes C and McGinnis, Julian and Shit, Suprosanna and Ezhov, Ivan and B{\"u}schl, Paul and Prabhakar, Chinmay and Sekuboyina, Anjany and Todorov, Mihail and Kaissis, Georgios and Ert{\"u}rk, Ali and others},
  booktitle={Thirty-Fifth Conference on Neural Information Processing Systems Datasets and Benchmarks Track (Round 2)},
  year={2021}
}
```
