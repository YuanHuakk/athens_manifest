#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare stock athens Xiaomi Camera 6.7.000480.0 for a custom ROM."""

import argparse
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

DEX_FILES = ("classes.dex", "classes4.dex", "classes5.dex", "classes6.dex")
SMALI_HELPERS = Path(__file__).parent / "miui-camera"


def run_tool(*command: str | Path, env: dict[str, str] | None = None) -> None:
    subprocess.run([str(argument) for argument in command], check=True, env=env)


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text()
    if content.count(old) != 1:
        raise ValueError(f"Expected one patch location in {path}")
    path.write_text(content.replace(old, new))


def patch_smali(work: Path) -> None:
    """Adapt the stock camera app for Athens on AOSP."""
    replace_once(
        work / "classes.dex.smali/com/android/camera/a$c.smali",
        "    const v0, 0x7f140ce3\n\n    invoke-static {v3, v0}, LF1/p4;->g(Landroid/app/Activity;I)V\n",
        "    # AOSP: omit the HyperOS-only limited-permissions dialog.\n",
    )
    replace_once(
        work / "classes4.dex.smali/Te/c.smali",
        '    const-string v3, "_global"\n\n'
        "    invoke-virtual {v0, v3}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
        "    move-result v0\n\n"
        "    sput-boolean v0, LTe/c;->m:Z",
        '    const-string v3, "_global"\n\n'
        "    invoke-virtual {v0, v3}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
        "    const/4 v0, 0x1\n\n"
        "    sput-boolean v0, LTe/c;->m:Z",
    )
    replace_once(
        work / "classes5.dex.smali/bh/f.smali",
        "    invoke-virtual {v2, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;\n\n"
        "    move-result-object v3\n",
        "    const/4 v3, 0x0\n\n"
        "    invoke-virtual {v2, v0, v3}, Landroid/content/Context;->getDir(Ljava/lang/String;I)Ljava/io/File;\n\n"
        "    move-result-object v3\n",
    )
    replace_once(
        work / "classes4.dex.smali/n9/f.smali",
        "    invoke-static {}, LFe/c;->n()Z\n\n    move-result p2\n\n    if-eqz p2, :cond_39e\n\n"
        "    sget-object p2, Ldq/a;->a:Landroid/hardware/camera2/CameraCharacteristics$Key;",
        "    # AOSP: include the HAL MIVI vendor tags, as on stock.\n\n"
        "    sget-object p2, Ldq/a;->a:Landroid/hardware/camera2/CameraCharacteristics$Key;",
    )

    # Supply MIVI per-capture metadata to the standard DNG writer.
    replace_once(
        work / "classes.dex.smali/n7/y.smali",
        "    new-instance v8, Landroid/hardware/camera2/DngCreator;\n\n"
        "    move-object/from16 v12, v35\n\n"
        "    invoke-direct {v8, v0, v12}, Landroid/hardware/camera2/DngCreator;-><init>(Landroid/hardware/camera2/CameraCharacteristics;Landroid/hardware/camera2/CaptureResult;)V",
        """    move-object/from16 v12, v35

    new-instance v8, Landroid/util/Size;
    invoke-direct {v8, v13, v14}, Landroid/util/Size;-><init>(II)V
    invoke-static {v0, v12, v8}, Lorg/pixelos/camera/RawMetadata;->forCapture(Landroid/hardware/camera2/CameraCharacteristics;Landroid/hardware/camera2/CaptureResult;Landroid/util/Size;)Landroid/hardware/camera2/CameraCharacteristics;
    move-result-object v0

    new-instance v8, Landroid/hardware/camera2/DngCreator;
    invoke-direct {v8, v0, v12}, Landroid/hardware/camera2/DngCreator;-><init>(Landroid/hardware/camera2/CameraCharacteristics;Landroid/hardware/camera2/CaptureResult;)V""",
    )
    helper = work / "classes.dex.smali/org/pixelos/camera/RawMetadata.smali"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text((SMALI_HELPERS / helper.name).read_text())

    # Arm the handoff only after starting the external Google Lens activity.
    replace_once(
        work / "classes.dex.smali/A4/f0.smali",
        "    :goto_ee\n    if-eqz v2, :cond_10f\n\n"
        "    check-cast p1, Landroidx/lifecycle/i0;",
        "    :goto_ee\n    if-eqz v2, :cond_10f\n\n"
        "    invoke-static {}, Lorg/pixelos/camera/LensCameraHandoff;->launched()V\n\n"
        "    check-cast p1, Landroidx/lifecycle/i0;",
    )
    open_camera = work / "classes6.dex.smali/ui/e.smali"
    replace_once(
        open_camera,
        ".field public final g:Z\n",
        ".field public final g:Z\n\n.field private deferredForLens:Z\n",
    )
    replace_once(
        open_camera,
        "    const/16 v0, 0xa\n\n    const/4 v1, 0x0\n",
        """    # A superseded request can already be on the camera thread when its message is removed.
    iget-boolean v0, p0, Lui/e;->deferredForLens:Z
    if-eqz v0, :continue_open
    iget-object v0, p0, Lui/c;->d:Ljava/lang/ref/WeakReference;
    invoke-virtual {v0}, Ljava/lang/ref/Reference;->get()Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Lyq/a$a;
    if-eqz v0, :discard_deferred
    invoke-virtual {v0}, Lyq/g;->a()Z
    move-result v0
    if-eqz v0, :continue_open

    :discard_deferred
    invoke-static {}, Lui/b;->a()Lui/b;
    move-result-object v0
    return-object v0

    :continue_open
    const/16 v0, 0xa

    const/4 v1, 0x0
""",
    )
    replace_once(
        open_camera,
        "    :cond_2da\n    invoke-static {}, LI6/q;->i()LI6/q;",
        """    :cond_2da
    invoke-static {}, Lui/c;->b()Lti/a$b;
    move-result-object v4
    iget-object v4, v4, Lti/a$b;->a:Landroid/hardware/camera2/CameraManager;
    invoke-static {}, Lti/c;->d()Landroid/os/Handler;
    move-result-object v5
    invoke-static {v4, v5}, Lorg/pixelos/camera/LensCameraHandoff;->shouldWait(Landroid/hardware/camera2/CameraManager;Landroid/os/Handler;)Z
    move-result v4
    if-eqz v4, :open_after_lens

    iput-boolean v3, p0, Lui/e;->deferredForLens:Z
    const-wide/16 v4, 0x32
    invoke-static {v3, p0, v4, v5}, Lti/c;->b(ILui/c;J)V
    invoke-static {}, Lui/b;->a()Lui/b;
    move-result-object v0
    return-object v0

    :open_after_lens
    invoke-static {}, LI6/q;->i()LI6/q;""",
    )
    # Keep the helper's method references out of the nearly full primary DEX.
    helper = work / "classes6.dex.smali/org/pixelos/camera/LensCameraHandoff.smali"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text((SMALI_HELPERS / helper.name).read_text())


