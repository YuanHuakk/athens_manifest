#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare the 406 Athens MiVK display contract with unpacked target-files."""

import argparse
import hashlib
import json
import os
import re
import runpy
import struct
import subprocess
import tempfile
from pathlib import Path

STOCK_VERSION = "OS4.0.6.0.XPICN"
STOCK_APK = "product/pangu/system/app/Joyose/Joyose.apk"
STOCK_DEFAULTS = "odm/etc/default_cloud.json"
TARGET_FILES = (
    "out/target/product/athens/obj/PACKAGING/target_files_intermediates/"
    "infinity_athens-target_files"
)
TOOL_DIR = "prebuilts/clang/host/linux-x86/llvm-binutils-stable"
MV_SIZE = "ro.vendor.display.dualDPU_EMVSize"
MV_SCALE = "vendor.display.default_resolution"
CORE_LIBRARIES = (
    "libgui.so",
    "libui.so",
    "libnativewindow.so",
    "libbinder.so",
    "libvulkan.so",
    "libEGL.so",
)
OEM_LIBRARIES = (
    "libmivk.so",
    "libmigl.so",
    "libanf.so",
    "libmisuperframe.so",
    "libmisurfaceflinger.so",
    "libfcmintf.so",
)
FRAME_CAPTURE_AIDL = "vendor.xiaomi.hardware.framecapturemanager-V1-ndk.so"
FRAME_CAPTURE_MANIFEST = (
    "odm/etc/vintf/manifest/vendor.xiaomi.hardware.framecapturemanager_aidl-service.xml"
)
MIVK_ELF_SHA256 = "25be6589f9089c3184aeaed4d3190051769d0147f2d437257e2ece5b96bee565"
MI_SURFACEFLINGER_SHA256 = (
    "db15fb9d84183cca85f9b2ee24695ec83c2d5301bbe8c2d5eabd74741cedb8a0"
)
ATHENS_PRODUCER_ABI = {
    "build_id": "8e3b5f7449f5d59f92cd02c537a4f3c0",
    "byte_size": "0x0ff0",
    "mProducer_offset": "0x0be0",
}
# The verified 406 ELF maps these text addresses at the same file offsets.
BLAST_INSTRUCTIONS = (
    (0x66EC3C, 0x52825600, 0x5281FE00, "BLAST allocation size"),
    (0x66ECEC, 0xF946A508, 0xF945F108, "BLAST producer member load"),
    (0x66EE2C, 0x52825601, 0x5281FE01, "BLAST constructor exception cleanup size"),
)
LOADER_STRINGS = {
    "libvulkan.so": (
        "/system_ext/lib64/libmivk.so",
        "MiVkGetInstanceProcAddr",
        "MiVkGetDeviceProcAddr",
    ),
    "libEGL.so": ("/system_ext/lib64/libmigl.so",),
}
STOCK_MODULES = {"afme", "mifi", "mimv", "misr"}
GPU_MODES = ("POWERSAVE", "BALANCE", "STANDARD", "HIGH_QUALITY", "CUSTOMIZE")
INSTRUCTION_SITES = {
    "default_enable": (0x48ECA4, 0x48ECC0),
    "joyose_transaction_30": (0x48FBC0, 0x48FBE4),
    "joyose_configs_member": (0x4903A8, 0x4903B8),
    "callback_name_suffix": (0x48B0AC, 0x48B0D4),
    "callback_binder_argument": (0x48B104, 0x48B114),
    "joyose_transaction_35": (0x48B154, 0x48B16C),
    "callback_transaction_1": (0x320898, 0x3208CC),
    "callback_store_mifisr_state": (0x48CA48, 0x48CA68),
    "enable_after_processor_config": (0x490658, 0x490680),
    "enable_flag_read": (0x49B7BC, 0x49B7C8),
    "blast_allocation": (0x66EC3C, 0x66EC44),
    "blast_producer_member_load": (0x66ECE4, 0x66ECF4),
    "blast_exception_cleanup": (0x66EE28, 0x66EE38),
    "genshin_motion_vector_submission": (0x704110, 0x70414C),
}
SYMBOLS_OF_INTEREST = {
    "libmivk.so": (
        "MiVkGetInstanceProcAddr ",
        "MiVkGetDeviceProcAddr ",
        "android::MotionVectorSurface::init(",
        "android::MotionVectorSurface::setUpProducer(",
        "android::MotionVectorSurface::queueGraphicBuffer(",
        "MiVkAppInfoMonitor::ParseVkMiFISRSwitch(",
        "com::xiaomi::joyose::BnGameInfoUpdate::onTransact(",
    ),
    "libmigl.so": ("android::MotionVectorSurface::queueGraphicBuffer(",),
    "libmisurfaceflinger.so": (
        "android::FrameCaptureManagerIntf::createConnection(",
        "android::FrameCaptureManagerIntf::NotifyFrameCaptureIntf(",
    ),
    "libfcmintf.so": (
        "android::FrameCaptureManagerIntf::createConnection(",
        "android::FrameCaptureManagerIntf::NotifyFrameCaptureIntf(",
    ),
}


