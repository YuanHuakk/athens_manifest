# Athens 内核

Infinity X 使用国行 `OS4.0.6.0.XPICNXM` 线刷包的内核和模块。原厂 Android 17 搭配 Android 16 GKI，版本为 `6.12.69-android16-6-g0a1dc0413ec7-ab16271006-4k`。设备树使用 2026-10-01 的 boot 和 vendor 安全补丁日期，启动链回滚下限为 `1790812800`。

## 准备构建输入

运行构建指南中的[内核准备命令](BUILD.md#准备内核输入)。脚本核对内核版本、拆出 12 个有序 DTB，并将原厂模块和加载清单写入新的 `device/xiaomi/athens-kernel/`。[准备脚本](../tools/prepare-kernel.py)

`kernel-headers.tar.gz` 的归档根为 `usr/include/`，合并顺序为 GKI 通用 UAPI、ARM64 UAPI、QTI UAPI。HAL 使用 Bionic 的通用头及单独清洗的 `athens_qti_kernel_headers`。迁移构建输入时一并复制 `Android.bp` 和 `qti-include/`。已有内核目录可在准备命令中加 `--qti-headers-only` 更新这两项。[固定的 GKI 和 QTI 源码版本](../uapi-sources.json)

| 406 构建输入 | SHA-256 |
| --- | --- |
| `kernel`（与 AOSP 构建 `16271006` 的 ARM64 4 KiB `Image` 一致） | `2bdda2f4c4365b40f1ca7422d0bb9b8adb587c46f5a4f87bcbff00b82c300e9d` |
| `vendor_ramdisk/msm_drm.ko` 和 `vendor_dlkm/msm_drm.ko` | `d375791cdcf563962b627e3a6c5849c3423f9ccc66aea8b44d42dccfa7f7f197` |

## 原神插帧与显示驱动

**原神单独插帧的 60→120 FPS 尚未通过实机验收。** 游戏面板和 Scene 仍显示约 60 FPS。DSI 整批写入、HAL 配置倍率和面板扫描频率分别反映传输、配置和刷新。验证每秒 120 个不同画面需要在独显输出端逐帧观测。

ROM 保留 MiVK 和 SurfaceFlinger 的动矢修复，使用 406 原厂 `msm_drm.ko`。可从 `/sys/module/msm_drm/notes/.note.gnu.build-id` 核对已加载模块的 Build ID `f852df29151bc376aca0ff9ff6f707d7ba1c3d56`。原厂驱动在发送前共用一份动矢缓冲区，后一帧可能覆盖前一帧。修复在原神使用 120 Hz 并完成画面配对时，给上一帧的显示信号预留最多 2 ms。修复后的 81 秒实战采样中未观察到覆盖。

仓库另存按 DRM 提交绑定动矢的内核补丁。主机回归使用 MiCode 显示仓库的固定提交 `1f1cd9c1b674014ae6ca324ffea12c96e121d6e1`，在临时目录应用补丁并编译测试。[内核补丁](../patches/kernel/0001-msm-bind-nova-emv-to-display-commit.patch) · [回归脚本](../patches/kernel/verify-emv-commit.py)

```bash
# DISPLAY_SRC 指向含上述提交的 MiCode 显示驱动 Git 检出
python3 "$MANIFEST_REPO/patches/kernel/verify-emv-commit.py" "$DISPLAY_SRC"
```

构建可上机的模块还缺 406 完整的 Athens Kleaf 配置和 Novatek D2 实现，或厂商提供的可重链接对象及头文件。官方 GKI 构建提供相同的内核及其符号版本。补齐厂商输入后，须核对 406 的模块依赖和符号 CRC，同时更新上表两份驱动并重建对应镜像。原厂 `vendor_dlkm/etc/NOTICE_GPL.html.gz` 列出的源码索取邮箱为 `oss-request@xiaomi.com`。[AOSP 构建产物](https://ci.android.com/builds/submitted/16271006/kernel_aarch64/latest) · [Athens Kleaf 配置](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/da9af1b6d83e1f53e4b8e4f4421e3c4161d2133d/kleaf-scripts/targets/athens.bzl#L4) · [Novatek 编译输入](https://github.com/MiCode/vendor_opensource_display-drivers/blob/1f1cd9c1b674014ae6ca324ffea12c96e121d6e1/msm/Kbuild#L393)
