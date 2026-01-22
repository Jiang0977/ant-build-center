# Ant Build 中控中心开发任务

## 当前进度
根据 `plan.md` 的实现计划检查进度

### Phase 1: 核心框架
- [x] 实现 `workspace_config.py` 数据持久化
- [x] 实现 `project_manager.py` 文件/分组 CRUD
- [x] 创建 `control_center.py` 主窗口框架

### Phase 2: 文件管理  
- [x] 文件/分组 CRUD 操作 (在 project_manager.py 中)
- [x] 添加文件对话框 + 批量导入（文件夹/粘贴路径）
- [x] 分组管理功能

### Phase 3: 构建集成
- [x] 集成现有 `ant_executor.py`
- [x] 右侧构建详情面板
- [x] 实时输出显示（复用 main.py 的终端样式）
- [x] 构建状态更新

### Phase 4: 增强功能
- [x] 批量构建功能
- [ ] 构建历史记录
- [ ] 设置面板
- [ ] 快捷键支持