def properties(path):
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )


def target_path(root, relative):
    partition, path = relative.split("/", 1)
    return root / partition.upper() / path


def run_tool(tools, name, *args):
    return subprocess.check_output(
        [str(tools / name), *map(str, args)], text=True, errors="replace"
    )


def novatek_emv_packages(rows):
    packages = []
    for row in rows:
        package, fi, _sr, _fisr = row.split("_")
        for variant in fi.split("|"):
            fields = variant.split("#")[2].split(",")
            if len(fields) == 17 and fields[15] == "1":
                packages.append(package)
                break
    return sorted(packages)


def stock_display_defaults(tree, stock):
    extractor = runpy.run_path(
        str(tree / "device/xiaomi/athens/joyose/extract_profiles.py")
    )
    apk = extractor["verified_input"](stock / STOCK_APK, extractor["JOYOSE_SHA256"])
    defaults = extractor["verified_input"](
        stock / STOCK_DEFAULTS, extractor["DEFAULTS_SHA256"]
    )
    document = extractor["decrypt_defaults"](defaults, apk)
    game_booster = document["booster_config"]["params"]["game_booster"]
    paths = {
        STOCK_APK: hashlib.sha256(apk).hexdigest(),
        STOCK_DEFAULTS: hashlib.sha256(defaults).hexdigest(),
    }
    render_defaults = {}
    for config, name_key, rows_key, process_key in (
        ("mivk_settings", "app", "app_params", "app_cmdlines"),
        ("migl_settings", "game", "game_params", "game_cmdlines"),
    ):
        settings = game_booster[config]
        rows = {}
        for row in settings[rows_key]:
            name = row[name_key]
            if name not in {"yuanshen", "hkrpg"}:
                continue
            xrender = row["xrender_config"]
            modules = {
                key: int(value)
                for key, value in (
                    entry.split(":", 1) for entry in xrender["support_module"]
                )
            }
            rows[name] = {
                "process_names": row[process_key],
                "render_thread_condition": xrender["checkMainInfo"],
                "modules": {
                    key: value for key, value in modules.items() if key in STOCK_MODULES
                },
            }
            if config == "mivk_settings":
                mi_mv_mask = modules["mimv"]
                rows[name]["mimv_index_in_support_module"] = list(modules).index("mimv")
                rows[name]["mimv_gpu_modes"] = [
                    mode
                    for index, mode in enumerate(GPU_MODES)
                    if mi_mv_mask & (1 << index)
                ]
        render_defaults[config] = {"enabled": settings["enable"], "profiles": rows}
    render_defaults["mivk_settings"]["use_gpu_tuner_selection"] = game_booster[
        "key_mivk_gputuner_select_enable"
    ]

    # Keep the chip profile package list separate from the graphics process names.
    selected = extractor["display_profiles"](document)["novatek_game_params"]
    return {
        "input_sha256": paths,
        "render_defaults": render_defaults,
        "novatek_emv_fi_packages": novatek_emv_packages(selected),
    }


def dynamic_symbols(tools, path, kind):
    if not path.is_file():
        return set()
    symbols = run_tool(tools, "llvm-nm", "--dynamic", "--format=posix", kind, path)
    # Count name coverage. A definition with @@ is the default symbol version.
    return {line.split()[0].replace("@@", "@") for line in symbols.splitlines() if line}


def loader_offsets(path, markers):
    if not path.is_file():
        return None
    contents = path.read_bytes()
    offsets = {}
    for marker in markers:
        position = contents.find(marker.encode() + b"\0")
        offsets[marker] = hex(position) if position >= 0 else None
    return offsets


