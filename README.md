# athens — PixelOS 构建清单

Redmi K100 Pro（athens）的 PixelOS 源码清单、补丁和构建工具。
设备树单独保存在 [android_device_xiaomi_athens](https://github.com/YuanHuakk/android_device_xiaomi_athens) 仓库。

## 内容

| 路径                               | 内容                                                 |
| ---------------------------------- | ---------------------------------------------------- |
| `default.xml`                      | repo 入口，引用完整锁定清单                          |
| `manifests/pixelos-r12-locked.xml` | 上游项目及对应提交                                   |
| `device-tree.json`                 | 配套设备树的路径、分支和提交                         |
| `uapi-sources.json`                | 内核头文件的公开源码版本                             |
| `patches/`                         | 18 个项目的补丁及应用基线                            |
| `tools/`                           | 原厂镜像解包、内核准备、补丁应用、相机处理和构建工具 |
| `docs/`                            | 构建步骤和内核输入                                   |
| `tests/`                           | 工具测试                                             |

[构建步骤](docs/BUILD.md) · [本地开发](docs/DEVELOPMENT.md) · [内核输入](docs/KERNEL.md)

## 使用方式

先按锁定清单同步 PixelOS，再检出配套设备树，应用补丁并准备本地专有文件。
补丁脚本会检查各项目的基线提交；`repo sync` 不会代替应用补丁这一步。

vendor 文件、预编译内核、小米相机 APK、签名密钥和 ROM 包均不在仓库中。
原厂文件通过脚本从 306 线刷包提取，头文件通过固定的公开源码生成。

来源与许可见 [NOTICE.md](NOTICE.md)。
