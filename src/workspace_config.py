"""
工作区配置管理模块

负责中控中心的工作区数据持久化，包括文件分组、构建历史等。
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class WorkspaceConfig:
    """工作区配置管理类"""

    VERSION = "1.0"

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化工作区配置管理器

        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        self._config_file = config_file or self._get_default_config_path()
        self._data = self._create_default_data()
        self.load()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        return str(base_path / "config" / "workspace.json")

    def _create_default_data(self) -> Dict[str, Any]:
        """创建默认数据结构"""
        return {
            "version": self.VERSION,
            "groups": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "未分组",
                    "color": "#95a5a6",
                    "expanded": True,
                    "files": []
                }
            ],
            "recent_files": [],
            "settings": {
                "max_concurrent_builds": 1,
                "auto_scroll_output": True,
                "confirm_before_batch": True,
                "show_build_notifications": True
            }
        }

    def load(self) -> None:
        """从文件加载配置"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                print(f"✅ 工作区配置加载成功: {self._config_file}")

                # 确保有默认分组
                if not self._data.get('groups'):
                    self._data['groups'] = self._create_default_data()['groups']
            else:
                print(f"⚠️  工作区配置不存在，使用默认配置: {self._config_file}")
                self._data = self._create_default_data()
        except Exception as e:
            print(f"❌ 加载工作区配置失败: {e}")
            self._data = self._create_default_data()

    def save(self) -> bool:
        """保存配置到文件"""
        try:
            config_dir = Path(self._config_file).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            print(f"✅ 工作区配置保存成功: {self._config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存工作区配置失败: {e}")
            return False

    # ==================== 分组管理 ====================

    def get_groups(self) -> List[Dict[str, Any]]:
        """获取所有分组"""
        return self._data.get('groups', [])

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取分组"""
        for group in self._data.get('groups', []):
            if group.get('id') == group_id:
                return group
        return None

    def add_group(self, name: str, color: str = "#3498db") -> str:
        """
        添加新分组

        Args:
            name: 分组名称
            color: 分组颜色

        Returns:
            新分组的ID
        """
        group_id = str(uuid.uuid4())
        new_group = {
            "id": group_id,
            "name": name,
            "color": color,
            "expanded": True,
            "files": []
        }
        self._data['groups'].append(new_group)
        self.save()
        return group_id

    def update_group(self, group_id: str, name: Optional[str] = None,
                     color: Optional[str] = None, expanded: Optional[bool] = None) -> bool:
        """更新分组信息"""
        group = self.get_group(group_id)
        if not group:
            return False

        if name is not None:
            group['name'] = name
        if color is not None:
            group['color'] = color
        if expanded is not None:
            group['expanded'] = expanded

        self.save()
        return True

    def delete_group(self, group_id: str, move_files_to: Optional[str] = None) -> bool:
        """
        删除分组

        Args:
            group_id: 要删除的分组ID
            move_files_to: 将文件移动到的目标分组ID，None则删除文件

        Returns:
            是否成功
        """
        groups = self._data.get('groups', [])

        # 不能删除最后一个分组
        if len(groups) <= 1:
            return False

        group = self.get_group(group_id)
        if not group:
            return False

        # 移动文件到其他分组
        if move_files_to and group.get('files'):
            target_group = self.get_group(move_files_to)
            if target_group:
                target_group['files'].extend(group['files'])

        # 删除分组
        self._data['groups'] = [g for g in groups if g.get('id') != group_id]
        self.save()
        return True

    # ==================== 文件管理 ====================

    def get_all_files(self) -> List[Dict[str, Any]]:
        """获取所有文件（包含分组信息）"""
        all_files = []
        for group in self._data.get('groups', []):
            for file in group.get('files', []):
                file_copy = file.copy()
                file_copy['group_id'] = group['id']
                file_copy['group_name'] = group['name']
                all_files.append(file_copy)
        return all_files

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文件"""
        for group in self._data.get('groups', []):
            for file in group.get('files', []):
                if file.get('id') == file_id:
                    return file
        return None

    def find_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """根据路径查找文件"""
        normalized_path = os.path.normpath(path)
        for group in self._data.get('groups', []):
            for file in group.get('files', []):
                if os.path.normpath(file.get('path', '')) == normalized_path:
                    return file
        return None

    def add_file(self, path: str, group_id: Optional[str] = None,
                 alias: Optional[str] = None) -> Optional[str]:
        """
        添加文件到分组

        Args:
            path: 文件路径
            group_id: 目标分组ID，None则添加到第一个分组
            alias: 文件别名

        Returns:
            新文件的ID，失败返回None
        """
        # 检查文件是否已存在
        if self.find_file_by_path(path):
            print(f"⚠️  文件已存在: {path}")
            return None

        # 确定目标分组
        if group_id:
            group = self.get_group(group_id)
        else:
            groups = self._data.get('groups', [])
            group = groups[0] if groups else None

        if not group:
            return None

        # 创建文件记录
        file_id = str(uuid.uuid4())
        file_name = Path(path).name
        new_file = {
            "id": file_id,
            "path": path,
            "alias": alias or file_name,
            "default_target": "",
            "last_run": None,
            "last_status": None,
            "run_count": 0
        }

        group['files'].append(new_file)

        # 添加到最近文件
        self._add_to_recent(path)

        self.save()
        return file_id

    def update_file(self, file_id: str, alias: Optional[str] = None,
                    default_target: Optional[str] = None,
                    last_run: Optional[str] = None,
                    last_status: Optional[str] = None) -> bool:
        """更新文件信息"""
        file = self.get_file(file_id)
        if not file:
            return False

        if alias is not None:
            file['alias'] = alias
        if default_target is not None:
            file['default_target'] = default_target
        if last_run is not None:
            file['last_run'] = last_run
        if last_status is not None:
            file['last_status'] = last_status
            if last_status in ['success', 'failure']:
                file['run_count'] = file.get('run_count', 0) + 1

        self.save()
        return True

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        for group in self._data.get('groups', []):
            files = group.get('files', [])
            for i, file in enumerate(files):
                if file.get('id') == file_id:
                    files.pop(i)
                    self.save()
                    return True
        return False

    def move_file(self, file_id: str, target_group_id: str,
                  target_index: Optional[int] = None) -> bool:
        """移动文件到其他分组或在分组内重新排序"""
        file_data = None
        current_group_id = None
        current_index = None

        for group in self._data.get('groups', []):
            files = group.get('files', [])
            for i, file in enumerate(files):
                if file.get('id') == file_id:
                    file_data = files.pop(i)
                    current_group_id = group.get('id')
                    current_index = i
                    break
            if file_data:
                break

        if not file_data:
            return False

        target_group = self.get_group(target_group_id)
        if not target_group:
            return False

        if target_index is None:
            target_index = len(target_group.get('files', []))

        if target_index < 0:
            target_index = 0

        if current_group_id == target_group_id and current_index is not None:
            if target_index > current_index:
                target_index -= 1

        files = target_group.get('files', [])
        if target_index > len(files):
            target_index = len(files)

        files.insert(target_index, file_data)
        self.save()
        return True

    # ==================== 最近文件 ====================

    def _add_to_recent(self, path: str, max_recent: int = 10) -> None:
        """添加到最近文件列表"""
        recent = self._data.get('recent_files', [])

        # 如果已存在，先移除
        if path in recent:
            recent.remove(path)

        # 添加到开头
        recent.insert(0, path)

        # 限制数量
        self._data['recent_files'] = recent[:max_recent]

    def get_recent_files(self) -> List[str]:
        """获取最近文件列表"""
        return self._data.get('recent_files', [])

    # ==================== 设置管理 ====================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置项"""
        return self._data.get('settings', {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """设置设置项"""
        if 'settings' not in self._data:
            self._data['settings'] = {}
        self._data['settings'][key] = value
        self.save()

    # ==================== 构建记录 ====================

    def record_build(self, file_id: str, success: bool) -> None:
        """记录构建结果"""
        self.update_file(
            file_id,
            last_run=datetime.now().isoformat(),
            last_status="success" if success else "failure"
        )

    @property
    def config_file(self) -> str:
        """获取配置文件路径"""
        return self._config_file


# 全局实例
_workspace_config: Optional[WorkspaceConfig] = None


def get_workspace_config() -> WorkspaceConfig:
    """获取全局工作区配置实例"""
    global _workspace_config
    if _workspace_config is None:
        _workspace_config = WorkspaceConfig()
    return _workspace_config


if __name__ == "__main__":
    # 测试工作区配置
    config = WorkspaceConfig()
    print("📋 工作区配置测试:")
    print(f"配置文件: {config.config_file}")
    print(f"分组数量: {len(config.get_groups())}")
    print(f"文件数量: {len(config.get_all_files())}")