def prepare_camera(
    tree: Path,
    stock_apk: Path,
    build_tools: Path,
    key: Path,
    cert: Path,
    output: Path,
) -> None:
    java = tree / "prebuilts/jdk/jdk21/linux-x86/bin/java"
    smali = tree / "prebuilts/extract-tools/common/smali"
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="athens-camera-") as temporary:
        work = Path(temporary)
        with zipfile.ZipFile(stock_apk) as apk:
            for name in DEX_FILES:
                (work / name).write_bytes(apk.read(name))
                run_tool(
                    java,
                    "-Xmx2g",
                    "-jar",
                    smali / "baksmali.jar",
                    "d",
                    work / name,
                    "-o",
                    work / (name + ".smali"),
                )

        patch_smali(work)
        for name in DEX_FILES:
            run_tool(
                java,
                "-Xmx2g",
                "-jar",
                smali / "smali.jar",
                "a",
                work / (name + ".smali"),
                "-o",
                work / ("patched-" + name),
            )

        unsigned = work / "unsigned.apk"
        with (
            zipfile.ZipFile(stock_apk) as original,
            zipfile.ZipFile(unsigned, "w") as apk,
        ):
            for entry in original.infolist():
                if entry.filename.startswith("META-INF/"):
                    continue
                if entry.filename in DEX_FILES:
                    data = (work / ("patched-" + entry.filename)).read_bytes()
                else:
                    data = original.read(entry.filename)
                apk.writestr(entry, data)

        aligned = work / "aligned.apk"
        run_tool(build_tools / "zipalign", "-f", "-P", "16", "4", unsigned, aligned)
        # MIUIX requires the ROM platform certificate for hidden API access.
        signing_env = dict(os.environ)
        signing_env["PATH"] = os.pathsep.join(
            (str(java.parent), signing_env.get("PATH", os.defpath))
        )
        run_tool(
            build_tools / "apksigner",
            "sign",
            "--key",
            key,
            "--cert",
            cert,
            "--out",
            output,
            aligned,
            env=signing_env,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, type=Path, help="Android source root")
    parser.add_argument("--stock-apk", required=True, type=Path)
    parser.add_argument("--build-tools", required=True, type=Path)
    parser.add_argument(
        "--key", required=True, type=Path, help="Platform signing key (.pk8)"
    )
    parser.add_argument(
        "--cert", required=True, type=Path, help="Platform certificate (.x509.pem)"
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare_camera(
        args.tree.resolve(),
        args.stock_apk.resolve(),
        args.build_tools.resolve(),
        args.key.resolve(),
        args.cert.resolve(),
        args.output.resolve(),
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
