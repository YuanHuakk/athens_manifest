# 构建

已有工作区的日常修改与增量编译见 [本地开发](DEVELOPMENT.md)。

以下命令在 Linux 下执行。需要 Git、repo、Git LFS、Python 3 和 Project Infinity X 构建依赖。
原厂镜像准备脚本需要 `erofs-utils`（提供 `fsck.erofs`）、`lz4` 和 `cpio`。
相机脚本另需 Android SDK Build Tools 37.0.0；编译使用源码树自带的 JDK 21。

构建主机还需常规 AOSP 依赖，包括 make、GCC/G++、Git LFS、zip/unzip、rsync、
flex、bison、bc、libssl-dev、libxml2-utils 和 zlib 开发包。Python 需 3.11 或更新版本。

将 `MANIFEST_REPO` 指向此仓库的 `infinity-x-17` 工作副本，再设置构建路径：

```bash
export MANIFEST_REPO=/path/to/athens_manifest
export TREE=/path/to/infinity-athens
export IMAGES=/path/to/athens_images_OS4.0.6.0.XPICNXM_17.0/images
export STOCK=/path/to/extracted-stock
export UAPI_CACHE=/path/to/uapi-sources-os4
export ANDROID_SDK_ROOT=/path/to/android-sdk
export RELEASE_DIR=/path/to/releases
```

## 同步源码

在空源码目录中初始化：

```bash
mkdir -p "$TREE"
cd "$TREE"
repo init --no-repo-verify --git-lfs -u "https://github.com/ProjectInfinity-X/manifest" \
  -b 17 -g default,-mips,-darwin,-notdefault
install -D -m 644 "$MANIFEST_REPO/default.xml" ".repo/local_manifests/athens.xml"
repo sync -c -j12 --no-clone-bundle
```

每次同步都会读取 Project Infinity X `17` 分支的当前清单，AOSP 版本由该清单统一选择。
本地清单同步共享的 Athens 设备树 `android-17` 分支、SM8850 公共树和小米硬件适配，并补齐 SM8850 的 Qualcomm 音频、显示、数据和 SELinux 项目。

Infinity X 使用独立的 `$TREE`，包含自己的 `.repo`、`out` 和生成的 vendor 目录。
编译前确认源码树内的设备树已包含 `infinity_athens.mk`。验证尚未发布的设备树改动时，将本地的 `AndroidProducts.mk`、`infinity_athens.mk` 和 `overlays/InfinityChargingAthens/` 同步到 `$TREE/device/xiaomi/athens/` 的对应位置。

## 应用补丁

在源码树根目录执行：

```bash
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD" --check
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD"
```

脚本按 `patches/series.json` 检查当前源码，全部检查通过后再应用补丁。
重复执行会跳过已应用的补丁。上游调整触及补丁内容时，检查会指出冲突所在的项目。

## 更新现有源码

在 `$TREE` 中执行。若同时更新 `athens_manifest`，先用上次应用时的补丁执行 `--reverse`，再更新该仓库并重新安装本地清单。

```bash
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD" --reverse &&
  repo sync -c -j12 --no-clone-bundle &&
  python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD"
```

## 提取原厂文件

