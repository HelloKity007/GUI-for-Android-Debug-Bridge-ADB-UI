# 🚀 Release 发布快速指南

## 📋 发布前检查清单

- [ ] 代码已测试通过
- [ ] CHANGELOG.md 已更新
- [ ] 所有功能正常工作
- [ ] 无严重 Bug

---

## 🎯 一键发布（推荐）

### Windows 用户
双击运行: `scripts\release_quick.bat`

选择发布模式:
1. **标准发布** - 目录模式 + ZIP（推荐）
2. **单文件发布** - 单个 EXE + ZIP
3. **快速打包** - 仅打包现有构建
4. **版本更新** - 递增版本号后发布

---

## 📝 手动发布流程

### 1. 更新版本号（可选）

```bash
cd scripts

# 查看当前版本
python version.py --version

# 递增补丁版本 (2.0.0 -> 2.0.1)
python version.py --bump patch

# 递增次版本 (2.0.1 -> 2.1.0)
python version.py --bump minor

# 递增主版本 (2.1.0 -> 3.0.0)
python version.py --bump major
```

### 2. 更新 CHANGELOG.md

编辑根目录的 `CHANGELOG.md`，在 `[Unreleased]` 部分添加更新内容。

### 3. 执行发布

```bash
cd scripts

# 标准发布（推荐）
python release.py

# 单文件模式
python release.py --onefile

# 递增版本号并发布
python release.py --bump patch
```

### 4. 验证发布

检查 `release/v{version}_{date}/` 目录:
- ✅ 可执行文件或目录
- ✅ ZIP 压缩包
- ✅ RELEASE_NOTES.md
- ✅ manifest.json

### 5. 测试运行

解压 ZIP 包，运行可执行文件，测试核心功能。

### 6. Git 提交

```bash
cd ..  # 返回项目根目录

git add .
git commit -m "release: v{version}"
git tag -a v{version} -m "Release version {version}"
git push origin feature/v2-enhanced-gui
git push origin v{version}
```

---

## 📦 发布输出

### 目录结构
```
release/
└── v2.0.0_2026-03-25/
    ├── ADB_GUI_Tool_v2.0.0/      # 可执行目录（目录模式）
    │   ├── ADB_GUI_Tool_v2.0.0.exe
    │   ├── extensions/
    │   ├── plugins/
    │   └── ...
    ├── ADB_GUI_Tool_v2.0.0.zip   # 压缩包
    ├── RELEASE_NOTES.md          # 发布说明
    └── manifest.json             # 文件清单
```

### 或单文件模式
```
release/
└── v2.0.0_2026-03-25/
    ├── ADB_GUI_Tool_v2.0.0.exe   # 单个可执行文件
    ├── ADB_GUI_Tool_v2.0.0.zip   # 压缩包
    ├── RELEASE_NOTES.md
    └── manifest.json
```

---

## 🔧 发布模式对比

| 模式 | 文件数量 | 启动速度 | 体积 | 适用场景 |
|------|---------|---------|------|---------|
| **目录模式** | 多文件 | 快 | 中等 | 日常使用 |
| **单文件模式** | 单文件 | 较慢 | 较大 | 快速分发 |

**推荐**: 目录模式（启动快，用户体验好）

---

## ⚙️ 命令参考

### release.py 完整参数

```bash
python release.py [选项]

--onefile         # 打包为单文件
--console         # 显示控制台（调试用）
--skip-build      # 跳过打包步骤
--no-zip          # 不创建 ZIP 压缩包
--bump TYPE       # 发布前递增版本号 (major/minor/patch)
-h, --help        # 显示帮助
```

### 使用示例

```bash
# 标准发布
python release.py

# 递增版本号后发布
python release.py --bump patch

# 单文件模式发布
python release.py --onefile

# 仅打包现有构建
python release.py --skip-build --no-zip
```

---

## 🐛 常见问题

### Q1: 打包失败
**A**:
1. 检查 Python 环境: `python --version`
2. 清理构建缓存: `python build.py --clean`
3. 重装 PyInstaller: `pip install --upgrade pyinstaller`

### Q2: 运行时报错
**A**:
1. 使用 `--console` 模式查看错误
2. 检查日志文件: `logs/` 目录
3. 确认依赖文件完整

### Q3: 版本号不对
**A**:
- 检查 `config.json` 中的 `app.version`
- 或使用 `python version.py --bump patch` 自动更新

---

## 📚 相关文档

- **详细文档**: `scripts/README_RELEASE.md`
- **更新日志**: `CHANGELOG.md`
- **用户手册**: `README.md`

---

## 📞 技术支持

如有问题，请在 GitHub Issues 提交。

---

**最后更新**: 2026-03-25
