"""
Ant Build Menu - Windows右键菜单扩展

一个为Windows系统提供Apache Ant构建工具右键菜单扩展的项目。
用户可以直接右键点击build.xml文件来执行Ant构建任务。

Author: AI Assistant
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__email__ = ""
__description__ = "Windows右键菜单扩展 for Apache Ant"

# 导出主要模块
from .config import Config
from .ant_executor import AntExecutor
from .logger import setup_logger

try:
    from .registry_manager import RegistryManager
except ImportError:
    RegistryManager = None

__all__ = [
    "Config",
    "RegistryManager", 
    "AntExecutor",
    "setup_logger"
] 
