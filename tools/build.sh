#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
: "${TREE:?Set TREE to the Evolution X source root}"
cd "$TREE"
source "build/envsetup.sh"
lunch "lineage_athens-${BUILD_VARIANT:-user}"
if [ "$#" -eq 0 ]; then set -- evolution; fi
m -j"${JOBS:-12}" "$@"
