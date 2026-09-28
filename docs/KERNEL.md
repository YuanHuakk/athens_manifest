# 内核输入

当前使用原厂内核 `6.12.69-android16-6-g0d80ee00f747-ab15461283-4k`，
来自 athens OS3.0.306.0.WPICNXM。

将本地内核包放在 `device/xiaomi/athens-kernel`，目录如下：

| 路径 | 来源 |
|---|---|
| `kernel` | boot.img 的 kernel 段 |
| `dtbo.img` | 原厂 dtbo.img |
| `dtb/raw01.dtb` … `dtb/raw12.dtb` | vendor_boot.img 的串联 FDT，按原始顺序拆分 |
| `vendor_ramdisk/` | vendor_boot ramdisk 中的 lib/modules |
| `vendor_dlkm/` | vendor_dlkm 镜像中的 lib/modules |
| `system_dlkm/` | system_dlkm 中该内核版本的模块目录内容 |
| `system_dlkm_flatten/` | system_dlkm 的 flatten/lib/modules |
| `kernel-headers.tar.gz` | UAPI 头，归档根为 usr/include |

`tools/prepare-kernel.py` 完成以上目录的生成。它调用源码树中的 `unpack_bootimg.py`，
按 FDT 的 totalsize 顺序拆分 DTB，用 lz4 / cpio 提取 vendor ramdisk 的模块。
模块加载清单和相对符号链接保持原样。

## UAPI 来源

`uapi-sources.json` 固定两个公开源码提交：

- GKI `android16-6.12`：`5169763275538844ab830145369bb81f14d261d3`
- QTI SM8850：`abdf3a50f1f9eb8ebace76e4e1a8e16c2e089a63`

生成顺序为 GKI `include/uapi`、GKI ARM64 `asm`、QTI `include/uapi`；QTI 同名文件覆盖
GKI。去除 Kbuild / Makefile，再加入与 r12 一致的 Makefile，生成以 `usr/include/` 为根的
压缩包。归档时间和文件顺序固定，不依赖下载时间。

这是 r12 使用的源码头文件组合，不是内核 `make headers_install` 的导出结果。
重新生成的 989 个文件已与 r12 输入逐文件比较一致。IPA 头文件由源码树中
`hardware/qcom-caf/sm8850/dataipa` 单独提供，不从其他机型的内核包补入。

脚本只准备构建输入，不重新编译内核。原厂内核、模块和生成的头文件包不提交到本仓库。
