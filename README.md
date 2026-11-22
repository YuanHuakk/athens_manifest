# athens — Evolution X 构建清单

Redmi K100 Pro（athens）的 Evolution X 源码清单、补丁和构建工具。
PixelOS 和 Evolution X 共用 [android_device_xiaomi_athens 的 `android-17` 分支](https://github.com/YuanHuakk/android_device_xiaomi_athens/tree/android-17)。

## 内容

| 路径                               | 内容                                                 |
| ---------------------------------- | ---------------------------------------------------- |
| `default.xml`                      | 叠加在 Evolution X 官方清单上的 Athens 设备适配     |
| `manifests/`                       | PixelOS r12 构建的历史清单                           |
| `device-tree.json`                 | 配套设备树的仓库名、路径和分支                       |
| `uapi-sources.json`                | 内核头文件的公开源码版本                             |
| `patches/`                         | 设备适配补丁及应用顺序                               |
| `tools/`                           | 原厂镜像解包、内核准备、补丁应用、相机处理和构建工具 |
| `docs/`                            | 构建步骤和内核输入                                   |
| `tests/`                           | 工具测试                                             |

[构建步骤](docs/BUILD.md) · [本地开发](docs/DEVELOPMENT.md) · [内核输入](docs/KERNEL.md)

## 使用方式

使用 Evolution X 官方 `cnb` 清单初始化源码，将 `default.xml` 安装到 `.repo/local_manifests/`。
`repo sync` 会更新官方清单及设备适配分支。同步完成后，补丁脚本会先检查整套补丁能否应用到当前源码，检查通过后再写入。

vendor 文件、预编译内核、APK、签名密钥和 ROM 包均不在仓库中。
原厂文件从国行 HyperOS 4 的 `OS4.0.6.0.XPICNXM` 线刷包提取，内核头文件按配套源码生成。

来源与许可见 [NOTICE.md](NOTICE.md)。
