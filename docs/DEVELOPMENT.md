# 本地开发

在共享设备树仓库维护跨 ROM 的改动。在本仓库维护 Infinity X 补丁和构建工具。新工作区先完成[首次构建准备](BUILD.md)。

## 绑定工作区

检出共享设备树的 `android-17` 分支，从本仓库根目录运行以下命令。配置和同步状态保存在 Git 忽略的 `.local/`。

```bash
python3 tools/workspace.py configure \
  --tree /path/to/infinity-athens \
  --device /path/to/android_device_xiaomi_athens \
  --stock /path/to/extracted-stock \
  --sdk /path/to/android-sdk
```

## 同步与构建

| 命令 | 用途 |
| --- | --- |
| `python3 tools/workspace.py status` | 检查工作区差异 |
| `python3 tools/workspace.py sync` | 同步设备树和补丁 |
| `python3 tools/workspace.py build nothing` | 同步并检查构建配置 |
| `python3 tools/workspace.py build` | 同步并构建 ROM |
| `python3 tools/workspace.py build cameraserver` | 同步并构建指定目标 |

同步会处理设备树中已删除的文件，遇到构建树中未归档的修改时会暂停。vendor、内核、APK 和 `out` 继续原地使用。[更新源码](BUILD.md#更新现有源码)后，独立检出的设备树也需对齐版本。

默认构建 `user`，通过 `BUILD_VARIANT=userdebug` 可选择调试版。

修改专有文件清单后运行 `python3 tools/workspace.py vendor`，修改相机处理脚本后运行 `python3 tools/workspace.py camera`。两者都会先同步。相机在发布构建中可用 `KEY` 和 `CERT` 指定签名。

## 导出框架补丁

在 Infinity X 源码树调试后，从本仓库导出补丁。用 `--include` 明确列出要纳入的新文件。

```bash
python3 tools/workspace.py capture frameworks/av
python3 tools/workspace.py capture hardware/xiaomi --include path/to/new/source.cpp
```

`capture` 以项目当前 `HEAD` 为基线，保留上游项目的暂存状态。新项目先登记在 `patches/series.json`。也可直接编辑补丁，再用 `sync` 按上次已应用的版本更新。

## 提交前检查

```bash
ruff check .
ruff format --check .
python3 -m unittest discover -s tests -v
```
