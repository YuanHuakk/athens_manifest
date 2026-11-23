#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
: "${TREE:?Set TREE to the Project Infinity X source root}"
cd "$TREE"
source "build/envsetup.sh"
variant="${BUILD_VARIANT:-user}"
lunch "infinity_athens-$variant"
if [[ "${TARGET_PRODUCT:-}" != infinity_athens || "${TARGET_BUILD_VARIANT:-}" != "$variant" ]]; then
    echo "Could not select infinity_athens-$variant" >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then set -- bacon; fi
m -j"${JOBS:-12}" "$@"
