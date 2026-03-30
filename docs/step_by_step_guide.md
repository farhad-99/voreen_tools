# Step-by-Step Guide: Vessel Graph Extraction

This guide walks you through extracting a vessel graph from a 3-D segmentation
mask stored in NIFTI format (`.nii` or `.nii.gz`) using the Voreen-based CLI
provided in this repository.

**Output:** `nodes.csv` and `edges.csv` – a graph representation of the vessel
network with 3-D positions, connectivity, and geometric measurements.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Linux x86-64 | Required for the provided Voreen binary |
| Python ≥ 3.8 | Managed automatically by pixi |
| [pixi](https://pixi.sh) | Cross-platform package manager |

---

## Step 1 – Install pixi

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

Restart your terminal (or run `source ~/.bashrc` / `source ~/.zshrc`) so that
the `pixi` command is available.

Verify the installation:

```bash
pixi --version
```

---

## Step 2 – Clone the repository

```bash
git clone https://github.com/farhad-99/voreen_tools.git
cd voreen_tools
```

---

## Step 3 – Install Python dependencies

From the repository root, run:

```bash
pixi install
```

This creates an isolated environment with all required packages (pandas, numpy,
scipy, nibabel, scikit-image, vedo, vtk, matplotlib).  All subsequent
`pixi run` commands automatically use this environment.

---

## Step 4 – Build the Voreen binary

`voreentool` (the Voreen command-line tool) must be **compiled from source**.
The source code is provided in `binaries/voreen-src-unix-nightly.tar.gz`.

### 4a – Extract the source archive

```bash
tar -xzf binaries/voreen-src-unix-nightly.tar.gz -C binaries/
```

This creates `binaries/voreen-src-unix-nightly/` containing the Voreen source.

### 4b – Build Voreen

See [`binaries/README.md`](../binaries/README.md) for full platform-specific
instructions.  In brief:

1. Install system dependencies:
   ```bash
   sudo apt install g++ git cmake libboost-all-dev libglew-dev qt5-default \
       libqt5svg5-dev libdevil-dev ffmpeg libswscale-dev libavcodec-dev \
       libavformat-dev
   ```

2. Create an out-of-tree build directory and configure:
   ```bash
   mkdir -p binaries/voreen-build
   cd binaries/voreen-build
   ccmake ../voreen-src-unix-nightly
   ```
   Enable at least `VRN_MODULE_VESSELNETWORKANALYS` and `VRN_BUILD_VOREENTOOL`
   plus all other modules listed in `binaries/README.md`.

3. Compile:
   ```bash
   make -j$(nproc)
   ```

The compiled binary will be at `binaries/voreen-build/bin/voreentool`.

### 4c – Export the binary path

```bash
export VOREEN_BIN="$(pwd)/binaries/voreen-build/bin"
```

> **Tip:** Add this `export` line to your `~/.bashrc` or `~/.zshrc` so it
> persists across terminal sessions.

Alternatively you can pass the path directly to the CLI with
`--voreen-path` (see [Step 5](#step-5--run-the-cli)).

---

## Step 5 – Run the CLI

### Minimal usage

```bash
pixi run vesselgraph -i /path/to/segmentation.nii.gz
```

Outputs `nodes.csv` and `edges.csv` in the current directory.

### Specify an output directory

```bash
pixi run vesselgraph -i segmentation.nii.gz -o results/
```

```
results/
├── nodes.csv
└── edges.csv
```

### All options

```
usage: vesselgraph [-h] -i FILE [-o DIR] [-b FLOAT]
                   [--voreen-path DIR] [--workspace-file FILE] [-v]

  -i FILE, --input FILE            Input segmentation mask (.nii or .nii.gz)
  -o DIR,  --output-dir DIR        Output directory (default: current directory)
  -b FLOAT, --bulge-size FLOAT     Pruning threshold (default: 3.0)
  --voreen-path DIR                Path to the voreentool binary directory
  --workspace-file FILE            Path to the Voreen workspace (.vws) file
  -v, --verbose                    Print verbose status output
```

### Examples

```bash
# Store results in ./results/
pixi run vesselgraph -i brain_vessels.nii.gz -o results/

# Less aggressive pruning – preserve more fine branches
pixi run vesselgraph -i brain_vessels.nii.gz -o results/ -b 2.5

# More aggressive pruning – keep only large vessels
pixi run vesselgraph -i brain_vessels.nii.gz -o results/ -b 4.0

# Verbose output, custom binary path
pixi run vesselgraph -i brain_vessels.nii.gz -o results/ \
    --voreen-path /opt/voreen/bin/ -v
```

---

## Step 6 – Understand the output

### `nodes.csv`

Semicolon-separated file — one row per graph node.

| Column | Description |
|---|---|
| `id` | Unique node identifier |
| `pos_x`, `pos_y`, `pos_z` | 3-D position in voxel coordinates |
| `degree` | Number of edges connected to this node |
| `isAtSampleBorder` | `1` if the node touches the volume boundary |

### `edges.csv`

Semicolon-separated file — one row per vessel segment.

| Column | Description |
|---|---|
| `id` | Unique edge identifier |
| `node1id`, `node2id` | Endpoint node IDs |
| `length` | Path length of the segment (voxels) |
| `volume` | Vessel volume (voxels³) |
| `num_voxels` | Number of voxels in this segment |
| `curveness` | Ratio of path length to Euclidean distance (1 = straight) |
| `avgRadiusAvg` | Mean vessel radius |
| `avgRadiusStd` | Standard deviation of vessel radius |
| `minRadiusAvg` / `maxRadiusAvg` | Min / max radius averages |
| `roundnessAvg` | Average cross-sectional roundness |
| `hasNodeAtSampleBorder` | `1` if either endpoint is at the volume boundary |

---

## Step 7 (Optional) – Post-process the graph

The raw Voreen output may contain duplicate edges (the same node pair
represented more than once).  The post-processing script deduplicates them and
recomputes node degrees:

```bash
pixi run post-process -e results/edges.csv -n results/nodes.csv
```

Output files:

```
results/
├── edges_processed.csv
└── nodes_processed.csv
```

---

## Step 8 (Optional) – Visualise the graph

### Generate a 3-D tube mesh (for Paraview)

```bash
pixi run to-vtk \
    -n results/nodes_processed.csv \
    -e results/edges_processed.csv \
    -s 1.0 \
    -o results/
```

This produces a VTK PolyData file where each vessel segment is rendered as a
tube with radius proportional to the average vessel radius.

### Convert the tube mesh to NIFTI (for ITK-Snap)

```bash
pixi run vtk-to-nifti \
    -i results/segmentation_tube_graph_scaling_factor_1.0.vtk
```

---

## Bulge Size Parameter

The `--bulge-size` / `-b` parameter controls branch pruning.  It is a
scale-invariant measure of how far a branch must extend beyond its parent
vessel to be kept in the graph.

| Value | Effect |
|---|---|
| 2.0–2.5 | Minimal pruning – preserves fine capillary-like branches |
| **3.0** | **Default – balanced pruning** |
| 3.5–5.0 | Aggressive pruning – retains only the largest vessel segments |

---

## Troubleshooting

**`Could not find the voreentool binary`**
- `voreentool` must be **compiled from source** – see [Step 4](#step-4--build-the-voreen-binary).
- After building, verify the binary exists: `ls binaries/voreen-build/bin/voreentool`.
- Set `VOREEN_BIN` or pass `--voreen-path`.

**`Input must be a NIFTI file`**
- Only `.nii` and `.nii.gz` files are supported.

**`nodes.csv was not created`**
- Ensure the Voreen binary is executable: `chmod +x binaries/voreen-build/bin/voreentool`.
- Run with `-v` to see the exact voreentool command being executed.
- Confirm the input is a valid binary (or near-binary) segmentation volume.

**Building Voreen from source**
`voreentool` is not distributed as a pre-built binary — it must be compiled
from `binaries/voreen-src-unix-nightly.tar.gz`.
See `binaries/README.md` for platform-specific build instructions and required
CMake flags.

---

## Citations

If you use these tools in your research, please cite:

**Voreen vessel extraction algorithm:**

```bibtex
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

**Post-processing scripts (if used):**

```bibtex
@inproceedings{paetzold2021whole,
  title={Whole brain vessel graphs: A dataset and benchmark for graph learning and neuroscience},
  author={Paetzold, Johannes C and McGinnis, Julian and Shit, Suprosanna and Ezhov, Ivan and B{\"u}schl, Paul and Prabhakar, Chinmay and Sekuboyina, Anjany and Todorov, Mihail and Kaissis, Georgios and Ert{\"u}rk, Ali and others},
  booktitle={Thirty-Fifth Conference on Neural Information Processing Systems Datasets and Benchmarks Track (Round 2)},
  year={2021}
}
```
