# 来源与许可

| 项目               | 上游                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| PixelOS            | https://github.com/PixelOS-AOSP/android_manifest                         |
| 平台代码、提取工具 | https://github.com/LineageOS                                             |
| SM8850 公共树      | https://github.com/AlexZorzi/android_device_xiaomi_sm8850-common         |
| GKI UAPI           | https://android.googlesource.com/kernel/common                           |
| QTI UAPI           | https://github.com/LineageOS/android_kernel_qcom_sm8850                  |
| Xiaomi 硬件适配    | https://github.com/AlexZorzi/android_hardware_xiaomi                     |
| 相机兼容处理参考   | https://github.com/xiaomi-onyx-dev/android_device_xiaomi_onyx-miuicamera |

相机参考提交：`933f9e89cf7f3ba81873f1ece4a6f4ab5811e585`。
其余版本见锁定 manifest、`patches/series.json` 和 `uapi-sources.json`。

原文件保留原有版权和许可证。本仓库新增的工具、文档采用 Apache-2.0；
跨项目补丁遵循对应上游文件的许可证。

vendor 文件、APK 和原厂预编译内核不随仓库发布。工具的许可证不覆盖这些文件。

构建工具和补丁集迁自本地 `android_device_xiaomi_athens`，原提交为
`3b19343ba0038699d7223e867af590edae3b9b50`。迁移保留文件内的作者和许可声明。
