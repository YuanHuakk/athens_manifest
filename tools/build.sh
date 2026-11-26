#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
: "${TREE:?Set TREE to the PixelOS source root}"
cd "$TREE"
source build/envsetup.sh
requested_variant="${BUILD_VARIANT:-user}"
breakfast athens "$requested_variant"
if [[ "${TARGET_PRODUCT:-}" != custom_athens || "${TARGET_BUILD_VARIANT:-}" != "$requested_variant" ]]; then
    echo "Could not select custom_athens-$requested_variant (selected ${TARGET_PRODUCT:-unset}-${TARGET_BUILD_VARIANT:-unset})" >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then set -- pixelos; fi
m -j"${JOBS:-12}" "$@"
