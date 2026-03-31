"""
配置管理模块

负责加载、保存和管理应用程序配置。
支持从JSON文件加载默认配置，并提供配置项的动态访问。
"""

import json
import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        self._config = {}
        self._config_file = config_file or self._get_default_config_path()
        self.load()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            base_path = Path(sys.executable).parent
        else:
            # 如果是源码运行
            base_path = Path(__file__).parent.parent
        
        return str(base_path / "config" / "settings.json")
    
    def load(self) -> None:
        """从文件加载配置"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                print(f"✅ 配置文件加载成功: {self._config_file}")
            else:
                print(f"⚠️  配置文件不存在: {self._config_file}")
                self._create_default_config()
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """创建默认配置"""
        self._config = {
            "menu_config": {
                "menu_text": "Run Ant Build",
                "menu_text_cn": "运行 Ant 构建",
                "icon": "",
                "registry_key": "AntBuildMenu"
            },
            "ant_config": {
                "timeout_seconds": 300,
                "show_output": True,
                "common_targets": ["compile", "build", "clean", "test"]
            },
            "ui_config": {
                "show_target_selection": True,
                "language": "auto",
                "theme": "default"
            },
            "logging": {
                "level": "INFO",
                "log_file": "ant_build.log",
                "max_log_size_mb": 10,
                "backup_count": 3
            },
            "paths": {
                "ant_home": "",
                "java_home": "",
                "work_dir": ""
            }
        }
        print("📁 使用默认配置")
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            config_dir = Path(self._config_file).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            print(f"✅ 配置文件保存成功: {self._config_file}")
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键，支持点分隔的嵌套键如 'menu_config.menu_text'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        # 遍历到倒数第二层
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置最后一层的值
        config[keys[-1]] = value
    
    def get_menu_text(self) -> str:
        """获取菜单显示文本"""
        language = self.get('ui_config.language', 'auto')
        if language == 'cn' or (language == 'auto' and self._is_chinese_system()):
            return self.get('menu_config.menu_text_cn', '运行 Ant 构建')
        return self.get('menu_config.menu_text', 'Run Ant Build')
    
    def _is_chinese_system(self) -> bool:
        """检测是否为中文系统"""
        try:
            import locale
            system_locale = locale.getdefaultlocale()[0]
            return system_locale and 'zh' in system_locale.lower()
        except:
            return False
    
    def get_ant_home(self) -> Optional[str]:
        """获取Ant安装路径"""
        ant_home = self.get('paths.ant_home')
        if ant_home and os.path.exists(ant_home):
            return ant_home
        
        # 尝试从环境变量获取
        env_ant_home = os.environ.get('ANT_HOME')
        if env_ant_home and os.path.exists(env_ant_home):
            self.set('paths.ant_home', env_ant_home)
            return env_ant_home
        
        return None

    def get_java_command(self) -> Optional[str]:
        """获取可用的 Java 命令或可执行路径"""
        java_home = self.get_java_home()
        if java_home:
            java_name = "java.exe" if sys.platform == "win32" else "java"
            java_exe = Path(java_home) / "bin" / java_name
            if java_exe.exists():
                return str(java_exe)

        java_cmd = shutil.which("java")
        if java_cmd:
            return java_cmd

        return None

    def get_ant_command(self) -> Optional[str]:
        """获取可用的 Ant 命令或可执行路径"""
        ant_home = self.get_ant_home()
        if ant_home:
            ant_name = "ant.bat" if sys.platform == "win32" else "ant"
            ant_exe = Path(ant_home) / "bin" / ant_name
            if ant_exe.exists():
                return str(ant_exe)

        ant_cmd = shutil.which("ant")
        if ant_cmd:
            return ant_cmd

        return None
    
    def get_java_home(self) -> Optional[str]:
        """获取Java安装路径"""
        java_home = self.get('paths.java_home')
        if java_home and os.path.exists(java_home):
            return java_home
        
        # 尝试从环境变量获取
        env_java_home = os.environ.get('JAVA_HOME')
        if env_java_home and os.path.exists(env_java_home):
            self.set('paths.java_home', env_java_home)
            return env_java_home
        
        return None
    
    def validate_environment(self) -> Dict[str, bool]:
        """
        验证运行环境
        
        Returns:
            验证结果字典
        """
        results = {
            'ant_available': False,
            'java_available': False,
            'ant_executable': False
        }
        
        # 检查Java环境
        results['java_available'] = self.get_java_command() is not None
        
        # 检查Ant环境
        ant_cmd = self.get_ant_command()
        results['ant_available'] = ant_cmd is not None
        results['ant_executable'] = ant_cmd is not None
        
        return results
    
    @property
    def config_file(self) -> str:
        """获取配置文件路径"""
        return self._config_file
    
    @property
    def config_data(self) -> Dict[str, Any]:
        """获取完整配置数据"""
        return self._config.copy()


# 全局配置实例
_global_config = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


if __name__ == "__main__":
    # 测试配置模块
    config = Config()
    print("📋 配置测试:")
    print(f"菜单文本: {config.get_menu_text()}")
    print(f"Ant路径: {config.get_ant_home()}")
    print(f"Java路径: {config.get_java_home()}")
    print(f"环境验证: {config.validate_environment()}") 
