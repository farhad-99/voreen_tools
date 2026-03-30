#!/usr/bin/env python3
"""vesselgraph_cli.py – CLI for vessel graph extraction using Voreen.

Takes a segmentation mask in NIFTI format (.nii or .nii.gz) and extracts a
vessel graph, producing nodes.csv and edges.csv in the specified output
directory.
"""

import argparse
import os
import pathlib
import shutil
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def find_voreen_binary(voreen_path=None):
    """Return the directory that contains the voreentool binary, or None."""
    candidates = []

    if voreen_path:
        candidates.append(Path(voreen_path))

    env_path = os.environ.get("VOREEN_BIN")
    if env_path:
        candidates.append(Path(env_path))

    # Check locations relative to this script
    script_dir = Path(__file__).parent
    candidates += [
        script_dir / "binaries" / "voreen-src-unix-nightly" / "bin",
        script_dir / "voreen-src-unix-nightly" / "bin",
        script_dir / "bin",
    ]

    for c in candidates:
        if (c / "voreentool").exists():
            return str(c)

    return None


def find_workspace_file(workspace_file=None):
    """Return the path to the Voreen workspace (.vws) file, or None."""
    if workspace_file:
        p = Path(workspace_file)
        if p.exists():
            return str(p)
        print(f"Error: workspace file not found: {workspace_file}", file=sys.stderr)
        return None

    script_dir = Path(__file__).parent
    default = script_dir / "feature-vesselgraphextraction_customized_command_line.vws"
    if default.exists():
        return str(default)

    return None


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

