# 内核输入

当前使用原厂内核 `6.12.69-android16-6-g0a1dc0413ec7-ab16271006-4k`，
来自 athens `OS4.0.6.0.XPICNXM`。原厂系统基于 Android 17，boot 镜像仍使用 Android 16 的 GKI。

共享设备树 `android-17` 将 boot 和 vendor 的安全补丁日期设为 2026-10-01，
并将启动链回滚下限设为 `1790812800`。设备树中的 `pvmfw` 和 `countrycode` 哈希描述符
取自同一线刷包的顶层 `vbmeta.img`，已分别对相应分区内容重算并核对哈希。

将本地内核包放在 `device/xiaomi/athens-kernel`，目录如下：

| 路径                              | 来源                                       |
| --------------------------------- | ------------------------------------------ |
| `kernel`                          | boot.img 的 kernel 段                      |
| `dtbo.img`                        | 原厂 dtbo.img                              |
| `dtb/raw01.dtb` … `dtb/raw12.dtb` | vendor_boot.img 的串联 FDT，按原始顺序拆分 |
| `vendor_ramdisk/`                 | vendor_boot ramdisk 中的 lib/modules       |
| `vendor_dlkm/`                    | vendor_dlkm 镜像中的 lib/modules           |
| `system_dlkm/`                    | system_dlkm 中该内核版本的模块目录内容     |
| `system_dlkm_flatten/`            | system_dlkm 的 flatten/lib/modules         |
| `kernel-headers.tar.gz`           | UAPI 头，归档根为 usr/include              |
| `Android.bp`、`qti-include/`      | Soong 头库及供用户态使用的 QTI 扩展头      |

`tools/prepare-kernel.py` 完成以上目录的生成。它调用源码树中的 `unpack_bootimg.py`，
按 FDT 的 totalsize 顺序拆分 DTB，用 lz4 / cpio 提取 vendor ramdisk 的模块。
模块加载清单和相对符号链接保持原样。

## UAPI 来源

`uapi-sources.json` 固定两个公开源码提交：

- GKI `android16-6.12`：`0a1dc0413ec7f42ad5924505ca2a519900ccf770`
- QTI SM8850：`abdf3a50f1f9eb8ebace76e4e1a8e16c2e089a63`

生成顺序为 GKI `include/uapi`、GKI ARM64 `asm`、QTI `include/uapi`；QTI 同名文件覆盖
GKI。去除 Kbuild / Makefile，再加入与 r12 一致的 Makefile，生成以 `usr/include/` 为根的
压缩包。归档时间和文件顺序固定，不依赖下载时间。

头文件由上述源码组合生成，未经 `make headers_install` 导出。IPA 头文件由
`hardware/qcom-caf/sm8850/dataipa` 单独提供。

编译 HAL 时，通用 Linux 接口使用当前 ROM 的 Bionic 头文件。脚本用同一源码树中的
`bionic/libc/kernel/tools/clean_header.py` 清洗 QTI 仓库 `include/uapi` 下跟踪的
28 个扩展头，生成独立的 `//device/xiaomi/athens-kernel:athens_qti_kernel_headers`。
新准备的内核输入已包含这个库。已有内核输入可执行一次以下命令：

```bash
python3 "$MANIFEST_REPO/tools/prepare-kernel.py" --qti-headers-only \
  --tree "$TREE" --uapi-cache "$UAPI_CACHE" --output "$TREE/device/xiaomi/athens-kernel"
```

该命令可重复执行。若向另一台构建机复制已准备的内核目录，请同时复制生成的
`Android.bp` 和 `qti-include/`。

脚本只准备构建输入，不重新编译内核。原厂内核、模块和生成的头文件包不提交到本仓库。
