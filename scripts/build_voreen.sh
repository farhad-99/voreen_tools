#!/usr/bin/env bash
# build_voreen.sh – extract and build voreentool from the bundled source tarball.
# Run from the repository root with: pixi run build-voreen
# or directly: bash scripts/build_voreen.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINARIES_DIR="${REPO_ROOT}/binaries"
SRC_TARBALL="${BINARIES_DIR}/voreen-src-unix-nightly.tar.gz"
SRC_DIR="${REPO_ROOT}/voreen-src-unix-nightly"
BUILD_DIR="${SRC_DIR}/build"
JOBS="${BUILD_JOBS:-$(nproc)}"

echo "=== Voreen build script ==="
echo "Source tarball : ${SRC_TARBALL}"
echo "Build directory: ${BUILD_DIR}"
echo "Parallel jobs  : ${JOBS}"

# 1. Extract source
if [ ! -d "${SRC_DIR}" ]; then
    echo "Extracting source..."
    tar -xzf "${SRC_TARBALL}" -C "${REPO_ROOT}"
else
    echo "Source directory already exists, skipping extraction."
fi

# 2. Configure with CMake
mkdir -p "${BUILD_DIR}"
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DOPENGL_gl_PREFERENCE=LEGACY \
    -DVRN_MODULE_BASE=ON \
    -DVRN_MODULE_BIGDATAIMAGEPROCESS=ON \
    -DVRN_MODULE_CONNEXE=ON \
    -DVRN_MODULE_DEPRECATED=OFF \
    -DVRN_MODULE_DEVIL=ON \
    -DVRN_MODULE_ENSEMBLEANALYSIS=ON \
    -DVRN_MODULE_EXPERIMENTAL=OFF \
    -DVRN_MODULE_FFMPEG=OFF \
    -DVRN_MODULE_FLOWANALYSIS=ON \
    -DVRN_MODULE_GDCM=OFF \
    -DVRN_MODULE_HDF5=ON \
    -DVRN_MODULE_ITK=OFF \
    -DVRN_MODULE_ITK_GENERATED=OFF \
    -DVRN_MODULE_OPENCL=OFF \
    -DVRN_MODULE_OPENMP=OFF \
    -DVRN_MODULE_PLOTTING=ON \
    -DVRN_MODULE_POI=OFF \
    -DVRN_MODULE_PVM=ON \
    -DVRN_MODULE_PYTHON=ON \
    -DVRN_MODULE_RANDOMWALKER=ON \
    -DVRN_MODULE_SAMPLE=OFF \
    -DVRN_MODULE_SEGY=ON \
    -DVRN_MODULE_STAGING=ON \
    -DVRN_MODULE_STEREOSCOPY=ON \
    -DVRN_MODULE_SURFACE=ON \
    -DVRN_MODULE_TIFF=OFF \
    -DVRN_MODULE_VESSELNETWORKANALYS=ON \
    -DVRN_MODULE_VTK=ON \
    -DVRN_MODULE_ZIP=ON \
    -DVRN_BUILD_VOREENTOOL=ON \
    -DVRN_BUILD_VOREENVE=OFF \
    -DVRN_USE_HDF5_VERSION=1.10 \
    -DVRN_USE_SSE41=ON

# 3. Build
cmake --build "${BUILD_DIR}" --parallel "${JOBS}"

echo ""
echo "=== Build complete ==="
echo "voreentool binary: ${BUILD_DIR}/bin/voreentool"
echo ""
echo "Pass the path to parse_voreen.py:"
echo "  python parse_voreen.py -vp '${BUILD_DIR}/bin' ..."
