"""
项目管理模块

提供文件验证、分组操作的业务逻辑封装。
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.workspace_config import get_workspace_config, WorkspaceConfig
from src.ant_executor import AntExecutor


class ProjectManager:
    """项目管理器类"""

    def __init__(self, workspace_config: Optional[WorkspaceConfig] = None):
        """
        初始化项目管理器

        Args:
            workspace_config: 工作区配置实例，None则使用全局实例
        """
        self.config = workspace_config or get_workspace_config()
        self.executor = AntExecutor()

    # ==================== 文件验证 ====================

    def validate_ant_file(self, path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证是否为有效的Ant构建文件

        Args:
            path: 文件路径

        Returns:
            Tuple[bool, str, Dict]: (是否有效, 消息, 解析信息)
        """
        info = {
            'project_name': '',
            'default_target': '',
            'targets': [],
            'target_count': 0
        }

        # 检查文件存在
        if not os.path.exists(path):
            return False, f"文件不存在: {path}", info

        # 检查扩展名
        if not path.lower().endswith('.xml'):
            return False, "不是XML文件", info

        # 解析XML
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # 检查是否为Ant项目文件
            if root.tag != 'project':
                return False, "不是Ant构建文件（缺少<project>根元素）", info

            # 提取项目信息
            info['project_name'] = root.get('name', Path(path).stem)
            info['default_target'] = root.get('default', '')

            # 提取目标
            targets = root.findall('.//target')
            info['targets'] = [t.get('name') for t in targets if t.get('name')]
            info['target_count'] = len(info['targets'])

            if info['target_count'] == 0:
                return False, "没有找到构建目标", info

            return True, "有效的Ant构建文件", info

        except ET.ParseError as e:
            return False, f"XML解析错误: {e}", info
        except Exception as e:
            return False, f"验证失败: {e}", info

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件详细信息"""
        valid, msg, info = self.validate_ant_file(path)

        return {
            'path': path,
            'filename': Path(path).name,
            'directory': str(Path(path).parent),
            'valid': valid,
            'message': msg,
            **info
        }

    # ==================== 文件操作 ====================

    def add_files(self, paths: List[str], group_id: Optional[str] = None) -> Dict[str, Any]:
        """
        批量添加文件

        Args:
            paths: 文件路径列表
            group_id: 目标分组ID

        Returns:
            添加结果统计
        """
        result = {
            'added': [],
            'skipped': [],
            'invalid': []
        }

        for path in paths:
            # 验证文件
            valid, msg, info = self.validate_ant_file(path)

            if not valid:
                result['invalid'].append({'path': path, 'reason': msg})
                continue

            # 添加文件
            file_id = self.config.add_file(
                path=path,
                group_id=group_id,
                alias=Path(path).name
            )

            if file_id:
                # 设置默认目标
                if info.get('default_target'):
                    self.config.update_file(file_id, default_target=info['default_target'])
                result['added'].append({'path': path, 'id': file_id})
            else:
                result['skipped'].append({'path': path, 'reason': '文件已存在'})

        return result

    def remove_file(self, file_id: str) -> bool:
        """移除文件"""
        return self.config.delete_file(file_id)

    def get_files_by_group(self, group_id: str) -> List[Dict[str, Any]]:
        """获取分组下的所有文件"""
        group = self.config.get_group(group_id)
        if not group:
            return []
        return group.get('files', [])

    # ==================== 分组操作 ====================

    def create_group(self, name: str, color: str = "#3498db") -> str:
        """创建新分组"""
        return self.config.add_group(name, color)

    def rename_group(self, group_id: str, new_name: str) -> bool:
        """重命名分组"""
        return self.config.update_group(group_id, name=new_name)

    def delete_group(self, group_id: str) -> bool:
        """
        删除分组（文件移动到未分组）
        """
        groups = self.config.get_groups()

        # 找到未分组
        default_group = None
        for g in groups:
            if g['name'] == '未分组' and g['id'] != group_id:
                default_group = g
                break

        # 如果没有未分组，使用第一个非当前分组
        if not default_group:
            for g in groups:
                if g['id'] != group_id:
                    default_group = g
                    break

        target_id = default_group['id'] if default_group else None
        return self.config.delete_group(group_id, move_files_to=target_id)

    def move_file_to_group(self, file_id: str, group_id: str,
                           target_index: Optional[int] = None) -> bool:
        """移动文件到指定分组或调整排序"""
        return self.config.move_file(file_id, group_id, target_index)

    # ==================== 构建操作 ====================

    def get_targets(self, file_id: str) -> List[str]:
        """获取文件的构建目标列表"""
        file = self.config.get_file(file_id)
        if not file:
            return []

        path = file.get('path')
        if not path or not os.path.exists(path):
            return []

        info = self.executor.parse_build_file(path)
        return info.get('targets', [])

    def record_build_result(self, file_id: str, success: bool) -> None:
        """记录构建结果"""
        self.config.record_build(file_id, success)

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取工作区统计信息"""
        groups = self.config.get_groups()
        all_files = self.config.get_all_files()

        success_count = sum(1 for f in all_files if f.get('last_status') == 'success')
        failure_count = sum(1 for f in all_files if f.get('last_status') == 'failure')

        return {
            'group_count': len(groups),
            'file_count': len(all_files),
            'success_count': success_count,
            'failure_count': failure_count,
            'never_run_count': len(all_files) - success_count - failure_count
        }

    def check_files_exist(self) -> List[Dict[str, Any]]:
        """检查所有文件是否存在，返回不存在的文件列表"""
        missing = []
        for file in self.config.get_all_files():
            path = file.get('path')
            if path and not os.path.exists(path):
                missing.append(file)
        return missing


# 全局实例
_project_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """获取全局项目管理器实例"""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager


if __name__ == "__main__":
    # 测试项目管理器
    manager = ProjectManager()
    print("📋 项目管理器测试:")
    print(f"统计信息: {manager.get_statistics()}")
