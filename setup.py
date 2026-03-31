"""
Ant Build Menu 项目打包配置

使用setuptools进行项目打包，支持生成wheel和sdist分发包。
也可以配合PyInstaller生成单独的可执行文件。
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
README_PATH = Path(__file__).parent / "README.md"
try:
    with open(README_PATH, "r", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Ant Build Menu - Windows右键菜单扩展for Apache Ant"

# 读取requirements文件
REQUIREMENTS_PATH = Path(__file__).parent / "requirements.txt"
try:
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() 
            for line in f.readlines() 
            if line.strip() and not line.startswith("#")
        ]
except FileNotFoundError:
    requirements = [
        "psutil>=5.9.0",
        "lxml>=4.9.0",
    ]

# 项目版本
VERSION = "1.0.6"

setup(
    name="ant-build-menu",
    version=VERSION,
    author="AI Assistant",
    author_email="",
    description="Windows右键菜单扩展 for Apache Ant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/ant-build-menu",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: Tk",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ],
        "build": [
            "pyinstaller>=5.0.0",
            "setuptools>=65.0.0",
            "wheel>=0.37.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ant-build-menu=main:main",
            "ant-build-installer=src.installer:main",
            "ant-build-control-center=control_center:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "scripts/*.bat"],
    },
    data_files=[
        ("config", ["config/settings.json"]),
        ("scripts", []),  # 脚本文件会在安装时动态生成
    ],
    zip_safe=False,
    keywords="ant build menu windows context menu右键菜单",
    project_urls={
        "Bug Reports": "https://github.com/your-username/ant-build-menu/issues",
        "Source": "https://github.com/your-username/ant-build-menu",
        "Documentation": "https://github.com/your-username/ant-build-menu/wiki",
    },
)


# PyInstaller配置示例
PYINSTALLER_SPEC = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/settings.json', 'config'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ant-build-menu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # 如果有图标文件
)

# 创建安装器的exe
installer_exe = EXE(
    PYZ([('installer', 'src/installer.py', 'PYSOURCE')]),
    [],
    [],
    [],
    [],
    name='installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

def show_help():
    """显示setup.py使用帮助"""
    print("🏗️  Ant Build Menu 打包配置")
    print(f"📦 版本: {VERSION}")
    print(f"📚 依赖包数量: {len(requirements)}")
    print(f"📝 详细文档: docs/build_guide.md")
    print("\n🚀 常用命令:")
    print("1. 开发安装: pip install -e .")
    print("2. 构建分发包: python setup.py sdist bdist_wheel")
    print("3. PyInstaller打包: pyinstaller main.spec")
    print("4. 安装开发依赖: pip install -e .[dev]")
    print("5. 查看所有命令: python setup.py --help-commands")
    
    # 生成PyInstaller配置文件
    spec_file = Path(__file__).parent / "main.spec"
    if not spec_file.exists():
        try:
            with open(spec_file, "w", encoding="utf-8") as f:
                f.write(PYINSTALLER_SPEC)
            print(f"\n✅ 已生成PyInstaller配置文件: {spec_file}")
        except Exception as e:
            print(f"\n❌ 生成PyInstaller配置文件失败: {e}")
    
    print(f"\n📖 更多信息请查看: docs/build_guide.md")

if __name__ == "__main__":
    import sys
    # 如果没有提供命令参数，显示帮助信息
    if len(sys.argv) == 1:
        show_help()
    else:
        # 否则按正常setuptools流程处理
        pass
