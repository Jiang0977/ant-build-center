# Ant Build Menu - Windows右键菜单扩展

## 项目概述

本项目旨在为Windows系统提供一个便捷的Apache Ant构建工具右键菜单扩展。用户可以直接右键点击`build.xml`文件，选择"Run Ant Build"来执行构建任务，无需手动打开命令行。

## 技术栈

```json
{
  "编程语言": ["Python 3.8+", "Batch Script"],
  "操作系统": ["Windows 10/11"],
  "依赖工具": ["Apache Ant (已安装配置)"],
  "核心技术": [
    "Windows注册表操作",
    "Shell扩展",
    "进程管理",
    "文件系统操作"
  ]
}
```

## 项目目标

- ✅ 实现右键菜单扩展功能
- ✅ 自动检测Apache Ant安装状态
- ✅ 提供用户友好的安装/卸载程序
- ✅ 支持构建结果日志查看
- ✅ 错误处理和异常捕获
- ✅ 支持多种构建目标选择

## 开发阶段

1. **需求分析** ✅
   - 分析Windows右键菜单扩展机制
   - 确定技术实现方案
   - 设计用户交互流程

2. **架构设计** ✅
   - 设计项目目录结构
   - 定义核心模块和接口
   - 制定安装部署方案

3. **核心功能实现** ✅
   - 注册表操作模块
   - Ant命令执行模块
   - 用户界面模块
   - 日志处理模块

4. **测试与修复** ✅
   - 单元测试
   - 集成测试
   - 用户接受测试
   - 问题修复和优化

5. **优化与部署** ✅
   - 性能优化
   - 代码清理
   - 文档完善

## 当前状态
✅ **项目已完成** - 所有核心功能已实现并测试通过

## 实现方案

### 1. 技术方案选择
- **方案A**: 纯注册表方式 - 直接修改Windows注册表添加右键菜单
- **方案B**: Python + 注册表 - 使用Python脚本管理注册表操作 ⭐ (推荐)
- **方案C**: Shell扩展DLL - 开发Windows Shell扩展

### 2. 核心组件
- `registry_manager.py` - 注册表操作管理器
- `ant_executor.py` - Ant命令执行器
- `installer.py` - 安装/卸载程序
- `config.py` - 配置管理
- `logger.py` - 日志处理

### 3. 用户流程
1. 运行安装程序
2. 自动检测Ant环境
3. 注册右键菜单项
4. 用户右键build.xml文件
5. 选择构建目标并执行
6. 查看构建结果

## 项目结构

```
ant-build-menu/
├── src/                     # 源代码目录
│   ├── __init__.py
│   ├── registry_manager.py  # 注册表管理
│   ├── ant_executor.py      # Ant执行器
│   ├── installer.py         # 安装程序
│   ├── config.py           # 配置管理
│   └── logger.py           # 日志管理
├── scripts/                # 脚本目录
│   ├── install.bat         # 安装脚本
│   ├── uninstall.bat       # 卸载脚本
│   └── run_ant.bat         # Ant执行脚本
├── config/                 # 配置文件
│   └── settings.json       # 默认配置
├── tests/                  # 测试目录
│   ├── __init__.py
│   ├── test_registry.py    # 注册表测试
│   └── test_ant_executor.py # 执行器测试
├── docs/                   # 文档目录
│   ├── install_guide.md    # 安装指南
│   └── user_manual.md      # 用户手册
├── requirements.txt        # Python依赖
├── setup.py               # 打包配置
└── README.md              # 项目说明
```

## 快速开始

### 安装
1. 确保已安装Python 3.8+和Apache Ant
2. 以管理员身份运行PowerShell
3. 执行安装命令：
   ```cmd
   python install.py install
   ```

### 使用
1. 右键点击任何XML文件
2. 选择"运行 Ant 构建"菜单
3. 在弹出界面中选择构建目标
4. 开始构建并查看结果

### 卸载
```cmd
python install.py uninstall
```

## 📦 打包与分发

本项目支持多种打包方式，详见 `docs/build_guide.md`

### 开发环境安装
```cmd
pip install -e .              # 可编辑安装
pip install -e .[dev]         # 包含开发工具
python show_build_info.py     # 查看打包信息
```

### 构建分发包
```cmd
python setup.py sdist bdist_wheel    # 生成分发包
```

### 生成独立可执行文件（完整打包流程）

推荐使用打包脚本一键完成：
```powershell
.\scripts\build_installer.ps1         # 构建并打包
.\scripts\build_installer.ps1 -Clean  # 清理后重新构建
```

或手动执行：
```cmd
pyinstaller main.spec         # 生成exe文件
```

**打包脚本执行步骤：**
1. 检查 Python 和 PyInstaller 环境
2. 清理旧的构建文件（可选 `-Clean` 参数）
3. 使用 PyInstaller 构建 exe 文件
4. 复制 `config` 和 `scripts` 到 dist 目录
5. 打包 `windows-dist.zip`（**仅包含 exe 文件**）

**生成的文件：**
| 文件 | 说明 |
|------|------|
| `main.exe` | 右键菜单主程序 |
| `installer.exe` | 安装/卸载程序 |
| `control_center.exe` | 中控中心（带图标，首次运行自动创建桌面快捷方式） |
| `windows-dist.zip` | 发布包（仅包含 exe 文件） |

### 发布到 Gitee
```powershell
# 使用 PowerShell 运行发布脚本
python scripts/publish_gitee_release.py -v V1.0.6 -t your_gitee_token

# 可选参数
python scripts/publish_gitee_release.py --target master  # 指定分支
```


![输入图片说明](examples/image.png)

## 风险评估

- **权限问题**: 修改注册表需要管理员权限
- **环境依赖**: 需要确保Ant已正确安装配置
- **兼容性**: 不同Windows版本的兼容性考虑
- **安全性**: 避免恶意利用注册表修改

## 贡献指南

欢迎提交Bug报告、功能请求和代码贡献。请确保：
- 遵循Python PEP 8编码规范
- 添加必要的测试用例
- 更新相关文档 