def run_extraction(input_path, output_dir, bulge_size, voreen_path, workspace_file, verbose=False):
    """Modify the Voreen workspace, execute voreentool, and collect outputs.

    Parameters
    ----------
    input_path : str or Path
        Absolute path to the input NIFTI segmentation mask.
    output_dir : str or Path
        Directory where nodes.csv and edges.csv will be written.
    bulge_size : float
        Pruning threshold passed to the VesselGraphCreator processor.
    voreen_path : str
        Directory containing the voreentool binary.
    workspace_file : str
        Path to the Voreen workspace (.vws) file used as a template.
    verbose : bool
        Print extra status information.

    Returns
    -------
    bool
        True on success, False on failure.
    """
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    nodes_csv = output_dir / "nodes.csv"
    edges_csv = output_dir / "edges.csv"

    with tempfile.TemporaryDirectory(prefix="voreen_") as tmpdir:
        tmpdir = Path(tmpdir)
        workdir = tmpdir / "work"
        tempdir_path = tmpdir / "temp"
        cachedir = tmpdir / "cache"
        ws_dir = tmpdir / "workspace"
        for d in (workdir, tempdir_path, cachedir, ws_dir):
            d.mkdir()

        # graph output goes to a temporary location (not needed by the user)
        graph_tmp = workdir / "graph.vvg.gz"

        # ---- patch workspace file ----------------------------------------
        workspace_copy = ws_dir / "workspace.vws"
        shutil.copy(workspace_file, workspace_copy)

        with open(workspace_copy, "r") as fh:
            ws_content = fh.read()

        bulge_property = (
            f'<Property mapKey="minBulgeSize" name="minBulgeSize" value="{bulge_size}"/>'
        )
        ws_content = ws_content.replace("/home/voreen_data/volume.nii", str(input_path))
        ws_content = ws_content.replace("/home/voreen_data/nodes.csv", str(nodes_csv))
        ws_content = ws_content.replace("/home/voreen_data/edges.csv", str(edges_csv))
        ws_content = ws_content.replace("/home/voreen_data/graph.vvg.gz", str(graph_tmp))
        ws_content = ws_content.replace(
            '<Property mapKey="minBulgeSize" name="minBulgeSize" value="3" />',
            bulge_property,
        )

        with open(workspace_copy, "w") as fh:
            fh.write(ws_content)

        # ---- run voreentool ----------------------------------------------
        cmd = (
            f"cd {shutil.quote(voreen_path)} && ./voreentool"
            f" --workspace {shutil.quote(str(workspace_copy))}"
            f" -platform minimal"
            f" --trigger-volumesaves --trigger-geometrysaves --trigger-imagesaves"
            f" --workdir {shutil.quote(str(workdir))}"
            f" --tempdir {shutil.quote(str(tempdir_path))}"
            f" --cachedir {shutil.quote(str(cachedir))}"
        )

        if verbose:
            print(f"Running: {cmd}")

        ret = os.system(cmd)

        if ret != 0:
            print(f"Error: voreentool exited with non-zero status {ret}.", file=sys.stderr)
            return False

        # ---- verify outputs ----------------------------------------------
        missing = [str(p) for p in (nodes_csv, edges_csv) if not p.exists()]
        if missing:
            print(
                "Error: the following output files were not created:\n"
                + "\n".join(f"  {m}" for m in missing),
                file=sys.stderr,
            )
            return False

    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="vesselgraph",
        description=(
            "Extract a vessel graph from a segmentation mask using Voreen.\n"
            "Produces nodes.csv and edges.csv in the output directory."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract to current directory
  python vesselgraph_cli.py -i segmentation.nii.gz

  # Specify output directory
  python vesselgraph_cli.py -i segmentation.nii.gz -o results/

  # Adjust pruning aggressiveness (default is 3.0)
  python vesselgraph_cli.py -i segmentation.nii.gz -o results/ -b 2.5

  # Provide a custom Voreen binary location
  python vesselgraph_cli.py -i segmentation.nii.gz -o results/ \\
      --voreen-path /opt/voreen/bin/

Environment Variables:
  VOREEN_BIN   Directory containing the voreentool binary
""",
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        metavar="FILE",
        help="Input segmentation mask (.nii or .nii.gz).",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=".",
        metavar="DIR",
        help="Output directory for nodes.csv and edges.csv (default: current directory).",
    )
    parser.add_argument(
        "-b", "--bulge-size",
        type=float,
        default=3.0,
        metavar="FLOAT",
        help=(
            "Bulge size threshold for graph pruning (default: 3.0). "
            "Controls how aggressively small branches are removed. "
            "Typical range: 2.0–5.0."
        ),
    )
    parser.add_argument(
        "--voreen-path",
        metavar="DIR",
        help=(
            "Path to the directory containing the voreentool binary. "
            "Overrides the VOREEN_BIN environment variable."
        ),
    )
    parser.add_argument(
        "--workspace-file",
        metavar="FILE",
        help=(
            "Path to the Voreen workspace (.vws) file. "
            "Defaults to the bundled command-line workspace."
        ),
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ---- validate input --------------------------------------------------
    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")

    name_lower = input_path.name.lower()
    if not (name_lower.endswith(".nii") or name_lower.endswith(".nii.gz")):
        parser.error(
            f"Input must be a NIFTI file (.nii or .nii.gz), got: {input_path.name}"
        )

    # ---- locate Voreen binary --------------------------------------------
    voreen_path = find_voreen_binary(args.voreen_path)
    if voreen_path is None:
        parser.error(
            "Could not find the voreentool binary.\n"
            "  • Extract the Voreen archive:  "
            "tar -xzf binaries/voreen-src-unix-nightly.tar.gz -C binaries/\n"
            "  • Then set VOREEN_BIN or use --voreen-path."
        )

    # ---- locate workspace file -------------------------------------------
    workspace_file = find_workspace_file(args.workspace_file)
    if workspace_file is None:
        parser.error(
            "Could not find the Voreen workspace file.\n"
            "  • The bundled workspace is: "
            "feature-vesselgraphextraction_customized_command_line.vws\n"
            "  • Use --workspace-file to specify a custom path."
        )

    # ---- print summary ---------------------------------------------------
    if args.verbose:
        print(f"Input:          {input_path.resolve()}")
        print(f"Output dir:     {Path(args.output_dir).resolve()}")
        print(f"Bulge size:     {args.bulge_size}")
        print(f"Voreen binary:  {voreen_path}")
        print(f"Workspace file: {workspace_file}")
        print()

    print(f"Extracting vessel graph from: {input_path}")

    success = run_extraction(
        input_path=args.input,
        output_dir=args.output_dir,
        bulge_size=args.bulge_size,
        voreen_path=voreen_path,
        workspace_file=workspace_file,
        verbose=args.verbose,
    )

    if success:
        output_dir = Path(args.output_dir).resolve()
        print(f"\nDone! Output files written to: {output_dir}")
        print("  nodes.csv")
        print("  edges.csv")
    else:
        print("\nExtraction failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
