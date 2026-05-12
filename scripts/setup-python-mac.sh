#!/usr/bin/env bash
# Downloads python-build-standalone for both Mac architectures and installs
# the packages required by ATD 2K APP into each.
# Run this once on a Mac before building the DMG releases:
#   bash scripts/setup-python-mac.sh
# Output: frontend/resources/python-mac-x64/  and  frontend/resources/python-mac-arm64/

set -euo pipefail

PYTHON_VERSION="3.12.8"
RELEASE_DATE="20241219"
BASE_URL="https://github.com/indygreg/python-build-standalone/releases/download/${RELEASE_DATE}"
PACKAGES="nba_api pandas requests"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="${SCRIPT_DIR}/../frontend/resources"

build_arch() {
  local ARCH=$1        # x86_64 or aarch64
  local TARGET=$2      # x64 or arm64

  local FILENAME="cpython-${PYTHON_VERSION}+${RELEASE_DATE}-${ARCH}-apple-darwin-install_only.tar.gz"
  local URL="${BASE_URL}/${FILENAME}"
  local OUT_DIR="${RESOURCES_DIR}/python-mac-${TARGET}"
  local TMP_TAR="/tmp/python-mac-${TARGET}.tar.gz"
  local TMP_EXTRACT="/tmp/python-mac-${TARGET}-extract"

  echo ""
  echo "==> Building Python for Mac ${TARGET} (${ARCH})"

  if [ -f "${OUT_DIR}/bin/python3.12" ]; then
    echo "    Already exists at ${OUT_DIR} — skipping download."
    echo "    Delete the folder and re-run to refresh."
    return 0
  fi

  echo "    Downloading ${FILENAME}..."
  curl -L --progress-bar "${URL}" -o "${TMP_TAR}"

  echo "    Extracting..."
  rm -rf "${TMP_EXTRACT}"
  mkdir -p "${TMP_EXTRACT}"
  tar -xzf "${TMP_TAR}" -C "${TMP_EXTRACT}"

  # python-build-standalone extracts to a 'python' subdirectory
  rm -rf "${OUT_DIR}"
  mv "${TMP_EXTRACT}/python" "${OUT_DIR}"
  rm -rf "${TMP_EXTRACT}" "${TMP_TAR}"

  echo "    Installing packages: ${PACKAGES}..."
  "${OUT_DIR}/bin/python3.12" -m pip install --upgrade pip --quiet
  "${OUT_DIR}/bin/python3.12" -m pip install ${PACKAGES} --quiet

  # Strip test files and docs to save space (~30MB)
  find "${OUT_DIR}" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
  find "${OUT_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
  find "${OUT_DIR}" -name "*.pyc" -delete 2>/dev/null || true

  echo "    Done. Size: $(du -sh "${OUT_DIR}" | cut -f1)"
}

mkdir -p "${RESOURCES_DIR}"

build_arch "x86_64" "x64"
build_arch "aarch64" "arm64"

echo ""
echo "==> Python setup complete."
echo "    You can now run: cd frontend && npm run dist:mac"
