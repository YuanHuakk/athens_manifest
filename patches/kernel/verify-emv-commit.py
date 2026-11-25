#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Apply the Athens EMV patch to the pinned MiCode files and test the implementation."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

BASE = "1f1cd9c1b674014ae6ca324ffea12c96e121d6e1"
HERE = Path(__file__).resolve().parent
PATCH = HERE / "0001-msm-bind-nova-emv-to-display-commit.patch"
FIXTURE = HERE / "tests" / "emv-commit-fixture.c"


def run(*args, cwd=None, capture=False):
    return subprocess.run(
        args, cwd=cwd, check=True, stdout=subprocess.PIPE if capture else None
    ).stdout


def section(source, start, end):
    at = source.index(start)
    return source[at : source.index(end, at)]


def ordered(source, *fragments):
    for fragment in fragments:
        at = source.index(fragment)
        source = source[at + len(fragment) :]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "display_checkout",
        type=Path,
        help="MiCode display drivers Git checkout containing the pinned revision",
    )
    args = parser.parse_args()
    checkout = args.display_checkout.resolve()
    with tempfile.TemporaryDirectory(prefix="athens-emv-test-") as work:
        root = Path(work)
        inputs = (
            run("git", "apply", "--numstat", str(PATCH), capture=True, cwd=root)
            .decode()
            .splitlines()
        )
        for row in inputs:
            name = row.split("\t")[2]
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                run("git", "show", f"{BASE}:{name}", cwd=checkout, capture=True)
            )
        run("git", "apply", "--check", str(PATCH), cwd=root)
        run("git", "apply", str(PATCH), cwd=root)
        run("git", "apply", "--reverse", "--check", str(PATCH), cwd=root)

        def source(name):
            return (root / "msm" / name).read_text()

        driver = source("mi_disp/mi_sde_connector.c")
        kms = source("sde/sde_kms.c")
        crtc = source("sde/sde_crtc.c")
        encoder = source("sde/sde_encoder.c")
        connector = source("sde/sde_connector.c")
        worker = source("mi_disp/mi_disp_feature.c")
        ordered(connector, "mi_emv_put(c_state->mi_emv);", "c_state->mi_emv = NULL;")
        ordered(
            connector,
            "msm_property_duplicate_state(",
            "c_state->mi_emv = NULL;",
            "c_state->mi_emv_reset = false;",
            "CONNECTOR_PROP_MI_EMV_INFO].value = 0;",
        )
        ordered(
            connector,
            "mi_sde_connector_set_emv_buffer(c_conn, c_state, u64_to_user_ptr(val))",
        )
        ordered(
            kms,
            "static void sde_kms_prepare_commit(",
            "if (!kms || !state)",
            "dev = sde_kms->dev;",
            "if (!dev || !dev->dev_private)",
            "old_conn_state->crtc != conn_state->crtc",
            "mi_emv_before_kickoff(",
            "drm_atomic_crtc_needs_modeset(cstate)",
        )
        ordered(
            kms,
            "static void sde_kms_commit(",
            "for_each_oldnew_crtc_in_state(",
            "old_mask & new_mask : 0;",
            "mi_emv_before_kickoff(",
            "sde_crtc_commit_kickoff(",
            "trigger_commit[disp_op]",
            "if (!s->mi_emv_hfi_submitted)",
            "mi_emv_kicked_encoders = 0;",
        )
        ordered(
            crtc,
            "void sde_crtc_commit_kickoff(",
            "if (sde_encoder_kickoff_observed(encoder, true)",
            "!is_error)",
            "mi_emv_kicked_encoders |= drm_encoder_mask(encoder)",
        )
        ordered(
            encoder,
            "static inline bool _sde_encoder_trigger_flush(",
            "return false;",
            "valid = !phys->fence_error_handle_in_progress;",
            "phys->ops.trigger_flush(phys);",
            "return valid;",
        )
        ordered(
            encoder,
            "static bool _sde_encoder_kickoff_phys(",
            "input_fence_status < 0",
            "goto handle_elevated_ahb_vote;",
            "if (_sde_encoder_trigger_flush(",
            "phys == sde_enc->cur_master",
            "return flushed;",
        )
        ordered(
            kms,
            "static void sde_kms_complete_commit(",
            "for_each_oldnew_connector_in_state(",
            "struct mi_emv_packet *packet = to_sde_connector_state(new_conn_state)->mi_emv;",
            "sde_kms_emv_confirmed(old_state, connector, new_conn_state)",
            "c_conn->ops.post_kickoff(connector, &params)",
            "if (emv_display)",
            "mi_emv_after_kickoff(connector, emv_display, packet)",
        )
        ordered(
            kms,
            "static void sde_kms_wait_for_commit_done(",
            "sde_encoder_wait_for_event_observed(encoder,",
            "if (ret && ret != -EWOULDBLOCK)",
            "break;",
            "recovery_rc = sde_encoder_hw_fence_error_observed(encoder, &had_fault)",
            "sde_kms_emv_wait_succeeded(observed, ret, had_fault, recovery_rc)",
            "mi_emv_done_encoders |= drm_encoder_mask(encoder)",
        )
        ordered(
            encoder,
            "int sde_encoder_wait_for_event_observed(",
            "*observed = false;",
            "count > 0;",
            "phys == sde_enc->cur_master",
            "phys->enable_state == SDE_ENC_ENABLED",
            "ret = fn_wait(phys);",
            "if (active_master && !ret)",
            "*observed = true;",
        )
        ordered(
            encoder,
            "int sde_encoder_hw_fence_error_observed(",
            "*had_fault = false;",
            "!sde_enc->phys_encs[0]->sde_hw_fence_error_status",
            "*had_fault = true;",
            "phys_enc->sde_hw_fence_error_status = false;",
        )
        ordered(
            source("sde/hfi/hfi_kms.c"),
            "static int hfi_kms_trigger_commit(",
            "if (disp_id == U32_MAX)",
            "trigger_rc = hfi_adapter_add_set_property(",
            "ret = hfi_adapter_set_cmd_buf(",
            "if (ret)",
            "return ret;",
            "!trigger_rc)",
            "mi_emv_hfi_submitted = true;",
        )
        ordered(
            worker,
            "kthread_create_worker(",
            "mi_emv_attach(",
            "mi_emv_detach(",
            "kthread_destroy_worker(",
        )
        ordered(
            source("dsi/dsi_drm.c"),
            "int dsi_conn_post_kickoff_emv(",
            "if (emv_display && is_mi_dev_support_nova())",
            "*emv_display = display;",
            "int dsi_conn_post_kickoff(",
            "dsi_conn_post_kickoff_emv(connector, params, NULL)",
        )
        original = run(
            "git",
            "show",
            f"{BASE}:msm/mi_disp/mi_sde_connector.c",
            cwd=checkout,
            capture=True,
        ).decode()
        default_setter = original[
            original.index("int mi_sde_connector_set_emv_buffer(") :
        ].strip()
        legacy = section(
            driver,
            "static int mi_sde_connector_set_legacy_emv_buffer(",
            "static bool mi_emv_uses_nova(",
        ).strip()
        if default_setter[default_setter.index("{") :] != legacy[legacy.index("{") :]:
            raise ValueError("non-Nova default setter changed")
        ordered(
            driver,
            "if (!mi_emv_uses_nova())",
            "return mi_sde_connector_set_legacy_emv_buffer(",
        )
        cc = os.environ.get("CC", "cc")
        flags = ("-std=gnu17", "-Wall", "-Wextra", "-Werror")
        config_test = root / "device.c"
        config_test.write_text(
            "#include <stdbool.h>\n"
            "#if defined(CONFIG_VIS_DISPLAY_V1) || defined(CONFIG_VIS_DISPLAY_V2_D2)\n"
            "static bool is_mi_dev_support_nova(void) { return true; }\n#endif\n"
            + section(
                driver,
                "static bool mi_emv_uses_nova(",
                "int mi_sde_connector_set_emv_buffer(",
            )
            + "int main(void) { return mi_emv_uses_nova() != EXPECTED; }\n"
        )
        for defines in (
            ("-DEXPECTED=0",),
            ("-DEXPECTED=1", "-DCONFIG_VIS_DISPLAY_V1"),
            ("-DEXPECTED=1", "-DCONFIG_VIS_DISPLAY_V2_D2"),
        ):
            run(cc, *flags, *defines, config_test, "-o", root / "device")
            run(root / "device")
        selected = section(
            driver,
            "#define MI_EMV_PACKAGE_WORDS ",
            "int mi_sde_connector_get_dc_status(",
        )
        selected += driver[driver.index("int mi_sde_connector_set_emv_buffer(") :]
        selected += "\n" + section(
            kms,
            "static bool sde_kms_emv_wait_succeeded(",
            "static void sde_kms_complete_commit(",
        )
        (root / "production-emv.c").write_text(selected)
        binary = root / "verify"
        run(
            os.environ.get("CC", "cc"),
            "-std=gnu17",
            "-pthread",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            "-g",
            "-O1",
            "-no-pie",
            "-I",
            root,
            FIXTURE,
            "-o",
            binary,
        )
        run(binary)
        print(
            f"PASS apply/reverse on {BASE} ({len(inputs)} source files) and display wiring"
        )


if __name__ == "__main__":
    main()
