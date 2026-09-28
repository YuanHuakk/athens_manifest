# athens — PixelOS 构建清单

Redmi K100 Pro（athens）PixelOS r12 的源码版本、补丁和构建工具。
设备树单独保存在 `android_device_xiaomi_athens` 仓库。

## 内容

| 路径 | 内容 |
|---|---|
| `default.xml` | repo 入口，引用完整锁定清单 |
| `manifests/pixelos-r12-locked.xml` | 上游项目及对应提交 |
| `device-tree.json` | 配套设备树的路径、分支和提交 |
| `patches/` | 17 个项目的补丁及应用基线 |
| `tools/` | 补丁应用、相机处理、构建和 ROM 导出脚本 |
| `docs/` | 构建步骤、内核输入和测试范围 |
| `tests/` | 工具测试 |

[构建步骤](docs/BUILD.md) · [内核输入](docs/KERNEL.md) · [测试状态](docs/STATUS.md)

## 使用方式

先按锁定清单同步 PixelOS，再检出配套设备树，应用补丁并准备本地专有文件。
补丁脚本会检查各项目的基线提交；`repo sync` 不会代替应用补丁这一步。

两个仓库目前只在本地整理，未配置 GitHub 远程地址。构建文档使用本地仓库路径。
vendor 文件、预编译内核、小米相机 APK、签名密钥和 ROM 包均不在仓库中。

当前配置为 SELinux Permissive、userdebug；System 安全补丁为 2026-09-01，
Vendor / Boot 为 2026-08-01。原工作区 r12 已编译通过，拆分后的仓库尚未从空目录完整重编。

来源与许可见 [NOTICE.md](NOTICE.md)。
