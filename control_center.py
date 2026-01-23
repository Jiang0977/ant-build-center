"""
Ant Build 中控中心主程序

提供多项目/多 build.xml 的管理与构建执行界面。
"""

import threading
import time
from pathlib import Path
from typing import Optional, List

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog

from src.workspace_config import get_workspace_config, WorkspaceConfig
from src.project_manager import get_project_manager, ProjectManager
from src.ant_executor import AntExecutor


class ControlCenterGUI:
    """中控中心主界面"""

    def __init__(self):
        self.config: WorkspaceConfig = get_workspace_config()
        self.manager: ProjectManager = get_project_manager()
        self.executor = AntExecutor()

        self.root = tk.Tk()
        self.root.title("🏗️ Ant Build 中控中心")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        self.root.configure(bg="#F5F5F5")

        self.current_file_id: Optional[str] = None
        self.current_group_id: Optional[str] = None
        self.current_process = None
        self.is_building = False
        self.batch_running = False
        self.batch_cancel_requested = False
        self.drag_data = {"items": [], "x": 0, "y": 0, "dragging": False}
        self.drag_indicator = None  # Floating label for drag feedback
        self.drag_highlight_item = None  # Currently highlighted drop target

        self._setup_ui()
        self.refresh_tree()
        self._update_status_bar()

    # ==================== UI 搭建 ====================

    def _setup_ui(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Button(toolbar, text="+ 添加文件", command=self.add_files_dialog).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text="📂 添加文件夹", command=self.add_folder_dialog).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text="🧾 粘贴路径", command=self.import_paths_dialog).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text="📁 添加分组", command=self.add_group_dialog).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.batch_button = ttk.Button(toolbar, text="▶ 批量构建", command=self.start_batch_build)
        self.batch_button.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="⚙ 设置", command=self.show_settings).pack(
            side=tk.LEFT
        )

        # 主体区域
        body = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left_frame = ttk.Frame(body, width=280)
        right_frame = ttk.Frame(body)
        left_frame.pack_propagate(False)
        body.add(left_frame, weight=0)
        body.add(right_frame, weight=1)

        # 左侧树
        tree_header = ttk.Frame(left_frame)
        tree_header.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(tree_header, text="分组列表", font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Button(tree_header, text="⏷ 全部收起", width=10, command=self.collapse_all_groups).pack(side=tk.RIGHT, padx=(2, 0))
        ttk.Button(tree_header, text="⏶ 全部展开", width=10, command=self.expand_all_groups).pack(side=tk.RIGHT)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<<TreeviewOpen>>", self.on_group_toggle)
        self.tree.bind("<<TreeviewClose>>", self.on_group_toggle)
        self.tree.bind("<ButtonPress-1>", self.on_tree_press, add="+")
        self.tree.bind("<B1-Motion>", self.on_tree_motion, add="+")
        self.tree.bind("<ButtonRelease-1>", self.on_tree_release, add="+")


        # 右侧详情
        detail_frame = ttk.LabelFrame(right_frame, text="构建详情")
        detail_frame.pack(fill=tk.X, padx=4, pady=4)

        self.file_path_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.target_var = tk.StringVar()

        ttk.Label(detail_frame, text="文件:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self.file_path_entry = ttk.Entry(detail_frame, textvariable=self.file_path_var, state="readonly")
        self.file_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=6, pady=4)

        ttk.Label(detail_frame, text="项目:").grid(row=1, column=0, sticky=tk.W, padx=6, pady=4)
        self.project_label = ttk.Label(detail_frame, textvariable=self.project_var)
        self.project_label.grid(row=1, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(detail_frame, text="目标:").grid(row=2, column=0, sticky=tk.W, padx=6, pady=4)
        self.target_combo = ttk.Combobox(detail_frame, textvariable=self.target_var, state="readonly", width=30)
        self.target_combo.grid(row=2, column=1, sticky=tk.W, padx=6, pady=4)

        button_frame = ttk.Frame(detail_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(6, 8))

        self.build_button = ttk.Button(button_frame, text="🚀 开始构建", command=self.start_build, state=tk.DISABLED)
        self.build_button.pack(side=tk.LEFT, padx=(0, 6))
        self.cancel_button = ttk.Button(button_frame, text="❌ 取消", command=self.cancel_build, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT)

        detail_frame.columnconfigure(1, weight=1)

        # 输出区域
        output_frame = ttk.LabelFrame(right_frame, text="实时输出")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        terminal_frame = tk.Frame(output_frame, bg="#2C3E50", relief=tk.RAISED, borderwidth=2)
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        terminal_frame.grid_columnconfigure(0, weight=1)
        terminal_frame.grid_rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(
            terminal_frame,
            height=15,
            wrap=tk.WORD,
            bg="#1E1E1E",
            fg="#00FF41",
            selectbackground="#404040",
            selectforeground="#FFFFFF",
            insertbackground="#00FF41",
            font=("Consolas", 10),
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=0
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
        self._setup_output_tags()

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.context_menu = tk.Menu(self.root, tearoff=0)

    def _setup_output_tags(self) -> None:
        self.output_text.tag_config("normal", foreground="#00FF41")
        self.output_text.tag_config("error", foreground="#FF4757")
        self.output_text.tag_config("warning", foreground="#FFA502")
        self.output_text.tag_config("success", foreground="#2ED573")
        self.output_text.tag_config("info", foreground="#3742FA")
        self.output_text.tag_config("build_target", foreground="#F1C40F", font=("Consolas", 10, "bold"))
        self.output_text.tag_config("command", foreground="#9C88FF", font=("Consolas", 10, "italic"))
        self.output_text.tag_config("timestamp", foreground="#70A1FF")

    # ==================== 树形列表 ====================

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for group in self.config.get_groups():
            group_id = group.get("id")
            group_text = f"📁 {group.get('name')}"
            group_iid = f"group:{group_id}"
            self.tree.insert("", "end", iid=group_iid, text=group_text, open=group.get("expanded", True))

            for file in group.get("files", []):
                file_iid = f"file:{file.get('id')}"
                self.tree.insert(group_iid, "end", iid=file_iid, text=self._format_file_label(file))

    def _format_file_label(self, file_data: dict) -> str:
        status = file_data.get("last_status")
        if status == "success":
            status_prefix = "✅"
        elif status == "failure":
            status_prefix = "❌"
        else:
            status_prefix = "⏺"
        display_name = self._get_display_name(file_data)
        return f"{status_prefix} {display_name}"

    def _update_tree_item(self, file_id: str) -> None:
        item_id = f"file:{file_id}"
        if not self.tree.exists(item_id):
            return
        file_data = self.config.get_file(file_id)
        if not file_data:
            return
        self.tree.item(item_id, text=self._format_file_label(file_data))

    # ==================== 选择与详情 ====================

    def on_tree_select(self, _event=None) -> None:
        item = self.tree.focus()
        if not item:
            return
        if item.startswith("file:"):
            self.current_file_id = item.split(":", 1)[1]
            self.current_group_id = None
            self.load_file_details(self.current_file_id)
        elif item.startswith("group:"):
            self.current_group_id = item.split(":", 1)[1]
            self.current_file_id = None
            self.clear_file_details()

    def on_tree_double_click(self, _event=None) -> None:
        if self.current_file_id:
            self.start_build()

    def on_tree_right_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.context_menu.delete(0, tk.END)

        if item.startswith("group:"):
            group_id = item.split(":", 1)[1]
            self.context_menu.add_command(
                label="添加文件",
                command=lambda: self.add_files_dialog(group_id=group_id)
            )
            self.context_menu.add_command(
                label="重命名分组",
                command=lambda: self.rename_group_dialog(group_id)
            )
            self.context_menu.add_command(
                label="删除分组",
                command=lambda: self.delete_group_dialog(group_id)
            )
        elif item.startswith("file:"):
            file_id = item.split(":", 1)[1]
            self.context_menu.add_command(label="构建", command=self.start_build)
            self.context_menu.add_command(
                label="移除文件",
                command=lambda: self.remove_file_dialog(file_id)
            )

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def on_group_toggle(self, _event=None) -> None:
        item = self.tree.focus()
        if not item or not item.startswith("group:"):
            return
        group_id = item.split(":", 1)[1]
        expanded = bool(self.tree.item(item, "open"))
        self.config.update_group(group_id, expanded=expanded)

    def expand_all_groups(self) -> None:
        """Expand all groups in the tree."""
        for group in self.config.get_groups():
            group_id = group.get("id")
            item_id = f"group:{group_id}"
            if self.tree.exists(item_id):
                self.tree.item(item_id, open=True)
                self.config.update_group(group_id, expanded=True)

    def collapse_all_groups(self) -> None:
        """Collapse all groups in the tree."""
        for group in self.config.get_groups():
            group_id = group.get("id")
            item_id = f"group:{group_id}"
            if self.tree.exists(item_id):
                self.tree.item(item_id, open=False)
                self.config.update_group(group_id, expanded=False)

    def on_tree_press(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if item and item.startswith("file:"):
            # Get all selected file items for multi-drag support
            selected = self.tree.selection()
            file_items = [i for i in selected if i.startswith("file:")]
            # If clicked item is not in selection, use only clicked item
            if item not in selected:
                file_items = [item]
            self.drag_data = {"items": file_items, "x": event.x, "y": event.y, "dragging": False}
        else:
            self.drag_data = {"items": [], "x": 0, "y": 0, "dragging": False}

    def on_tree_motion(self, event) -> None:
        if not self.drag_data.get("items"):
            return
        moved = abs(event.x - self.drag_data["x"]) + abs(event.y - self.drag_data["y"])
        if moved > 5:
            if not self.drag_data["dragging"]:
                self.drag_data["dragging"] = True
                self.tree.config(cursor="hand2")
                # Create floating drag indicator
                self._create_drag_indicator(event)
            else:
                # Update drag indicator position and highlight target
                self._update_drag_indicator(event)

    def _create_drag_indicator(self, event) -> None:
        """Create a floating label showing drag info."""
        if self.drag_indicator:
            self.drag_indicator.destroy()
        
        item_count = len(self.drag_data["items"])
        if item_count == 1:
            # Get file name for single item
            item_id = self.drag_data["items"][0]
            file_id = item_id.split(":", 1)[1]
            file_data = self.config.get_file(file_id)
            text = f"📄 {self._get_display_name(file_data)}" if file_data else "📄 1 个文件"
        else:
            text = f"📄 {item_count} 个文件"
        
        self.drag_indicator = tk.Toplevel(self.root)
        self.drag_indicator.overrideredirect(True)  # Remove window decorations
        self.drag_indicator.attributes("-topmost", True)
        self.drag_indicator.attributes("-alpha", 0.85)
        
        label = tk.Label(
            self.drag_indicator,
            text=text,
            bg="#3498DB",
            fg="white",
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=5,
            relief=tk.RAISED,
            borderwidth=1
        )
        label.pack()
        
        # Position near cursor
        x = self.root.winfo_pointerx() + 15
        y = self.root.winfo_pointery() + 15
        self.drag_indicator.geometry(f"+{x}+{y}")

    def _update_drag_indicator(self, event) -> None:
        """Update drag indicator position and highlight drop target."""
        if self.drag_indicator:
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 15
            self.drag_indicator.geometry(f"+{x}+{y}")
        
        # Highlight potential drop target
        target_item = self.tree.identify_row(event.y)
        
        # Clear previous highlight
        if self.drag_highlight_item and self.drag_highlight_item != target_item:
            try:
                if self.tree.exists(self.drag_highlight_item):
                    self.tree.tag_configure("drag_highlight", background="")
                    current_tags = list(self.tree.item(self.drag_highlight_item, "tags") or ())
                    if "drag_highlight" in current_tags:
                        current_tags.remove("drag_highlight")
                        self.tree.item(self.drag_highlight_item, tags=current_tags)
            except Exception:
                pass
            self.drag_highlight_item = None
        
        # Apply highlight to new target (only groups or files not in selection)
        if target_item and target_item not in self.drag_data["items"]:
            if target_item.startswith("group:"):
                self.tree.tag_configure("drag_highlight", background="#D5F5E3")
            else:
                self.tree.tag_configure("drag_highlight", background="#FCF3CF")
            
            current_tags = list(self.tree.item(target_item, "tags") or ())
            if "drag_highlight" not in current_tags:
                current_tags.append("drag_highlight")
                self.tree.item(target_item, tags=current_tags)
            self.drag_highlight_item = target_item

    def _cleanup_drag_ui(self) -> None:
        """Clean up drag indicator and highlights."""
        if self.drag_indicator:
            self.drag_indicator.destroy()
            self.drag_indicator = None
        
        if self.drag_highlight_item:
            try:
                if self.tree.exists(self.drag_highlight_item):
                    current_tags = list(self.tree.item(self.drag_highlight_item, "tags") or ())
                    if "drag_highlight" in current_tags:
                        current_tags.remove("drag_highlight")
                        self.tree.item(self.drag_highlight_item, tags=current_tags)
            except Exception:
                pass
            self.drag_highlight_item = None
        
        self.tree.config(cursor="")

    def on_tree_release(self, event) -> None:
        # Clean up drag UI
        self._cleanup_drag_ui()
        
        if not self.drag_data.get("dragging"):
            self.drag_data = {"items": [], "x": 0, "y": 0, "dragging": False}
            return
        
        source_items = self.drag_data.get("items", [])
        self.drag_data = {"items": [], "x": 0, "y": 0, "dragging": False}
        
        # Filter to only file items
        source_items = [i for i in source_items if i.startswith("file:")]
        if not source_items:
            return

        target_item = self.tree.identify_row(event.y)
        if not target_item or target_item in source_items:
            return

        self._move_files_by_drag(source_items, target_item, event.y)

    def _move_files_by_drag(self, source_items: List[str], target_item: str, y: int) -> None:
        """Move multiple files by drag. Supports multi-selection."""
        target_group_id = None
        target_index = None

        if target_item.startswith("group:"):
            target_group_id = target_item.split(":", 1)[1]
            target_index = len(self._get_group_files(target_group_id))
        elif target_item.startswith("file:"):
            target_file_id = target_item.split(":", 1)[1]
            target_group_id = self._find_group_id_by_file(target_file_id)
            if not target_group_id:
                return
            target_index = self._get_file_index_in_group(target_group_id, target_file_id)
            if target_index is None:
                return
            bbox = self.tree.bbox(target_item)
            if bbox:
                mid_y = bbox[1] + bbox[3] / 2
                if y > mid_y:
                    target_index += 1

        if not target_group_id:
            return

        # Move all selected files
        moved_file_ids = []
        for source_item in source_items:
            source_file_id = source_item.split(":", 1)[1]
            moved = self.manager.move_file_to_group(source_file_id, target_group_id, target_index)
            if moved:
                moved_file_ids.append(source_file_id)
                if target_index is not None:
                    target_index += 1  # Adjust index for next file
        
        if not moved_file_ids:
            return
        
        self.refresh_tree()
        # Reselect all moved files
        for file_id in moved_file_ids:
            item_id = f"file:{file_id}"
            if self.tree.exists(item_id):
                self.tree.selection_add(item_id)
        # Focus first moved item
        if moved_file_ids:
            first_item = f"file:{moved_file_ids[0]}"
            if self.tree.exists(first_item):
                self.tree.focus(first_item)
        self._update_status_bar()

    def on_file_drop(self, event) -> Optional[str]:
        paths = self._parse_dnd_files(event.data)
        if not paths:
            return event.action

        self._handle_drop_paths(paths, event.x_root, event.y_root)
        return event.action

    def _parse_input_paths(self, data: str) -> List[str]:
        if not data:
            return []
        paths: List[str] = []
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [line]
            if ";" in line:
                parts = [p.strip() for p in line.split(";") if p.strip()]
            for part in parts:
                cleaned = part.strip().strip('"').strip("'")
                if cleaned:
                    paths.append(cleaned)

        seen = set()
        unique_paths = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        return unique_paths

    def _get_group_files(self, group_id: str) -> List[dict]:
        group = self.config.get_group(group_id)
        if not group:
            return []
        return group.get("files", [])

    def _get_file_index_in_group(self, group_id: str, file_id: str) -> Optional[int]:
        group = self.config.get_group(group_id)
        if not group:
            return None
        for i, file in enumerate(group.get("files", [])):
            if file.get("id") == file_id:
                return i
        return None

    def _get_display_name(self, file_data: dict) -> str:
        path = file_data.get("path", "")
        if path:
            return Path(path).name
        return file_data.get("alias") or ""

    def _reselect_item(self, item_id: str) -> None:
        if self.tree.exists(item_id):
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)

    def load_file_details(self, file_id: str) -> None:
        file_data = self.config.get_file(file_id)
        if not file_data:
            self.clear_file_details()
            return

        path = file_data.get("path", "")
        info = self.manager.get_file_info(path)
        self.file_path_var.set(path)
        self.project_var.set(info.get("project_name") or self._get_display_name(file_data))

        targets = info.get("targets") or []
        options = ["(使用默认目标)"] + targets if targets else ["(使用默认目标)"]
        self.target_combo["values"] = options
        self.target_combo.set(options[0])

        if info.get("default_target") and not file_data.get("default_target"):
            self.config.update_file(file_id, default_target=info.get("default_target"))

        self.build_button.config(state=tk.NORMAL if not self.is_building else tk.DISABLED)

    def clear_file_details(self) -> None:
        self.file_path_var.set("")
        self.project_var.set("")
        self.target_combo["values"] = []
        self.target_var.set("")
        self.build_button.config(state=tk.DISABLED)

    # ==================== 文件/分组管理 ====================

    def add_files_dialog(self, group_id: Optional[str] = None) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 Ant 构建文件",
            filetypes=[("XML 文件", "*.xml"), ("全部文件", "*.*")]
        )
        if not paths:
            return

        target_group = group_id or self._get_selected_group_id()
        result = self.manager.add_files(list(paths), group_id=target_group)
        self.refresh_tree()
        self._update_status_bar()

        added = len(result.get("added", []))
        invalid = len(result.get("invalid", []))
        skipped = len(result.get("skipped", []))
        messagebox.showinfo(
            "添加结果",
            f"成功添加: {added}\n无效文件: {invalid}\n已存在: {skipped}"
        )

    def add_folder_dialog(self, group_id: Optional[str] = None) -> None:
        folder = filedialog.askdirectory(title="选择包含 XML 的文件夹")
        if not folder:
            return
        xml_paths = [str(p) for p in Path(folder).rglob("*.xml")]
        if not xml_paths:
            messagebox.showinfo("添加结果", "未找到任何 XML 文件。")
            return

        target_group = group_id or self._get_selected_group_id()
        result = self.manager.add_files(xml_paths, group_id=target_group)
        self.refresh_tree()
        self._update_status_bar()

        added = len(result.get("added", []))
        invalid = len(result.get("invalid", []))
        skipped = len(result.get("skipped", []))
        messagebox.showinfo(
            "添加结果",
            f"扫描到 {len(xml_paths)} 个 XML\n成功添加: {added}\n无效文件: {invalid}\n已存在: {skipped}"
        )

    def import_paths_dialog(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("批量导入路径")
        top.geometry("560x360")
        top.transient(self.root)
        top.grab_set()

        frame = ttk.Frame(top, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        target_group = self._get_selected_group_id()
        target_name = "未指定分组"
        if target_group:
            group = self.config.get_group(target_group)
            if group:
                target_name = group.get("name") or target_name

        ttk.Label(frame, text=f"目标分组: {target_name}").pack(anchor=tk.W)
        ttk.Label(frame, text="每行一个路径，可粘贴多行，仅导入 XML 文件。").pack(anchor=tk.W, pady=(6, 4))

        text = scrolledtext.ScrolledText(frame, height=12, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(8, 0))

        def do_import():
            raw = text.get("1.0", tk.END)
            paths = self._parse_input_paths(raw)
            if not paths:
                messagebox.showwarning("提示", "未检测到有效路径。")
                return

            result = self.manager.add_files(paths, group_id=target_group)
            self.refresh_tree()
            self._update_status_bar()

            added = len(result.get("added", []))
            invalid = len(result.get("invalid", []))
            skipped = len(result.get("skipped", []))
            messagebox.showinfo(
                "导入结果",
                f"成功添加: {added}\n无效文件: {invalid}\n已存在: {skipped}"
            )
            top.destroy()

        ttk.Button(button_frame, text="导入", command=do_import).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(button_frame, text="取消", command=top.destroy).pack(side=tk.RIGHT)

    def add_group_dialog(self) -> None:
        name = simpledialog.askstring("添加分组", "分组名称:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self.manager.create_group(name)
        self.refresh_tree()
        self._update_status_bar()

    def rename_group_dialog(self, group_id: str) -> None:
        group = self.config.get_group(group_id)
        if not group:
            return
        name = simpledialog.askstring("重命名分组", "新分组名称:", initialvalue=group.get("name"))
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self.manager.rename_group(group_id, name)
        self.refresh_tree()
        self._update_status_bar()

    def delete_group_dialog(self, group_id: str) -> None:
        group = self.config.get_group(group_id)
        if not group:
            return
        result = messagebox.askyesno(
            "删除分组",
            f"确定删除分组“{group.get('name')}”吗？\n分组内文件将移动到其他分组。"
        )
        if not result:
            return
        if not self.manager.delete_group(group_id):
            messagebox.showwarning("删除失败", "无法删除该分组（可能是最后一个分组）。")
            return
        self.refresh_tree()
        self._update_status_bar()

    def remove_file_dialog(self, file_id: str) -> None:
        file_data = self.config.get_file(file_id)
        if not file_data:
            return
        result = messagebox.askyesno(
            "移除文件",
            f"确定移除文件“{self._get_display_name(file_data)}”吗？\n文件不会被删除。"
        )
        if not result:
            return
        self.manager.remove_file(file_id)
        self.refresh_tree()
        self._update_status_bar()
        self.clear_file_details()

    # ==================== 构建执行 ====================

    def start_build(self) -> None:
        if self.is_building:
            return
        file_id = self.current_file_id
        if not file_id:
            messagebox.showwarning("提示", "请先选择一个构建文件。")
            return

        file_data = self.config.get_file(file_id)
        if not file_data:
            return

        path = file_data.get("path")
        if not path or not Path(path).exists():
            messagebox.showerror("错误", f"文件不存在: {path}")
            return

        valid, msg = self.executor.validate_environment()
        if not valid:
            messagebox.showerror("环境验证失败", msg)
            return

        target = self.target_var.get()
        if target == "(使用默认目标)":
            target = ""

        self._enter_build_state(single=True)
        self._reset_output(f"🚀 开始构建: {self._get_display_name(file_data)}\n")
        self.append_output(f"📂 工作目录: {Path(path).parent}\n")
        self.append_output(f"⏰ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        thread = threading.Thread(target=self._run_build_thread, args=(file_id, target))
        thread.daemon = True
        thread.start()

    def _run_build_thread(self, file_id: str, target: str) -> None:
        try:
            def output_callback(line: str, is_error: bool):
                self.append_output(line, is_error)

            def process_callback(process):
                self.current_process = process

            file_data = self.config.get_file(file_id)
            if not file_data:
                self.root.after(0, self._exit_build_state)
                return

            path = file_data.get("path")
            success, execution_time = self.executor.execute_ant_command_realtime(
                path, target, output_callback, process_callback
            )

            self.root.after(0, self._build_completed, file_id, success, execution_time)
        except Exception as e:
            self.root.after(0, self._build_error, str(e))

    def _build_completed(self, file_id: str, success: bool, execution_time: float) -> None:
        self.config.record_build(file_id, success)
        self._update_tree_item(file_id)
        self._update_status_bar()

        if success:
            self.status_var.set(f"✅ 构建成功! 耗时: {execution_time:.2f}秒")
        else:
            self.status_var.set("❌ 构建失败")

        self._exit_build_state()

    def _build_error(self, error_msg: str) -> None:
        self.append_output(f"❌ 构建过程中发生错误: {error_msg}\n", True)
        self.status_var.set("❌ 构建过程中发生错误")
        self._exit_build_state()

    def cancel_build(self) -> None:
        if not self.is_building:
            return
        self.batch_cancel_requested = True

        if self.current_process:
            try:
                self.append_output("\n⚠️ 用户请求取消构建...\n", True)
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=5)
                except Exception:
                    self.current_process.kill()
                    self.append_output("❌ 强制终止构建进程\n", True)
            except Exception as e:
                self.append_output(f"❌ 取消构建失败: {e}\n", True)

        self.status_var.set("❌ 构建已取消")
        self._exit_build_state()

    # ==================== 批量构建 ====================

    def start_batch_build(self) -> None:
        if self.is_building:
            return

        group_id = self._get_selected_group_id()
        if not group_id:
            messagebox.showwarning("提示", "请先选择一个分组进行批量构建。")
            return

        group = self.config.get_group(group_id)
        if not group or not group.get("files"):
            messagebox.showwarning("提示", "该分组没有可构建文件。")
            return

        if self.config.get_setting("confirm_before_batch", True):
            result = messagebox.askyesno(
                "确认批量构建",
                f"确定开始批量构建分组“{group.get('name')}”吗？"
            )
            if not result:
                return

        valid, msg = self.executor.validate_environment()
        if not valid:
            messagebox.showerror("环境验证失败", msg)
            return

        self.batch_running = True
        self.batch_cancel_requested = False
        self._enter_build_state(single=False)
        self._reset_output(f"📦 批量构建开始: {group.get('name')}\n\n")

        file_ids = [f.get("id") for f in group.get("files", []) if f.get("id")]
        thread = threading.Thread(target=self._run_batch_thread, args=(file_ids,))
        thread.daemon = True
        thread.start()

    def _run_batch_thread(self, file_ids: List[str]) -> None:
        total = len(file_ids)
        success_count = 0
        failure_count = 0

        for index, file_id in enumerate(file_ids, start=1):
            if self.batch_cancel_requested:
                self.append_output("\n🛑 批量构建已取消\n", True)
                break

            file_data = self.config.get_file(file_id)
            if not file_data:
                continue

            path = file_data.get("path")
            if not path or not Path(path).exists():
                self.append_output(f"❌ 文件不存在，跳过: {path}\n", True)
                failure_count += 1
                continue

            self.append_output(f"\n==== [{index}/{total}] {self._get_display_name(file_data)} ====\n")

            def output_callback(line: str, is_error: bool):
                self.append_output(line, is_error)

            def process_callback(process):
                self.current_process = process

            success, execution_time = self.executor.execute_ant_command_realtime(
                path, "", output_callback, process_callback
            )
            self.config.record_build(file_id, success)
            self.root.after(0, self._update_tree_item, file_id)

            if success:
                success_count += 1
                self.append_output(
                    f"✅ 完成: {self._get_display_name(file_data)} ({execution_time:.2f}秒)\n"
                )
            else:
                failure_count += 1
                self.append_output(
                    f"❌ 失败: {self._get_display_name(file_data)} ({execution_time:.2f}秒)\n",
                    True
                )

        self.root.after(0, self._batch_completed, success_count, failure_count)

    def _batch_completed(self, success_count: int, failure_count: int) -> None:
        self.batch_running = False
        self._update_status_bar()
        self.append_output(
            f"\n📊 批量构建完成: 成功 {success_count} / 失败 {failure_count}\n"
        )
        self.status_var.set(f"批量构建完成: 成功 {success_count} / 失败 {failure_count}")
        self._exit_build_state()

    # ==================== 输出处理 ====================

    def _reset_output(self, header: str) -> None:
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, header, "info")

    def append_output(self, text: str, is_error: bool = False) -> None:
        def update_gui():
            tag = self._resolve_output_tag(text, is_error)
            self.output_text.insert(tk.END, text, tag)

            if self.config.get_setting("auto_scroll_output", True):
                self.output_text.see(tk.END)

        self.root.after(0, update_gui)

    def _resolve_output_tag(self, text: str, is_error: bool) -> str:
        if is_error:
            return "error"
        lowered = text.lower()
        if any(keyword in lowered for keyword in ["成功", "success", "✅", "build successful", "successful"]):
            return "success"
        if any(keyword in lowered for keyword in ["警告", "warning", "⚠️", "warn"]):
            return "warning"
        if any(keyword in text for keyword in ["🚀 执行", "ant命令", "command:"]):
            return "command"
        if any(keyword in text for keyword in ["📁", "📂", "⏰", "📦"]):
            return "info"
        if any(keyword in text for keyword in [":", "Total time:", "BUILD"]):
            return "build_target"
        if text.strip().startswith("[") and "]" in text:
            return "build_target"
        return "normal"

    # ==================== 状态与辅助 ====================

    def _enter_build_state(self, single: bool = True) -> None:
        self.is_building = True
        self.batch_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.build_button.config(state=tk.DISABLED)
        if single:
            self.status_var.set("正在构建...")
        else:
            self.status_var.set("正在批量构建...")

    def _exit_build_state(self) -> None:
        self.is_building = False
        self.current_process = None
        self.cancel_button.config(state=tk.DISABLED)
        self.batch_button.config(state=tk.NORMAL)

        if self.current_file_id:
            self.build_button.config(state=tk.NORMAL)
        else:
            self.build_button.config(state=tk.DISABLED)

    def _update_status_bar(self) -> None:
        stats = self.manager.get_statistics()
        self.status_var.set(
            f"共 {stats.get('file_count', 0)} 个构建文件 | "
            f"成功 {stats.get('success_count', 0)} | "
            f"失败 {stats.get('failure_count', 0)} | "
            f"未运行 {stats.get('never_run_count', 0)}"
        )

    def _get_selected_group_id(self) -> Optional[str]:
        if self.current_group_id:
            return self.current_group_id
        if self.current_file_id:
            return self._find_group_id_by_file(self.current_file_id)
        return None

    def _find_group_id_by_file(self, file_id: str) -> Optional[str]:
        for group in self.config.get_groups():
            for file in group.get("files", []):
                if file.get("id") == file_id:
                    return group.get("id")
        return None

    def show_settings(self) -> None:
        messagebox.showinfo("设置", "设置面板尚未实现。")

    # ==================== 关闭处理 ====================

    def close_application(self) -> None:
        if self.is_building:
            result = messagebox.askyesno("确认", "构建正在进行中，确定要关闭吗？")
            if not result:
                return
            self.cancel_build()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = ControlCenterGUI()
    app.run()


if __name__ == "__main__":
    main()
