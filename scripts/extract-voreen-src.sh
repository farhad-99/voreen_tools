#!/usr/bin/env bash
# Extract the Voreen source tarball only when the tarball has changed.
# A SHA-256 marker file (binaries/.voreen-src-sha) is used to detect changes.
set -euo pipefail

TARBALL=binaries/voreen-src-unix-nightly.tar.gz
MARKER=binaries/.voreen-src-sha
DEST=binaries/voreen-src-unix-nightly

NEW_SHA=$(sha256sum "$TARBALL" | cut -d' ' -f1)
OLD_SHA=$(cat "$MARKER" 2>/dev/null || echo "none")

if [ "$NEW_SHA" != "$OLD_SHA" ] || [ ! -d "$DEST" ]; then
  echo "Extracting Voreen source..."
  rm -rf "$DEST"
  tar -xzf "$TARBALL" -C binaries/
  echo "$NEW_SHA" > "$MARKER"
else
  echo "Voreen source already up-to-date, skipping extraction."
fi
