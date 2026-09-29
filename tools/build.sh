#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
: "${TREE:?Set TREE to the PixelOS source root}"
cd "$TREE"
source build/envsetup.sh
lunch custom_athens trunk_staging userdebug
if [ "$#" -eq 0 ]; then set -- pixelos; fi
m -j"${JOBS:-12}" "$@"
