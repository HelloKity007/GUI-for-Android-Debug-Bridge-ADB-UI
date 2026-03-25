# Release 目录

此目录包含 ADB GUI Tool 的正式发布版本。

## 目录结构

```
release/
├── v2.0.0_2026-03-25/           # 版本发布目录
│   ├── ADB_GUI_Tool_v2.0.0/     # 可执行文件目录
│   │   ├── ADB_GUI_Tool_v2.0.0.exe
│   │   ├── extensions/          # 扩展目录
│   │   ├── plugins/             # 插件目录
│   │   └── ...                  # 其他资源文件
│   ├── ADB_GUI_Tool_v2.0.0.zip  # 压缩包
│   ├── RELEASE_NOTES.md         # 发布说明
│   └── manifest.json            # 文件清单
├── index.json                   # 版本索引
└── README.md                    # 本文件
```

## 版本命名规则

### 目录命名
格式: `v{version}_{date}`

示例:
- `v2.0.0_2026-03-25` - 2.0.0 版本，发布于 2026年3月25日
- `v2.1.0_2026-04-01` - 2.1.0 版本，发布于 2026年4月1日

### 文件命名
- **可执行文件**: `ADB_GUI_Tool_v{version}.exe`
- **压缩包**: `ADB_GUI_Tool_v{version}.zip`
- **发布说明**: `RELEASE_NOTES.md`
- **清单文件**: `manifest.json`

## 版本索引 (index.json)

```json
{
  "releases": [
    {
      "version": "2.0.0",
      "full_version": "2.0.0.15",
      "date": "2026-03-25",
      "path": "v2.0.0_2026-03-25",
      "latest": true
    }
  ]
}
```

## 使用说明

### 下载最新版本

1. 打开 `index.json` 查找 `"latest": true` 的版本
2. 进入对应的版本目录
3. 下载 `.zip` 压缩包

### 安装步骤

1. 解压 ZIP 文件到目标目录
2. 运行 `ADB_GUI_Tool_v{version}.exe`
3. 首次启动会提示配置 ADB 路径
4. 连接 Android 设备开始使用

### 版本更新

直接下载新版本并解压到新目录即可。

配置文件位置:
- 用户设置: `settings.json`（新版本会自动创建）
- ADB 配置: `config.json`（可从旧版本复制）

## 版本历史

详见各版本目录中的 `RELEASE_NOTES.md` 或项目根目录的 `CHANGELOG.md`。

## 系统要求

- **操作系统**: Windows 10/11 (64位)
- **Android 设备**: 需启用 USB 调试
- **运行时**: 无需额外依赖（已内置）

## 问题反馈

如遇到问题，请在 GitHub Issues 提交反馈。

---

**最后更新**: 2026-03-25
