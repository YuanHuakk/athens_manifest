#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
: "${TREE:?Set TREE to the PixelOS source root}"
cd "$TREE"
source build/envsetup.sh
breakfast athens "${BUILD_VARIANT:-user}"
if [ "$#" -eq 0 ]; then set -- pixelos; fi
m -j"${JOBS:-12}" "$@"
