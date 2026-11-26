# 构建 Infinity X

以下命令在同一个 Bash 会话中执行，用国行 HyperOS 406 准备 Redmi K100 Pro（`athens`）的 Android 17 全量包。已有工作区的日常修改见[本地开发](DEVELOPMENT.md)。

## 输入和路径

构建主机使用 64 位 Linux。安装 `repo`、Git、Git LFS、Python 3.11 或更新版本，以及 AOSP 构建依赖（make、GCC/G++、flex、bison、bc、zip/unzip、rsync、libssl-dev、libxml2-utils、zlib 开发包）。原厂文件提取需要 `erofs-utils`、`lz4`、`cpio` 和 Python 包 `cryptography`。相机签名需要 Android SDK Build Tools 37.0.0。JDK 21 随源码同步。

另备两个文件，下载后在下面填入绝对路径。

- 国行 `OS4.0.6.0.XPICNXM` 线刷包。后续命令校验归档并只解出构建用到的四个镜像。[小米下载](https://cdnorg.d.miui.com/OS4.0.6.0.XPICNXM/athens_images_OS4.0.6.0.XPICNXM_20261026.0000.00_17.0_cn_8452ad1aa7.tgz)
- Pixel Tips `6.0.0.734377952` 原签名 APK，供 Turbo 更新紧急温度提醒。[固定版本下载](https://raw.githubusercontent.com/gm-stuffs/google_mustang_dump/12c4fb58093a30da53829e7aeb36589e3754ef9c/product/priv-app/TipsPrebuilt_v6.0.0.734377952/TipsPrebuilt_v6.0.0.734377952.apk)

从空的工作目录开始。已有清单副本时，将 `MANIFEST_REPO` 指向该副本即可。

```bash
git clone --branch infinity-x-17 --single-branch https://github.com/YuanHuakk/athens_manifest.git
export MANIFEST_REPO="$PWD/athens_manifest"
export TREE="$PWD/infinity-athens" IMAGES="$PWD/images-406" STOCK="$PWD/stock-406"
export UAPI_CACHE="$PWD/uapi-cache" RELEASE_DIR="$PWD/releases"
export FASTBOOT_TGZ=/path/to/athens-406.tgz
export PIXEL_TIPS_APK=/path/to/TipsPrebuilt.apk
export ANDROID_SDK_ROOT=/path/to/android-sdk
```

## 同步源码并应用补丁

```bash
mkdir -p "$TREE"
cd "$TREE"
repo init --no-repo-verify --git-lfs -u https://github.com/ProjectInfinity-X/manifest \
  -b 17 -g default,-mips,-darwin,-notdefault
install -Dm644 "$MANIFEST_REPO/default.xml" .repo/local_manifests/athens.xml
repo sync -c -j12 --no-clone-bundle
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$TREE"
```

`repo sync` 跟随 Infinity X `17` 和共享设备树 `android-17`。补丁脚本先检查 `patches/series.json` 中的所有项目，再应用改动。单独检查可加 `--check`。

## 提取原厂文件

```bash
printf '%s  %s\n' 8452ad1aa7a38e6f2fd0463704791660 "$FASTBOOT_TGZ" | md5sum -c - &&
  mkdir -p "$IMAGES" &&
  tar -xf "$FASTBOOT_TGZ" -C "$IMAGES" --strip-components=2 \
    athens_images_OS4.0.6.0.XPICNXM_17.0/images/{super,boot,vendor_boot,dtbo}.img &&
  python3 "$MANIFEST_REPO/tools/prepare-stock.py" --tree "$TREE" --images "$IMAGES" --output "$STOCK"
```

已有解压好的线刷包时，可直接将 `IMAGES` 指向其 `images/`，从 `prepare-stock.py` 开始。`STOCK` 应指向尚未创建的目录。脚本提取 A 槽并检查设备代号和 vendor 版本。

## 准备内核输入

```bash
python3 "$MANIFEST_REPO/tools/prepare-kernel.py" --tree "$TREE" --images "$IMAGES" \
  --stock "$STOCK" --uapi-cache "$UAPI_CACHE" --output "$TREE/device/xiaomi/athens-kernel"
```

首次运行会下载 `uapi-sources.json` 固定的头文件源码，之后可复用缓存。完整准备要求 `athens-kernel` 目录尚未创建。内核、模块及显示驱动的来源见[内核输入](KERNEL.md)。

## 准备 vendor、Pixel Tips 和小米相机

```bash
(cd "$TREE/device/xiaomi/athens" && ./extract-files.py "$STOCK")
python3 "$MANIFEST_REPO/tools/prepare-pixel-tips.py" --apk "$PIXEL_TIPS_APK" \
  --output "$TREE/device/xiaomi/athens/tips/TipsPrebuilt.apk"

camera="$STOCK/product/priv-app/MiuiCamera/MiuiCamera.apk"
platform="$TREE/build/make/target/product/security/platform"
printf '%s  %s\n' fc3922743a7a526d7eab5e818d769144ce789088dd2016607866cb731dea0b8e "$camera" | sha256sum -c - &&
  python3 "$MANIFEST_REPO/tools/prepare-miui-camera.py" --tree "$TREE" --stock-apk "$camera" \
    --build-tools "$ANDROID_SDK_ROOT/build-tools/37.0.0" \
    --key "${KEY:-${platform}.pk8}" --cert "${CERT:-${platform}.x509.pem}" \
    --output "$TREE/device/xiaomi/athens/camera/MiuiCamera.apk"
```

一次提取会生成 `vendor/xiaomi/athens`、`vendor/xiaomi/sm8850-common`，同时导入 406 计算器并从 Joyose 生成游戏显示配置。Pixel Tips 脚本校验 APK 摘要。小米相机使用 406 的 `6.7.000480.0` 并以 ROM 平台证书签名。上例使用源码自带的开发密钥，使用发布密钥时将 `KEY` 和 `CERT` 指向相同 ROM 的平台密钥与证书。

## 编译与导出

默认配置为 `infinity_athens-user`，包含 GApps 和 406 QTI aptX Adaptive。诊断蓝牙时可在编译前通过 `export ATHENS_APTX_ADAPTIVE_TEST_BUILD=false` 关闭 Adaptive。

| 可选构建配置 | Bash 设置 | 依赖与范围 |
| --- | --- | --- |
| MiVK 动矢实验 | `export ATHENS_MIVK_TEST_BUILD=true` | 保留 Vulkan 动矢接入代码，使用提取的 `libanf`、`libmisuperframe`、`libmivk` 和 Joyose 配置。原神 60 FPS 输入时，尚未确认面板每秒输出 120 个不同画面。 |

```bash
JOBS=12 "$MANIFEST_REPO/tools/build.sh" nothing
JOBS=12 "$MANIFEST_REPO/tools/build.sh"
```

`nothing` 检查构建图，无目标参数时执行 `m bacon`。调试版可在编译前设置 `export BUILD_VARIANT=userdebug`。全量 ZIP 位于 `$TREE/out/target/product/athens/`。需要保留独立副本时可按包内 UTC 时间导出。若目录里有多个版本，将通配符换成本次 ZIP 的完整名称。

```bash
python3 "$MANIFEST_REPO/tools/export-candidate.py" \
  "$TREE"/out/target/product/athens/Project_Infinity-X-*-athens-*-GAPPS-UNOFFICIAL.zip \
  "$RELEASE_DIR" --revision r1
```

## 更新现有源码

先保存开发中的改动。用上次应用的清单撤回旧补丁，再更新清单、同步上游和重新应用补丁。

```bash
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$TREE" --reverse &&
  git -C "$MANIFEST_REPO" pull --ff-only &&
  install -Dm644 "$MANIFEST_REPO/default.xml" "$TREE/.repo/local_manifests/athens.xml" &&
  (cd "$TREE" && repo sync -c -j12 --no-clone-bundle) &&
  python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$TREE"
```
