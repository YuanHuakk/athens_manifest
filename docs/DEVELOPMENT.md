# 本地开发

设备树在 `android_device_xiaomi_athens` 修改，框架补丁和工具在 `athens_manifest` 修改。
PixelOS 源码目录用于调试、应用补丁和编译，继续使用已有的 `out`、vendor 和内核输入。

## 绑定工作区

在 `athens_manifest` 根目录执行一次：

```bash
python3 tools/workspace.py configure \
  --tree /path/to/pixelos \
  --device /path/to/android_device_xiaomi_athens \
  --stock /path/to/extracted-stock \
  --sdk /path/to/android-sdk
```

路径保存在 `.local/workspace.json`，同步状态也保存在 `.local/`，该目录不提交 Git。
新工作区仍需先按 [BUILD.md](BUILD.md) 准备源码、vendor、内核和 APK。

## 日常命令

```bash
python3 tools/workspace.py status          # 检查两边是否一致
python3 tools/workspace.py sync            # 同步设备树和补丁
python3 tools/workspace.py build nothing   # 同步后检查构建配置
python3 tools/workspace.py build pixelos   # 同步后增量编译完整 ROM
python3 tools/workspace.py build cameraserver  # 也可指定多个编译目标
```

默认编译 `user`，athens 仍保持 SELinux Permissive。需要 ADB Root 和启动诊断脚本时，
使用 `BUILD_VARIANT=userdebug python3 tools/workspace.py build pixelos`。
构建类型不改变签名密钥；当前本地输入使用开发测试密钥。

设备树按 Git 管理的文件及未忽略的新文件同步；删除的源文件也会删除对应构建副本。
相机、Pixel Tips APK、vendor、内核和 `out` 不属于这次源码同步的范围，继续原地使用。
同步前会检查构建副本，存在未归档修改时停止，不覆盖它们。

修改相机处理脚本后，重新生成本地 APK；修改提取清单后，重新提取 vendor：

```bash
python3 tools/workspace.py camera
python3 tools/workspace.py vendor
```

这两步会先同步源码。相机默认使用源码树的平台测试密钥，发布签名可通过 `KEY`、`CERT`
指定。普通构建不会自动重提取原厂文件或重新处理相机 APK。

## 框架调试

在 PixelOS 源码树调试上游项目后，将改动导出为补丁：

```bash
python3 tools/workspace.py capture frameworks/av
python3 tools/workspace.py sync
python3 tools/workspace.py build cameraserver
```

`capture` 按固定上游提交生成补丁，不提交 Git，也不改变上游项目的暂存区。
新增文件要明确列出，避免把调试日志等临时文件放进补丁：

```bash
python3 tools/workspace.py capture hardware/xiaomi \
  --include path/to/new/source.cpp
```

也可以直接修改仓库中的补丁，再执行 `sync`。工具根据上次已应用的版本计算更新，
无需手动回退旧补丁。新涉及的上游项目需先加入 `patches/series.json` 并固定基线提交。

本地开发不自动更新 `device-tree.json` 的发布提交号；发布时应在提交设备树后更新它。