def oem_libraries(tools, stock, target):
    results = {}
    for name in OEM_LIBRARIES:
        relative = f"system_ext/lib64/{name}"
        stock_elf = stock / relative
        target_elf = target_path(target, relative)
        headers = run_tool(tools, "llvm-readelf", "--dynamic", stock_elf)
        results[relative] = {
            "stock_sha256": hashlib.sha256(stock_elf.read_bytes()).hexdigest(),
            "stock_needed": re.findall(r"\(NEEDED\).*?\[([^]]+)]", headers),
            "target_path_present": target_elf.is_file(),
        }
        if target_elf.is_file():
            results[relative]["target_sha256"] = hashlib.sha256(
                target_elf.read_bytes()
            ).hexdigest()
        if name in SYMBOLS_OF_INTEREST:
            symbols = run_tool(tools, "llvm-nm", "--dynamic", "--demangle", stock_elf)
            results[relative]["stock_dynamic_symbols"] = [
                line.strip()
                for line in symbols.splitlines()
                if any(symbol in line for symbol in SYMBOLS_OF_INTEREST[name])
            ]
    return results


def linker_evidence(tools, stock, target):
    stock_core = set().union(
        *(
            dynamic_symbols(tools, stock / f"system/lib64/{name}", "--defined-only")
            for name in CORE_LIBRARIES
        )
    )
    target_core = set().union(
        *(
            dynamic_symbols(tools, target / f"SYSTEM/lib64/{name}", "--defined-only")
            for name in CORE_LIBRARIES
        )
    )
    result = {}
    for name in ("libmivk.so", "libmigl.so"):
        imports = dynamic_symbols(
            tools, stock / f"system_ext/lib64/{name}", "--undefined-only"
        )
        stock_core_imports = imports & stock_core
        result[name] = {
            "stock_import_count": len(imports),
            "imports_in_stock_core": len(stock_core_imports),
            "stock_core_imports_missing_in_target_core": sorted(
                stock_core_imports - target_core
            ),
        }
    return {"compared_lib64": CORE_LIBRARIES, "oem_imports": result}


def stock_mivk_instruction_evidence(tools, mivk):
    if hashlib.sha256(mivk.read_bytes()).hexdigest() != MIVK_ELF_SHA256:
        raise ValueError(f"Unexpected 406 stock MiVK instruction fixture: {mivk}")
    result = {}
    for name, (start, stop) in INSTRUCTION_SITES.items():
        disassembly = run_tool(
            tools,
            "llvm-objdump",
            "-d",
            "-C",
            "--no-show-raw-insn",
            f"--start-address={start:#x}",
            f"--stop-address={stop:#x}",
            mivk,
        )
        result[name] = [
            line.strip()
            for line in disassembly.splitlines()
            if re.match(r"\s+[0-9a-f]+:", line)
        ]
    result["string_file_offsets"] = loader_offsets(
        mivk,
        (
            "xiaomi.joyose",
            "com.xiaomi.joyose.IJoyoseInterface",
            "/proc/%d/cmdline",
            "_mivk",
            "configs",
            "mifisr_type",
            "/data/system/mcd/emv_status",
        ),
    )
    return result


def stock_motion_vector_packet(mi_surfaceflinger):
    contents = mi_surfaceflinger.read_bytes()
    if hashlib.sha256(contents).hexdigest() != MI_SURFACEFLINGER_SHA256:
        raise ValueError(
            f"Unexpected 406 stock SurfaceFlinger fixture: {mi_surfaceflinger}"
        )

    # DualDPUgetMVInfo copies 11 constants and appends three values before the sample grid.
    header = (*struct.unpack_from("<11f", contents, 0x2F1DC), 4121, 20482, 1620)
    footer = struct.unpack_from("<4f", contents, 0x237D0)
    return {
        "scale_property": MV_SCALE,
        "packet_length_floats": 1644,
        "header": header,
        "sample_grid": {
            "width": 60,
            "height": 27,
            "storage_index": "14 + x * 27 + y",
            "source_coordinates": "(x * ceil(width / 60), y * ceil(height / 27)) using buffer stride",
            "formats": {"RGBA_1010102": "R/G / 1023", "RGBA_8888": "R/G / 255"},
            "center_bias": struct.unpack("<f", bytes.fromhex("ff fe fe be"))[0],
            "horizontal": "trunc(-sign(r) * (2*r)^2 * scale_width)",
            "vertical": "trunc(sign(g) * (2*g)^2 * scale_height)",
            "packing": "float(abs(Y) + (abs(X) << 12) + (Y > 0 ? 0x200 : 0) "
            "+ (X > 0 ? 0x400000 : 0))",
        },
        "footer_index": 1634,
        "footer": footer,
        "initial_fill": 40000.0,
        "unchanged_tail_range": [1638, 1644],
        "evidence_addresses": {
            "read_scaling_property": "0x4b824",
            "initialize_packet": "0x61f0c",
            "copy_header": "0x69ecc",
            "pack_sample": "0x6a0a8",
            "copy_footer": "0x6a1a8",
            "send_to_hwc": "0x69b94",
        },
    }


