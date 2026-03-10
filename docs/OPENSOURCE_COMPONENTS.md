# 开源组件清单 / Open Source Components

本项目集成了以下优秀的开源项目和组件，感谢所有贡献者的付出！

---

## 📱 核心功能组件

### ADB (Android Debug Bridge)
- **来源**: [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- **许可证**: Apache 2.0
- **用途**: Android设备调试桥，提供设备连接、文件传输、应用管理等核心功能
- **版本**: 随Android SDK更新

### Scrcpy
- **来源**: [Genymobile/scrcpy](https://github.com/Genymobile/scrcpy)
- **许可证**: Apache 2.0
- **用途**: Android设备屏幕镜像和控制工具
- **集成路径**: `extensions/scrcpy-win64-v3.3.3/`

---

## 📚 文档与参考

### Awesome ADB
- **来源**: [mzlogin/awesome-adb](https://github.com/mzlogin/awesome-adb)
- **许可证**: 无限制
- **用途**: ADB命令使用大全，提供中英文命令参考手册
- **集成路径**: `extensions/awesome-adb-readme/`
- **说明**: 完整的ADB命令文档，支持Markdown渲染显示

### Markdown Here
- **来源**: [adam-p/markdown-here](https://github.com/adam-p/markdown-here)
- **许可证**: MIT
- **用途**: 参考其Markdown渲染方案，用于命令手册的格式化显示
- **说明**: 仅参考实现，未直接引用代码

---

## 🔧 反编译工具

### JADX-GUI-AI
- **来源**: [cncsnet1/jadx-gui-ai](https://github.com/cncsnet1/jadx-gui-ai)
- **许可证**: Apache 2.0
- **用途**: APK反编译工具，支持AI辅助代码分析
- **集成路径**: `extensions/jadx_decompiler/`
- **功能特性**:
  - 将APK/DEX反编译为Java代码
  - AI智能代码分析与解释
  - 安全漏洞检测
  - 代码注释翻译

---

## 🎯 功能参考项目

### ADB GUI (bigsinger)
- **来源**: [bigsinger/adbgui](https://github.com/bigsinger/adbgui)
- **许可证**: MIT
- **参考功能**: 
  - 文件列表浏览
  - 应用列表管理
- **说明**: 参考其功能设计，重新实现

### ADB GUI (hexadezi)
- **来源**: [hexadezi/adbGUI](https://github.com/hexadezi/adbGUI)
- **许可证**: MIT
- **参考功能**:
  - 增强日志系统（级别过滤、搜索、导出）
  - 快捷操作面板
- **说明**: 参考其功能设计，重新实现

### ADB-Explorer
- **来源**: [Alex4SSB/ADB-Explorer](https://github.com/Alex4SSB/ADB-Explorer)
- **许可证**: MIT
- **参考功能**:
  - 高级文件管理器
  - 驱动器视图
  - 回收站功能
  - 操作队列
- **说明**: 参考其功能设计，使用PyQt6重新实现

### AndroidTestScripts
- **来源**: [gb112211/AndroidTestScripts](https://github.com/gb112211/AndroidTestScripts)
- **许可证**: MIT
- **参考功能**:
  - 批量APK操作
  - 性能测试（FPS/CPU/内存）
  - 媒体捕获
  - 日志收集
- **说明**: 参考其功能设计，作为测试脚本扩展集成

### AndroidControl
- **来源**: [imharryzhu/AndroidControl](https://github.com/imharryzhu/AndroidControl)
- **许可证**: MIT
- **参考功能**:
  - 多设备集群控制
  - 脚本录制与回放
  - 同步操作
  - 设备分组管理
- **说明**: 参考其功能设计，作为集群控制扩展集成

---

## 🐍 Python依赖库

| 库名 | 版本 | 许可证 | 用途 |
|------|------|--------|------|
| PyQt6 | >=6.0 | GPL v3 | GUI框架 |
| psutil | >=5.9 | BSD-3 | 系统监控 |

---

## 📄 许可证说明

本项目遵循各开源组件的原始许可证要求：

- **Apache 2.0**: 允许商业使用、修改、分发，需保留版权声明
- **MIT**: 允许任意使用，需保留版权声明
- **GPL v3**: 衍生作品需以相同许可证开源
- **BSD-3**: 允许任意使用，需保留版权声明

---

## 🙏 致谢

感谢以上所有开源项目的作者和贡献者！

开源社区的力量让这个项目成为可能。如果本项目对您有帮助，也请考虑为上述原始项目点个Star ⭐

---

*最后更新: 2024年*
