# 构建

已有工作区的日常修改与增量编译见 [本地开发](DEVELOPMENT.md)。

以下命令在 Linux 下执行。需要 Git、repo、Git LFS、Python 3 和 PixelOS 构建依赖。
原厂镜像准备脚本需要 `erofs-utils`（提供 `fsck.erofs`）、`lz4` 和 `cpio`。
相机脚本另需 Android SDK Build Tools 37.0.0；编译使用源码树自带的 JDK 21。

构建主机还需常规 AOSP 依赖，包括 make、GCC/G++、Git LFS、zip/unzip、rsync、
flex、bison、bc、libssl-dev、libxml2-utils 和 zlib 开发包。Python 需 3.11 或更新版本。

先设置几个本地路径：

```bash
export MANIFEST_REPO=/path/to/athens_manifest
export DEVICE_REPO=/path/to/android_device_xiaomi_athens
export TREE=/path/to/pixelos
export IMAGES=/path/to/athens_images_OS3.0.306.0.WPICNXM_16.0/images
export STOCK=/path/to/extracted-stock
export UAPI_CACHE=/path/to/uapi-sources
export ANDROID_SDK_ROOT=/path/to/android-sdk
export RELEASE_DIR=/path/to/releases
```

取得构建清单和设备树：

```bash
git clone --branch pixelos-17 https://github.com/YuanHuakk/athens_manifest.git "$MANIFEST_REPO"
git clone --branch pixelos-17 https://github.com/YuanHuakk/android_device_xiaomi_athens.git "$DEVICE_REPO"
```

## 同步源码

在空源码目录中初始化：

```bash
mkdir -p "$TREE"
cd "$TREE"
repo init -u "$MANIFEST_REPO" -b pixelos-17 -m default.xml --git-lfs
repo sync -c -j12
mkdir -p device/xiaomi
git clone --no-checkout "$DEVICE_REPO" device/xiaomi/athens
DEVICE_REVISION=$(python3 - "$MANIFEST_REPO/device-tree.json" <<'PYTHON'
import json
import sys

with open(sys.argv[1]) as source:
    print(json.load(source)["revision"])
PYTHON
)
git -C device/xiaomi/athens checkout --detach "$DEVICE_REVISION"
```

设备树提交由 `device-tree.json` 固定，不跟随分支最新提交。
锁定清单已经包含 SM8850 项目。`sm8850-platform.xml` 仅供以后换基线时参考，不要重复加载。

## 应用补丁

在源码树根目录执行：

```bash
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD" --check
python3 "$MANIFEST_REPO/tools/apply-patches.py" --tree "$PWD"
```

脚本核对 `patches/series.json` 中的提交号，全部检查通过后再应用补丁。
重复执行会跳过已应用的补丁。

## 提取原厂文件

先自行取得 athens **OS3.0.306.0.WPICNXM** 线刷包并解压，`$IMAGES` 指向其中的
`images/`。需要 `super.img`、`boot.img`、`vendor_boot.img` 和 `dtbo.img`。

下面从镜像生成新的 `$STOCK` 目录，无需挂载或 root 权限：

```bash
python3 "$MANIFEST_REPO/tools/prepare-stock.py" \
  --tree "$TREE" --images "$IMAGES" --output "$STOCK"
```

脚本提取 super 的 a 槽，并将 system-as-root 转成提取工具需要的目录结构。
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

脚本适用于原厂 6.3.008710.8。`KEY` 和 `CERT` 使用与 ROM 相同的平台签名：

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

## 编译

```bash
TREE="$PWD" JOBS=12 bash "$MANIFEST_REPO/tools/build.sh" pixelos
```

完成后导出独立副本；把下面的文件名替换为实际输出：

```bash
python3 "$MANIFEST_REPO/tools/export-candidate.py" \
  out/target/product/athens/PixelOS_athens-17.0-YYYYMMDD-HHMM.zip \
  "$RELEASE_DIR" --revision r13
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