def stock_joyose_contract():
    # This contract comes from the verified APK and ELF, not a recorded live response.
    return {
        "service": "xiaomi.joyose",
        "descriptor": "com.xiaomi.joyose.IJoyoseInterface",
        "query": {
            "transaction": 30,
            "request": "String16 process name",
            "response": "Exception status followed by nullable String16 JSON with configs object",
            "known_configs_fields": {
                "remode": "int selected using the process name and calling UID",
                "xrender_BaseInfo": "int mask of indexes in the original support_module list",
                "xrender_ModuleList": "comma-separated names of selected modules when nonempty",
                "xrender_CheckMainInfo": "configured string when present and mask is nonzero",
                "xrender_PayloadData": "optional profile payloadData when present and mask is nonzero",
                "xrender_CheckEXT": "optional profile checkEXT when present and mask is nonzero",
            },
            "notes": "JoyoseManagerNative.queryVKSettingsByAppName passes the calling UID to "
            "utils.z.a. That method checks the active feature flag and exact process "
            "name, then recomputes remode and the configs object. s0.r.R0 computes "
            "the xrender fields using the active GPU mode. Native code also reads "
            "mifisr_type when present. No live or complete reply is asserted.",
        },
        "registration": {
            "transaction": 35,
            "request": [
                "String16 process name with _mivk suffix",
                "strong callback Binder",
            ],
            "native_flags": 0,
            "java_proxy_flags": 1,
            "evidence": "MiVkAppInfoMonitor::EventProcess and IJoyoseInterface.Stub dispatch",
        },
        "callback": {
            "descriptor": "com.xiaomi.joyose.IGameInfoUpdate",
            "transaction": 1,
            "method": "sendToMiGL",
            "known_message": "String16 11 <package> <0|1>",
            "meaning": "MiFISR disable/enable status. The native parser checks the package "
            "before storing the value. This message alone proves no rendered frame.",
            "evidence": "IGameInfoUpdate and Joyose t0.s.Z, MiVkAppInfoMonitor::ParseVkMiFISRSwitch",
        },
    }


def matching_libgui_layout(tools, tree, target):
    symbols = tree / "out/target/product/athens/symbols/system/lib64/libgui.so"
    packaged = target / "SYSTEM/lib64/libgui.so"
    if not symbols.is_file() or not packaged.is_file():
        return None
    build_ids = [
        re.search(r"Build ID: ([a-f0-9]+)", run_tool(tools, "llvm-readelf", "-n", p))
        for p in (symbols, packaged)
    ]
    if not all(build_ids) or build_ids[0][1] != build_ids[1][1]:
        return None

    layout = run_tool(
        tools, "llvm-dwarfdump", "--name=BLASTBufferQueue", "--show-children", symbols
    )
    entries = re.split(r"(?m)^0x[0-9a-f]+:\s+", layout)
    size = next(
        (
            match[1]
            for entry in entries
            if entry.startswith("DW_TAG_class_type") and '"BLASTBufferQueue"' in entry
            if (match := re.search(r"DW_AT_byte_size\s+\((0x[0-9a-f]+)\)", entry))
        ),
        None,
    )
    offset = next(
        (
            match[1]
            for entry in entries
            if entry.startswith("DW_TAG_member") and '"mProducer"' in entry
            if (
                match := re.search(
                    r"DW_AT_data_member_location\s+\((0x[0-9a-f]+)\)", entry
                )
            )
        ),
        None,
    )
    if size is None or offset is None:
        return None
    return {"build_id": build_ids[0][1], "byte_size": size, "mProducer_offset": offset}


