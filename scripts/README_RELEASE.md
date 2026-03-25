# 发布流程说明

## 快速发布

### 方式 1: 使用批处理脚本（推荐）
双击运行 `release_quick.bat`，按提示选择发布模式。

### 方式 2: 命令行
```bash
# 标准发布（目录模式）
python release.py

# 单文件发布
python release.py --onefile

# 递增版本号后发布
python release.py --bump patch
```

---

## 完整发布流程

### 1. 更新版本号

**自动递增**:
```bash
# 递增补丁版本号 (2.0.0 -> 2.0.1)
python version.py --bump patch

# 递增次版本号 (2.0.1 -> 2.1.0)
python version.py --bump minor

# 递增主版本号 (2.1.0 -> 3.0.0)
python version.py --bump major
```

**手动修改**:
编辑 `config.json` 中的 `app.version` 字段。

### 2. 更新 CHANGELOG

编辑项目根目录的 `CHANGELOG.md`，在 `[Unreleased]` 部分添加本次更新的内容：

```markdown
## [Unreleased]

### 新增
- 新功能描述

### 变更
- 功能变更描述

### 修复
- Bug 修复描述
```

### 3. 执行发布

```bash
cd scripts

# 标准发布流程（推荐）
python release.py

# 或指定选项
python release.py --onefile  # 单文件模式
python release.py --console  # 显示控制台（调试用）
```

### 4. 发布验证

发布完成后，检查 `release/` 目录：

```
release/
├── v2.0.0_2026-03-25/           # 版本发布目录
│   ├── ADB_GUI_Tool_v2.0.0.exe  # 可执行文件（单文件模式）
│   ├── ADB_GUI_Tool_v2.0.0/     # 或可执行目录（目录模式）
│   ├── ADB_GUI_Tool_v2.0.0.zip  # 压缩包
│   ├── RELEASE_NOTES.md         # 发布说明
│   └── manifest.json            # 文件清单
└── index.json                   # 版本索引
```

### 5. 测试发布版本

1. 解压 ZIP 包到测试目录
2. 运行可执行文件
3. 测试核心功能
4. 检查日志输出

### 6. Git 提交和标签

```bash
cd ..  # 返回项目根目录

# 提交变更
git add .
git commit -m "release: v2.0.0"

# 创建版本标签
git tag -a v2.0.0 -m "Release version 2.0.0"

# 推送到远程
git push origin feature/v2-enhanced-gui
git push origin v2.0.0
```

---

## 发布模式说明

### 目录模式（默认）
- 生成独立目录，包含所有依赖文件
- 启动速度快
- 适合日常使用

**优点**: 启动快，资源独立
**缺点**: 文件较多

### 单文件模式
- 所有资源打包到单个 EXE 文件
- 便于分发
- 首次启动较慢（需解压资源）

**优点**: 单文件分发
**缺点**: 首次启动慢，体积较大

---

## 命令参考

### release.py

```bash
python release.py [选项]

选项:
  --onefile         打包为单文件
  --console         显示控制台窗口
  --skip-build      跳过打包步骤
  --no-zip          不创建 ZIP 压缩包
  --bump TYPE       发布前递增版本号 (major/minor/patch)
  -h, --help        显示帮助
```

### version.py

```bash
python version.py [选项]

选项:
  --bump TYPE       递增版本号 (major/minor/patch)
  --version         显示当前版本
```

### build.py

```bash
python build.py [选项]

选项:
  --onefile         打包为单文件
  --console         显示控制台窗口
  --clean           仅清理构建文件
  --version         显示版本信息
  --bump TYPE       递增版本号后打包
```

---

## 版本号规则

遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/):

- **主版本号 (X.0.0)**: 不兼容的 API 修改
- **次版本号 (0.X.0)**: 向下兼容的功能新增
- **修订号 (0.0.X)**: 向下兼容的问题修正
- **构建号 (0.0.0.X)**: 每次打包自动递增

示例: `2.0.3.15`
- 主版本: 2
- 次版本: 0
- 修订号: 3
- 构建号: 15

---

## 发布检查清单

发布前确认：

- [ ] 代码已测试通过
- [ ] CHANGELOG.md 已更新
- [ ] 版本号已更新
- [ ] Git 分支已合并到 main
- [ ] 所有 TODO 已处理或记录
- [ ] 依赖项已更新（requirements.txt）
- [ ] 配置文件已更新（config.json）
- [ ] README.md 已同步更新

发布后验证：

- [ ] 可执行文件能正常启动
- [ ] 核心功能正常工作
- [ ] 日志无异常错误
- [ ] ZIP 压缩包完整
- [ ] Git 标签已推送
- [ ] Release Notes 准确

---

## 故障排查

### 打包失败

**现象**: PyInstaller 报错
**解决**:
1. 检查 Python 环境和依赖
2. 清理构建缓存: `python build.py --clean`
3. 重新安装 PyInstaller: `pip install --upgrade pyinstaller`

### 运行报错

**现象**: 可执行文件无法启动
**解决**:
1. 使用 `--console` 模式查看错误信息
2. 检查是否缺少依赖文件
3. 验证 `--add-data` 参数是否正确

### 文件缺失

**现象**: 运行时提示找不到文件
**解决**:
1. 检查 build.py 中的 `--add-data` 配置
2. 确保资源文件已包含在打包中
3. 使用目录模式验证文件结构

---

## 自动化发布（可选）

### GitHub Actions

创建 `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Build
        run: |
          cd scripts
          python release.py --onefile
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: release/**/*.zip
```

---

## 联系方式

如有问题，请在 GitHub Issues 提交反馈。