先取得 athens 国行 **OS4.0.6.0.XPICNXM** [官方线刷包](https://bigota.d.miui.com/OS4.0.6.0.XPICNXM/athens_images_OS4.0.6.0.XPICNXM_20261026.0000.00_17.0_cn_8452ad1aa7.tgz) 并解压，`$IMAGES` 指向其中的
`images/`。需要 `super.img`、`boot.img`、`vendor_boot.img` 和 `dtbo.img`。
线刷包的 MD5 为 `8452ad1aa7a38e6f2fd0463704791660`。

下面从镜像生成新的 `$STOCK` 目录，无需挂载或 root 权限：

```bash
python3 "$MANIFEST_REPO/tools/prepare-stock.py" \
  --tree "$TREE" --images "$IMAGES" --output "$STOCK"
```

脚本提取 super 的 a 槽，并将 system-as-root 转成提取工具需要的目录结构。
原厂 vendor 将此版本写作 `OS4.0.6.0.XPICN`，脚本同时检查 ODM 的设备代号。
目标目录必须不存在。中途失败时，删除本次生成的不完整目录后重跑。
解包中间文件放在输出目录旁，成功或失败退出时会清除。

然后在源码目录提取专有文件并生成构建规则：

```bash
cd device/xiaomi/athens
./extract-files.py "$STOCK"
cd ../../..
```

这个入口同时处理 athens 和 sm8850-common，生成两个 `vendor/xiaomi/` 目录。

## 准备内核输入

```bash
python3 "$MANIFEST_REPO/tools/prepare-kernel.py" \
  --tree "$TREE" --images "$IMAGES" --stock "$STOCK" \
  --uapi-cache "$UAPI_CACHE" --output "$TREE/device/xiaomi/athens-kernel"
```

脚本提取原厂内核、DTB 和模块，并从 `uapi-sources.json` 中固定的公开源码生成头文件包。
首次运行需要网络下载 UAPI 源码。输出目录必须不存在；现有缓存必须匹配清单版本。
文件来源和头文件组成见 [KERNEL.md](KERNEL.md)。

## 准备小米相机

脚本适用于原厂 `6.7.000480.0`，原始 APK 的 SHA-256 为
`fc3922743a7a526d7eab5e818d769144ce789088dd2016607866cb731dea0b8e`。
`KEY` 和 `CERT` 使用与 ROM 相同的平台签名：

```bash
export KEY="$TREE/build/make/target/product/security/platform.pk8"
export CERT="$TREE/build/make/target/product/security/platform.x509.pem"
python3 "$MANIFEST_REPO/tools/prepare-miui-camera.py" \
  --tree "$PWD" \
  --stock-apk "$STOCK/product/priv-app/MiuiCamera/MiuiCamera.apk" \
  --build-tools "$ANDROID_SDK_ROOT/build-tools/37.0.0" \
  --key "$KEY" --cert "$CERT" \
  --output device/xiaomi/athens/camera/MiuiCamera.apk
```

AOSP 开发测试密钥在 `build/make/target/product/security/`。
使用自己的发布密钥时，也要配置 ROM 签名。IFAAService 会随源码编译，不用单独放 APK。

## 准备 Pixel Tips

Turbo 通过 Pixel Tips 的 provider 更新紧急温度警告状态。使用
[BP4A.260205.001 中的原签名 APK](https://github.com/gm-stuffs/google_mustang_dump/blob/12c4fb58093a30da53829e7aeb36589e3754ef9c/product/priv-app/TipsPrebuilt_v6.0.0.734377952/TipsPrebuilt_v6.0.0.734377952.apk)，
下载到仓库之外，再校验并复制到本地构建输入：

```bash
python3 "$MANIFEST_REPO/tools/prepare-pixel-tips.py" \
  --apk /path/to/TipsPrebuilt.apk \
  --output "$TREE/device/xiaomi/athens/tips/TipsPrebuilt.apk"
```

脚本固定 APK 校验值，不修改或重签名。构建将它安装到 product/priv-app；权限使用
已有的 `privapp-permissions-google-p.xml`。

## 编译

```bash
TREE="$PWD" JOBS=12 bash "$MANIFEST_REPO/tools/build.sh" nothing
TREE="$PWD" JOBS=12 bash "$MANIFEST_REPO/tools/build.sh"
```

脚本默认选择 `infinity_athens-user`，由 Infinity X 根据上游 `BUILD_ID` 决定 release 配置。无目标参数时执行 `m bacon`。
产品使用非官方构建类型并包含 GApps。SELinux 配置为 Enforcing，刷入后可用 `adb shell getenforce` 确认运行状态。
设置 `BUILD_VARIANT=userdebug` 可启用经过认证的 ADB 调试。默认使用开发测试密钥，发布签名需单独配置。

完成后导出独立副本；把下面的文件名替换为实际输出：

```bash
python3 "$MANIFEST_REPO/tools/export-candidate.py" \
  "out/target/product/athens/Project_Infinity-X-4.2-athens-DD.MM.YYYY-GAPPS-UNOFFICIAL.zip" \
  "$RELEASE_DIR" --revision r1
```

导出文件名使用包内 UTC 时间。独立副本不会随下一次构建输出一起被覆盖。

## 修改代码后

在 `athens_manifest` 仓库根目录执行：

```bash
ruff check .
ruff format --check .
python3 -m unittest discover -s tests -v
```

设备树仓库单独执行 `ruff check .` 和 `ruff format --check .`。