def prepare_producer_candidate(stock_mivk, target_layout, output):
    if target_layout != ATHENS_PRODUCER_ABI:
        raise ValueError(
            "The target libgui does not match the audited MiVK producer ABI"
        )
    contents = bytearray(stock_mivk.read_bytes())
    if hashlib.sha256(contents).hexdigest() != MIVK_ELF_SHA256:
        raise ValueError("The MiVK input does not match the audited 406 ELF")

    for offset, original, replacement, description in BLAST_INSTRUCTIONS:
        if struct.unpack_from("<I", contents, offset)[0] != original:
            raise ValueError(f"Unexpected {description} instruction at {offset:#x}")
        struct.pack_into("<I", contents, offset, replacement)

    # Publish only a complete candidate, without replacing an existing file.
    with tempfile.NamedTemporaryFile(dir=output.parent) as temporary:
        temporary.write(contents)
        temporary.flush()
        os.link(temporary.name, output)

    return {
        "path": str(output),
        "sha256": hashlib.sha256(contents).hexdigest(),
        "target_libgui_build_id": target_layout["build_id"],
        "changed_instructions": {
            hex(offset): description for offset, _, _, description in BLAST_INSTRUCTIONS
        },
        "scope": "BLAST layout adaptation for offline integration. No renderer or HWC test.",
    }


def audit(tree, stock, target):
    tools = tree / TOOL_DIR
    stock_odm = properties(stock / "odm/etc/build.prop")
    stock_vendor = properties(stock / "vendor/build.prop")
    target_system = properties(target / "SYSTEM/build.prop")
    target_odm = properties(target / "ODM/etc/build.prop")
    if (
        stock_odm.get("ro.product.odm.device") != "athens"
        or stock_vendor.get("ro.vendor.build.version.incremental") != STOCK_VERSION
    ):
        raise ValueError(f"Expected extracted Athens {STOCK_VERSION} under {stock}")
    if target_system.get("ro.product.system.device") != "athens":
        raise ValueError(f"Expected unpacked Athens target-files under {target}")
    loaders = {}
    for name, markers in LOADER_STRINGS.items():
        relative = f"system/lib64/{name}"
        loaders[relative] = {
            "stock": loader_offsets(stock / relative, markers),
            "target": loader_offsets(target_path(target, relative), markers),
        }
    frame_capture = {}
    for relative in (
        FRAME_CAPTURE_MANIFEST,
        "odm/lib64/libframecapturemanager.so",
        f"odm/lib64/{FRAME_CAPTURE_AIDL}",
        f"system_ext/lib64/{FRAME_CAPTURE_AIDL}",
    ):
        frame_capture[relative] = {
            "stock": (stock / relative).is_file(),
            "target": target_path(target, relative).is_file(),
        }
    return {
        "stock": {
            "path": str(stock),
            "version": STOCK_VERSION,
            "odm_properties": {key: stock_odm.get(key) for key in (MV_SIZE, MV_SCALE)},
        },
        "target": {
            "path": str(target),
            "system_incremental": target_system.get(
                "ro.system.build.version.incremental"
            ),
            "odm_properties": {key: target_odm.get(key) for key in (MV_SIZE, MV_SCALE)},
        },
        "stock_display_defaults": stock_display_defaults(tree, stock),
        "stock_joyose_contract": stock_joyose_contract(),
        "loader_string_file_offsets": loaders,
        "oem_libraries": oem_libraries(tools, stock, target),
        "separate_frame_capture_files": frame_capture,
        "core_dynamic_symbol_comparison": linker_evidence(tools, stock, target),
        "blast_buffer_queue_abi": {
            "stock_mivk_producer_read_offset": "0xd48",
            "target_libgui_layout": matching_libgui_layout(tools, tree, target),
        },
        "stock_mivk_disassembly": stock_mivk_instruction_evidence(
            tools, stock / "system_ext/lib64/libmivk.so"
        ),
        "stock_motion_vector_packet": stock_motion_vector_packet(
            stock / "system_ext/lib64/libmisurfaceflinger.so"
        ),
        "scope": "Static arm64 fixture comparison. Symbol name/version coverage does not "
        "verify linker namespace access, C++ ABI, Binder operation or rendered frames.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, type=Path, help="Android source tree")
    parser.add_argument(
        "--stock", required=True, type=Path, help="Extracted stock 406 root"
    )
    parser.add_argument(
        "--target-files", type=Path, help="Unpacked target-files directory"
    )
    parser.add_argument(
        "--producer-candidate",
        type=Path,
        help="Create a BLAST-ABI MiVK integration candidate at a new path",
    )
    args = parser.parse_args()
    tree = args.tree.resolve()
    target = (args.target_files or tree / TARGET_FILES).resolve()
    try:
        stock = args.stock.resolve()
        result = audit(tree, stock, target)
        if args.producer_candidate is not None:
            result["producer_candidate"] = prepare_producer_candidate(
                stock / "system_ext/lib64/libmivk.so",
                result["blast_buffer_queue_abi"]["target_libgui_layout"],
                args.producer_candidate.absolute(),
            )
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
