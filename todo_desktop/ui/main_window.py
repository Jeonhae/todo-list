from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView, QToolTip, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QCursor, QFont, QFontMetrics, QIcon
from pathlib import Path
from .task_model import TaskTableModel
from .pomodoro import PomodoroController

from .. import models, repository
from .dialogs import TaskDialog

# Simple translation mapping for UI strings
_TRANSLATIONS = {
    "zh": {
        "title": "待办事项",
        "add": "添加",
        "edit": "编辑",
        "delete": "删除",
        "pin_tooltip": "置顶：保持窗口在其他窗口之上",
        "font_tooltip": "界面文字大小",
        
        "select_task": "请先选择一个任务。",
        "not_found": "未找到该任务。",
        "confirm_delete": "确认删除所选任务？",
        "delete_title": "删除",
        "status_fmt": "总任务: {total} | 未完成: {pending} | 已完成: {completed}",
        "done": "已完成",
        "pending": "未完成",
    },
    "en": {
        "title": "Todo List",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "pin_tooltip": "Always on top: keep window above others",
        "font_tooltip": "UI font size",
        
        "select_task": "Please select a task first.",
        "not_found": "Task not found.",
        "confirm_delete": "Confirm delete selected task?",
        "delete_title": "Delete",
        "status_fmt": "Total: {total} | Pending: {pending} | Completed: {completed}",
        "done": "Done",
        "pending": "Pending",
    },
}


class MainWindow(QMainWindow):
    def __init__(self, db_path: str = "todo_desktop.db"):
        super().__init__()
        self.db_path = db_path
        models.init_db(self.db_path)
        # language state: 'zh' or 'en'
        self.lang = "zh"
        self.setWindowTitle(self._tr("title"))
        # apply application/window icon from assets/images/icon_desktop.* if present
        try:
            self._apply_app_icon()
        except Exception:
            pass
        self.resize(600, 400)
        # Use a frameless window so we can embed a custom title bar
        try:
            self.setWindowFlag(Qt.FramelessWindowHint, True)
        except Exception:
            pass
        # resizing support for frameless window
        try:
            self._resizing = False
            self._resize_start = None
            self._start_geom = None
            self._resize_margin = 12
        except Exception:
            pass
        # 初始化计数
        self.total_count = 0
        self.pending_count = 0
        self.completed_count = 0
        central = QWidget()
        self.setCentralWidget(central)
        try:
            # ensure main window and central widget receive mouse move events
            self.setMouseTracking(True)
            central.setMouseTracking(True)
        except Exception:
            pass
        layout = QVBoxLayout(central)

        # 控件
        ctrl_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.del_btn = QPushButton("删除")
        # use translated labels
        self.add_btn.setText(self._tr("add"))
        self.edit_btn.setText(self._tr("edit"))
        self.del_btn.setText(self._tr("delete"))
        ctrl_layout.addWidget(self.add_btn)
        ctrl_layout.addWidget(self.edit_btn)
        ctrl_layout.addWidget(self.del_btn)
        # 图钉按钮：切换窗口置顶
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip(self._tr("pin_tooltip"))
        self.pin_btn.setFlat(True)
        self.pin_btn.setFixedWidth(28)
        # 样式：未选中为灰色，选中时高亮（黄色），并带轻微背景
        self.pin_btn.setStyleSheet(
            "QPushButton{color:gray; background:transparent; border:none; font-size:14px;}"
            "QPushButton:checked{color:#ffb400; background:rgba(255,180,0,0.12); border-radius:4px;}"
        )
        # 在控制区右侧加入伸缩空间并放置字号调整控件及图钉按钮
        # 字号控件
        try:
            default_size = QApplication.font().pointSize()
            if default_size <= 0:
                default_size = 12
        except Exception:
            default_size = 12
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 30)
        self.font_spin.setValue(default_size)
        self.font_spin.setSuffix(" pt")
        self.font_spin.setToolTip(self._tr("font_tooltip"))
        self.font_spin.setFixedWidth(84)
        self.font_spin.valueChanged.connect(self._on_font_size_changed)
        # language toggle button placed to the left of font size control
        ctrl_layout.addStretch()
        # language toggle removed per UI requirement
        ctrl_layout.addWidget(self.font_spin)
        # Create a custom title bar and place it above the control layout.
        try:
            self.title_bar = QWidget()
            self.title_bar.setObjectName("title_bar")
            title_layout = QHBoxLayout(self.title_bar)
            title_layout.setContentsMargins(6, 0, 6, 0)
            title_layout.setSpacing(6)
            # app icon (if available)
            try:
                ico_lbl = QLabel()
                ico_pix = self.windowIcon().pixmap(16, 16)
                ico_lbl.setPixmap(ico_pix)
                title_layout.addWidget(ico_lbl)
            except Exception:
                pass
            # window title
            title_lbl = QLabel(self.windowTitle())
            title_lbl.setObjectName("title_lbl")
            title_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            title_layout.addWidget(title_lbl)
            title_layout.addStretch()
            # place the pin button into the title bar (left of minimize)
            try:
                title_layout.addWidget(self.pin_btn)
            except Exception:
                pass
            # window control buttons
            self.min_btn = QPushButton("▁")
            self.max_btn = QPushButton("▢")
            self.close_btn = QPushButton("✕")
            for b in (self.min_btn, self.max_btn, self.close_btn):
                try:
                    b.setFixedSize(28, 24)
                    b.setFlat(True)
                    b.setFocusPolicy(Qt.NoFocus)
                except Exception:
                    pass
            title_layout.addWidget(self.min_btn)
            title_layout.addWidget(self.max_btn)
            title_layout.addWidget(self.close_btn)
            # insert title bar above controls
            layout.addWidget(self.title_bar)
            # connect control signals
            try:
                self.min_btn.clicked.connect(self.showMinimized)
                self.max_btn.clicked.connect(self._toggle_max_restore)
                self.close_btn.clicked.connect(self.close)
            except Exception:
                pass
            # enable dragging via event filter and ensure central widget events are observed
            try:
                self.title_bar.installEventFilter(self)
                self._titlebar_drag_pos = None
            except Exception:
                pass
            try:
                # install event filter on central widget so we can detect resize drags over its children
                try:
                    self.centralWidget().installEventFilter(self)
                    self.centralWidget().setMouseTracking(True)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            # fallback: if title bar creation fails, continue with control layout only
            pass
        layout.addLayout(ctrl_layout)

        # 任务表格（使用 model/view 以提高大量行时的性能）
        self.table = QTableView()
        self.model = TaskTableModel([])
        # ensure model uses current language for headers/status
        try:
            self.model.set_language(self.lang)
        except Exception:
            pass
        self.table.setModel(self.model)
        # 使用可交互的列宽（用户/程序可调整），并在内容超出时显示水平滚动条
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        try:
            # 减小水平滚动步幅，避免拖动时滚动过快
            sb = self.table.horizontalScrollBar()
            avg = QFontMetrics(self.table.font()).averageCharWidth() or 8
            sb.setSingleStep(max(8, int(avg * 2)))
        except Exception:
            pass
        # 启用单元格文本自动换行，这样可以通过增加行高来完整显示长文本
        try:
            self.table.setWordWrap(True)
        except Exception:
            pass
        # 初始列宽（可根据字体/窗口大小动态调整）
        try:
            self.table.setColumnWidth(0, 300)
            self.table.setColumnWidth(1, 100)
            self.table.setColumnWidth(2, 80)
            self.table.setColumnWidth(3, 120)
        except Exception:
            pass
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        # Place the task table and a right-side panel (`toto_panel`) in a horizontal split
        try:
            content_layout = QHBoxLayout()
            content_layout.addWidget(self.table)
            # Right-side placeholder panel for Pomodoro (toto_panel)
            self.toto_panel = QWidget()
            self.toto_panel.setObjectName("toto_panel")
            # Pomodoro durations (seconds)
            self.focus_seconds = 25 * 60
            self.break_seconds = 5 * 60
            # use a vertical layout inside the panel so future controls stack nicely
            try:
                tp_layout = QVBoxLayout(self.toto_panel)
                tp_layout.setContentsMargins(8, 8, 8, 8)
                tp_layout.setSpacing(12)

                # Top: title
                title_lbl = QLabel("番茄钟")
                title_lbl.setAlignment(Qt.AlignCenter)
                try:
                    # use application/table font to keep consistent UI appearance
                    tf = QFont(self.table.font())
                    tf.setPointSize(max(10, tf.pointSize() + 2))
                    title_lbl.setFont(tf)
                except Exception:
                    pass
                tp_layout.addWidget(title_lbl)

                # Label shown above the orange circle when a pomodoro is started
                try:
                    self.current_task_lbl = QLabel("")
                    self.current_task_lbl.setAlignment(Qt.AlignCenter)
                    self.current_task_lbl.setVisible(False)
                    tp_layout.addWidget(self.current_task_lbl)
                except Exception:
                    pass

                # Middle: orange circular indicator
                try:
                    self.pomodoro_circle = QLabel()
                    self.pomodoro_circle.setFixedSize(120, 120)
                    self.pomodoro_circle.setStyleSheet(
                        "background-color: #ff8c00; border-radius: 60px;"
                    )
                    self.pomodoro_circle.setAlignment(Qt.AlignCenter)
                    try:
                        # larger font for timer display
                        pf = QFont(self.table.font())
                        pf.setPointSize(max(12, pf.pointSize() + 4))
                        self.pomodoro_circle.setFont(pf)
                    except Exception:
                        pass
                    try:
                        # initialize circle text to default focus time
                        self.pomodoro_circle.setText(self._format_time(self.focus_seconds))
                    except Exception:
                        pass
                    tp_layout.addWidget(self.pomodoro_circle, alignment=Qt.AlignHCenter)
                except Exception:
                    # fallback placeholder
                    placeholder = QLabel(self._format_time(self.focus_seconds))
                    placeholder.setAlignment(Qt.AlignCenter)
                    try:
                        placeholder.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    tp_layout.addWidget(placeholder)

                # Focus time row
                try:
                    focus_row = QHBoxLayout()
                    lbl_focus = QLabel("专注时长：")
                    try:
                        lbl_focus.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    focus_row.addWidget(lbl_focus)
                    self.focus_minus = QPushButton("-")
                    self.focus_minus.setFixedWidth(28)
                    self.focus_minus.clicked.connect(lambda: self._change_focus_seconds(-60))
                    focus_row.addWidget(self.focus_minus)
                    self.focus_time_lbl = QLabel(self._format_time(self.focus_seconds))
                    try:
                        self.focus_time_lbl.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    self.focus_time_lbl.setFixedWidth(60)
                    self.focus_time_lbl.setAlignment(Qt.AlignCenter)
                    focus_row.addWidget(self.focus_time_lbl)
                    self.focus_plus = QPushButton("+")
                    self.focus_plus.setFixedWidth(28)
                    self.focus_plus.clicked.connect(lambda: self._change_focus_seconds(60))
                    focus_row.addWidget(self.focus_plus)
                    tp_layout.addLayout(focus_row)
                except Exception:
                    pass

                # Break time row
                try:
                    break_row = QHBoxLayout()
                    lbl_break = QLabel("休息时长：")
                    try:
                        lbl_break.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    break_row.addWidget(lbl_break)
                    self.break_minus = QPushButton("-")
                    self.break_minus.setFixedWidth(28)
                    self.break_minus.clicked.connect(lambda: self._change_break_seconds(-60))
                    break_row.addWidget(self.break_minus)
                    self.break_time_lbl = QLabel(self._format_time(self.break_seconds))
                    try:
                        self.break_time_lbl.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    self.break_time_lbl.setFixedWidth(60)
                    self.break_time_lbl.setAlignment(Qt.AlignCenter)
                    break_row.addWidget(self.break_time_lbl)
                    self.break_plus = QPushButton("+")
                    self.break_plus.setFixedWidth(28)
                    self.break_plus.clicked.connect(lambda: self._change_break_seconds(60))
                    break_row.addWidget(self.break_plus)
                    tp_layout.addLayout(break_row)
                except Exception:
                    pass

                tp_layout.addStretch()

                # Bottom: button container. Initially contains the single Start button (disabled)
                try:
                    self._btn_container = QWidget()
                    btn_layout = QHBoxLayout(self._btn_container)
                    btn_layout.setContentsMargins(0, 0, 0, 0)
                    btn_layout.setSpacing(8)
                    # start button
                    self.start_btn = QPushButton("开始")
                    self.start_btn.setEnabled(False)
                    try:
                        self.start_btn.setFont(QFont(self.table.font()))
                    except Exception:
                        pass
                    self.start_btn.setFixedWidth(100)
                    self.start_btn.clicked.connect(self._on_start_pomodoro)
                    btn_layout.addWidget(self.start_btn)
                    tp_layout.addWidget(self._btn_container, alignment=Qt.AlignHCenter)
                except Exception:
                    pass
            except Exception:
                pass

            # give the panel a reasonable default width
            try:
                self.toto_panel.setFixedWidth(220)
            except Exception:
                pass

            # ensure the orange circle size matches 80% of the panel width
            try:
                if hasattr(self, '_update_pomodoro_circle_size'):
                    self._update_pomodoro_circle_size()
            except Exception:
                pass
            except Exception:
                pass

            # Pomodoro runtime state
            try:
                # use PomodoroController for pomodoro timer behavior
                self._pomodoro_running = False
                self._pomodoro_paused = False
                self._pomodoro_remaining = 0
                self.pomodoro = PomodoroController(self.focus_seconds, self.break_seconds, parent=self)
                # update UI on each tick
                try:
                    self.pomodoro.tick.connect(lambda rem: self.pomodoro_circle.setText(self._format_time(rem)))
                except Exception:
                    pass
                try:
                    self.pomodoro.finished.connect(self._on_pomodoro_finished)
                except Exception:
                    pass
            except Exception:
                pass
            # Task timing runtime state
            try:
                self._timing_task_id = None
                self._timing_elapsed = 0
                self._task_timer = QTimer(self)
                self._task_timer.setInterval(1000)
                self._task_timer.timeout.connect(self._task_tick)
            except Exception:
                pass

            content_layout.addWidget(self.toto_panel)
            layout.addLayout(content_layout)
        except Exception:
            # fallback: add table directly if layout changes fail
            layout.addWidget(self.table)

        # 启用鼠标跟踪以接收 cellEntered 信号，显示任务备注（若有）
        self.table.setMouseTracking(True)
        # when using QTableView, use entered(QModelIndex) to show tooltips
        try:
            self.table.entered.connect(self._on_cell_hover)
        except Exception:
            pass

        # 状态栏
        self.status = QLabel("")
        layout.addWidget(self.status)

        # 连接信号
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn.clicked.connect(self.on_delete)
        self.table.clicked.connect(self.on_status_click)
        self.table.doubleClicked.connect(self.on_edit)

        # 初始时没有选择，编辑/删除不可用
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)
        # 当选择改变时更新按钮状态
        try:
            self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        except Exception:
            pass

        # 连接图钉按钮事件以切换置顶状态
        self.pin_btn.toggled.connect(self._toggle_always_on_top)

        self.refresh()

        # pin button remains in the control layout (original behavior)


    def refresh(self):
        # 在填充表格时禁用排序，避免插入过程中触发重排导致单元格未设置的问题
        self.table.setSortingEnabled(False)
        tasks = repository.list_tasks(show_all=True)
        rows = []
        for t in tasks:
            rows.append({
                "id": t.id,
                "title": t.title,
                "notes": t.notes,
                "done": bool(t.done),
                "priority": t.priority if t.priority is not None else 0,
                "due_date": t.due_date,
                "elapsed_seconds": int(getattr(t, 'elapsed_seconds', 0) or 0),
            })

        # feed model
        try:
            self.model.set_rows(rows)
        except Exception:
            pass

        # update counts and status
        self.total_count = len(rows)
        self.pending_count = len([r for r in rows if not r.get("done")])
        self.completed_count = len([r for r in rows if r.get("done")])
        try:
            self.status.setText(self._tr("status_fmt").format(
                total=self.total_count, pending=self.pending_count, completed=self.completed_count
            ))
        except Exception:
            self.status.setText(f"Total: {self.total_count}")
        try:
            self.table.viewport().update()
        except Exception:
            pass
        # 恢复排序
        self.table.setSortingEnabled(True)
        try:
            self._adjust_table_to_window()
        except Exception:
            pass

    def selected_task_id(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.get_task_id(idx.row())

    def on_add(self):
        dlg = TaskDialog(self)
        if dlg.exec():
            title, notes, priority, due = dlg.get_values()
            repository.add_task(title=title, notes=notes, priority=priority, due_date=due)
            # 增量更新计数
            self.pending_count += 1
            self.total_count += 1
            self.refresh()

    def on_edit(self, _=None):
        tid = self.selected_task_id()
        if not tid:
            QMessageBox.information(self, self._tr("edit"), self._tr("select_task"))
            return
        t = repository.get_task(tid)
        if not t:
            QMessageBox.warning(self, self._tr("edit"), self._tr("not_found"))
            self.refresh()
            return
        dlg = TaskDialog(self, task=t)
        if dlg.exec():
            title, notes, priority, due = dlg.get_values()
            repository.update_task(tid, title=title, notes=notes, priority=priority, due_date=due)
            self.refresh()

    def on_status_click(self, index):
        # index is a QModelIndex when using QTableView
        try:
            if not index.isValid():
                return
            if index.column() != 1:
                return
            row = index.row()
            tid = self.model.get_task_id(row)
            if not tid:
                return
            t = repository.get_task(tid)
            if not t:
                return
            new_done = not t.done
            # if marking done and this task is being timed, stop timer and save elapsed
            try:
                if new_done and getattr(self, '_timing_task_id', None) == tid:
                    try:
                        # stop task timer and persist elapsed
                        if getattr(self, '_task_timer', None) and self._task_timer.isActive():
                            try:
                                self._task_timer.stop()
                            except Exception:
                                pass
                        # save elapsed to repository
                        try:
                            repository.update_task(tid, elapsed_seconds=int(getattr(self, '_timing_elapsed', 0) or 0))
                        except Exception:
                            pass
                        # clear timing state
                        try:
                            self._timing_task_id = None
                            self._timing_elapsed = 0
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
            # also stop any running pomodoro and reset circle when task completes
            try:
                # Stop pomodoro timer if active
                try:
                    if getattr(self, 'pomodoro', None) and self.pomodoro.is_active():
                        try:
                            self.pomodoro.stop()
                        except Exception:
                            pass
                except Exception:
                    pass
                # Reset pomodoro runtime state and UI to initial focus state
                try:
                    self._pomodoro_running = False
                    self._pomodoro_paused = False
                    self._pomodoro_remaining = int(self.focus_seconds)
                    try:
                        self.pomodoro_circle.setText(self._format_time(self._pomodoro_remaining))
                    except Exception:
                        pass
                    # hide current task label (if any) and restore start button
                    try:
                        if hasattr(self, 'current_task_lbl') and self.current_task_lbl is not None:
                            try:
                                self.current_task_lbl.setVisible(False)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        # show only the start button (enabled depending on selection)
                        self._show_start_button()
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass
            repository.set_done(tid, new_done)
            # refresh view (keeps logic simple and correct)
            self.refresh()
        except Exception:
            pass

    def on_delete(self):
        tid = self.selected_task_id()
        if not tid:
            QMessageBox.information(self, self._tr("delete"), self._tr("select_task"))
            return
        t = repository.get_task(tid)
        if not t:
            QMessageBox.warning(self, self._tr("delete"), self._tr("not_found"))
            self.refresh()
            return
        if QMessageBox.question(self, self._tr("delete"), self._tr("confirm_delete")) != QMessageBox.StandardButton.Yes:
            return
        repository.delete_task(tid)
        # 增量更新计数
        self.total_count -= 1
        if t.done:
            self.completed_count -= 1
        else:
            self.pending_count -= 1
        self.refresh()

    def _on_selection_changed(self):
        # 当表格当前选择发生变化时，启用或禁用编辑/删除按钮
        try:
            selected = self.table.selectionModel().selectedRows()
            has = len(selected) > 0
            self.edit_btn.setEnabled(has)
            self.del_btn.setEnabled(has)
            # enable Pomodoro start button only when a single pending task is selected
            try:
                if hasattr(self, 'start_btn'):
                    enabled = False
                    if has:
                        # check selected rows; enable if at least one selected and any selected task is not done
                        for idx in selected:
                            row = idx.row()
                            tid = self.model.get_task_id(row)
                            if not tid:
                                continue
                            t = repository.get_task(tid)
                            if t and not t.done:
                                enabled = True
                                break
                    self.start_btn.setEnabled(enabled)
            except Exception:
                try:
                    self.start_btn.setEnabled(False)
                except Exception:
                    pass
        except Exception:
            try:
                # 保底处理：若出错则禁用按钮
                self.edit_btn.setEnabled(False)
                self.del_btn.setEnabled(False)
            except Exception:
                pass

    def _tr(self, key: str) -> str:
        try:
            return _TRANSLATIONS.get(self.lang, {}).get(key, key)
        except Exception:
            return key

    # language toggle removed; no UI control to change language at runtime

    def _apply_app_icon(self):
        """Look for an icon file named `icon_desktop` with common extensions under assets/images
        and set it as the application/window icon."""
        try:
            # project root: two parents above this file (todo_desktop/ui -> todo_desktop -> project root)
            project_root = Path(__file__).resolve().parents[2]
            icons_dir = project_root / "assets" / "images"
            if not icons_dir.exists():
                return
            for ext in ("png", "ico", "svg", "icns"):
                p = icons_dir / f"icon_desktop.{ext}"
                if p.exists():
                    ico = QIcon(str(p))
                    try:
                        self.setWindowIcon(ico)
                    except Exception:
                        pass
                    try:
                        # Also set application-level icon
                        QApplication.setWindowIcon(ico)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    def _on_font_size_changed(self, size: int):
        """调整应用字体大小（以 point 为单位）并立即生效。"""
        # 仅将字号应用到任务表格，不影响其它界面元素
        try:
            # 基于表格当前字体创建一个副本并修改大小
            new_font = QFont(self.table.font())
            try:
                new_font.setPointSize(int(size))
            except Exception:
                new_font.setPointSize(size)

            # 应用到表格与表头
            try:
                self.table.setFont(new_font)
            except Exception:
                pass
            try:
                self.table.horizontalHeader().setFont(new_font)
            except Exception:
                pass

            # 更新水平滚动步幅以配合新的字体大小
            try:
                sb = self.table.horizontalScrollBar()
                avg = QFontMetrics(new_font).averageCharWidth() or 8
                sb.setSingleStep(max(8, int(avg * 2)))
            except Exception:
                pass

            # 告知 model 使用新的标题字体，并应用到表格/表头
            try:
                self.model.set_title_font(new_font)
            except Exception:
                pass

            # 重新根据标题列字体计算行高和列宽
            try:
                self._adjust_table_to_window(title_font=new_font)
            except Exception:
                pass
        except Exception:
            pass

    def _on_cell_hover(self, index):
        """当鼠标移动到表格的某个单元格时，显示该行任务的备注（如果存在）。"""
        try:
            if not index or not index.isValid():
                QToolTip.hideText()
                return
            # model provides tooltip via ToolTipRole
            notes = self.model.data(index.sibling(index.row(), 0), Qt.ToolTipRole)
            if notes:
                QToolTip.showText(QCursor.pos(), notes, self.table)
            else:
                QToolTip.hideText()
        except Exception:
            try:
                QToolTip.hideText()
            except Exception:
                pass

    def _toggle_always_on_top(self, checked: bool):
        try:
            if checked:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            else:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            # 重新应用并刷新窗口标志
            self.show()
        except Exception:
            pass

    def _on_start_pomodoro(self):
        try:
            tid = self.selected_task_id()
            if not tid:
                QMessageBox.information(self, self._tr("add"), "请先选择一个任务。")
                return
            t = repository.get_task(tid)
            if not t:
                QMessageBox.warning(self, self._tr("add"), "未找到该任务。")
                return
            if t.done:
                QMessageBox.information(self, self._tr("add"), "所选任务已完成。")
                return
            # Start timing the selected task and start the pomodoro countdown.
            try:
                # If another task is being timed, stop it and persist elapsed seconds
                try:
                    prev_tid = getattr(self, '_timing_task_id', None)
                    if prev_tid and prev_tid != tid:
                        try:
                            if getattr(self, '_task_timer', None) and self._task_timer.isActive():
                                try:
                                    self._task_timer.stop()
                                except Exception:
                                    pass
                            # persist the previous elapsed
                            try:
                                repository.update_task(prev_tid, elapsed_seconds=int(getattr(self, '_timing_elapsed', 0) or 0))
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass

                # initialize task timing state for the selected task
                try:
                    self._timing_task_id = tid
                    self._timing_elapsed = int(getattr(t, 'elapsed_seconds', 0) or 0)
                    # show current task label above circle
                    try:
                        if hasattr(self, 'current_task_lbl') and self.current_task_lbl is not None:
                            try:
                                self.current_task_lbl.setText(f"当前任务：{t.title}")
                                self.current_task_lbl.setVisible(True)
                            except Exception:
                                pass
                            try:
                                self._update_pomodoro_circle_size()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # start task timer
                    try:
                        self._task_timer.start()
                    except Exception:
                        pass
                except Exception:
                    pass

                # initialize and start pomodoro countdown (focus mode)
                try:
                    try:
                        self.pomodoro.start('focus')
                        self._pomodoro_running = True
                        self._pomodoro_paused = False
                    except Exception:
                        # fallback: update circle text
                        try:
                            self._pomodoro_remaining = int(self.focus_seconds)
                            self.pomodoro_circle.setText(self._format_time(self._pomodoro_remaining))
                        except Exception:
                            pass
                except Exception:
                    pass

                # update UI buttons to pause/reset
                try:
                    self._show_pause_reset_buttons()
                except Exception:
                    pass
            except Exception:
                QMessageBox.information(self, "番茄钟", f"开始任务计时：{t.title}")
        except Exception:
            try:
                QMessageBox.information(self, "番茄钟", "开始番茄钟")
            except Exception:
                pass

    def _pomodoro_tick(self):
        # removed: legacy method retained for compatibility but no-op
        return

    def _task_tick(self):
        """Increment running task elapsed counter every second and update the table display."""
        try:
            if not getattr(self, '_timing_task_id', None):
                return
            try:
                self._timing_elapsed = int(self._timing_elapsed) + 1
            except Exception:
                try:
                    self._timing_elapsed = int(getattr(self, '_timing_elapsed', 0) or 0)
                    self._timing_elapsed += 1
                except Exception:
                    self._timing_elapsed = 0
            # update model row for the task
            try:
                # find row index with matching id
                for r in range(self.model.rowCount()):
                    tid = self.model.get_task_id(r)
                    if tid == self._timing_task_id:
                        # update underlying rows data and emit change
                        try:
                            # update the internal rows structure
                            if 0 <= r < len(self.model._rows):
                                self.model._rows[r]['elapsed_seconds'] = int(self._timing_elapsed)
                                top = self.model.index(r, 4)
                                bottom = self.model.index(r, 4)
                                try:
                                    self.model.dataChanged.emit(top, bottom, [Qt.DisplayRole])
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        break
            except Exception:
                pass
        except Exception:
            pass

    def _format_time(self, seconds: int) -> str:
        try:
            m = int(seconds) // 60
            s = int(seconds) % 60
            return f"{m:02d}:{s:02d}"
        except Exception:
            return "00:00"

    def _change_focus_seconds(self, delta: int):
        try:
            self.focus_seconds = max(60, self.focus_seconds + int(delta))
            self.focus_time_lbl.setText(self._format_time(self.focus_seconds))
            # if pomodoro not running, update the orange circle to reflect new focus duration
            try:
                if not getattr(self, '_pomodoro_running', False):
                    if hasattr(self, 'pomodoro_circle') and self.pomodoro_circle is not None:
                        self.pomodoro_circle.setText(self._format_time(self.focus_seconds))
            except Exception:
                pass
        except Exception:
            pass

    def _change_break_seconds(self, delta: int):
        try:
            self.break_seconds = max(60, self.break_seconds + int(delta))
            self.break_time_lbl.setText(self._format_time(self.break_seconds))
        except Exception:
            pass

    # Button layout helpers
    def _show_start_button(self):
        try:
            # clear container
            for i in reversed(range(self._btn_container.layout().count())):
                w = self._btn_container.layout().itemAt(i).widget()
                if w:
                    w.setParent(None)
            # add start button
            self.start_btn = QPushButton("开始")
            try:
                self.start_btn.setFont(QFont(self.table.font()))
            except Exception:
                pass
            self.start_btn.setFixedWidth(100)
            self.start_btn.clicked.connect(self._on_start_pomodoro)
            self._btn_container.layout().addWidget(self.start_btn)
            # enable based on selection
            try:
                sel = self.table.selectionModel().selectedRows()
                enabled = False
                for idx in sel:
                    row = idx.row()
                    tid = self.model.get_task_id(row)
                    if not tid:
                        continue
                    t = repository.get_task(tid)
                    if t and not t.done:
                        enabled = True
                        break
                self.start_btn.setEnabled(enabled)
            except Exception:
                try:
                    self.start_btn.setEnabled(True)
                except Exception:
                    pass
        except Exception:
            pass

    def _show_pause_reset_buttons(self):
        try:
            # clear container
            for i in reversed(range(self._btn_container.layout().count())):
                w = self._btn_container.layout().itemAt(i).widget()
                if w:
                    w.setParent(None)
            # pause/resume button (left)
            self.pause_btn = QPushButton("暂停")
            try:
                self.pause_btn.setFont(QFont(self.table.font()))
            except Exception:
                pass
            self.pause_btn.setFixedWidth(100)
            self.pause_btn.clicked.connect(self._on_pause_clicked)
            self._btn_container.layout().addWidget(self.pause_btn)
            # reset button (right)
            self.reset_btn = QPushButton("重置")
            try:
                self.reset_btn.setFont(QFont(self.table.font()))
            except Exception:
                pass
            self.reset_btn.setFixedWidth(100)
            self.reset_btn.clicked.connect(self._on_reset_clicked)
            self._btn_container.layout().addWidget(self.reset_btn)
        except Exception:
            pass

    def _on_pomodoro_finished(self, mode: str):
        """Handle a finished pomodoro session: notify user and switch mode."""
        try:
            if mode == 'focus':
                try:
                    QMessageBox.information(self, '番茄钟', '专注结束，开始休息')
                except Exception:
                    pass
                # start break
                try:
                    if getattr(self, 'pomodoro', None):
                        self.pomodoro.start('break')
                        self._pomodoro_running = True
                        self._pomodoro_paused = False
                except Exception:
                    pass
            else:
                try:
                    QMessageBox.information(self, '番茄钟', '休息结束，开始专注')
                except Exception:
                    pass
                try:
                    if getattr(self, 'pomodoro', None):
                        self.pomodoro.start('focus')
                        self._pomodoro_running = True
                        self._pomodoro_paused = False
                except Exception:
                    pass
        except Exception:
            pass

    def _on_pause_clicked(self):
        try:
            if not self._pomodoro_running:
                return
            if not self._pomodoro_paused:
                # pause
                try:
                    if getattr(self, 'pomodoro', None):
                        try:
                            self.pomodoro.pause()
                        except Exception:
                            pass
                except Exception:
                    pass
                self._pomodoro_paused = True
                try:
                    self.pause_btn.setText("继续")
                except Exception:
                    pass
            else:
                # resume
                try:
                    if getattr(self, 'pomodoro', None):
                        try:
                            self.pomodoro.resume()
                        except Exception:
                            pass
                except Exception:
                    pass
                self._pomodoro_paused = False
                try:
                    self.pause_btn.setText("暂停")
                except Exception:
                    pass
        except Exception:
            pass

    def _on_reset_clicked(self):
        try:
            reply = QMessageBox.question(self, "重置", "重置当前计时？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            # stop timer and reset remaining to focus_seconds
            try:
                if getattr(self, 'pomodoro', None):
                    try:
                        self.pomodoro.stop()
                    except Exception:
                        pass
            except Exception:
                pass
            self._pomodoro_running = False
            self._pomodoro_paused = False
            self._pomodoro_remaining = int(self.focus_seconds)
            try:
                self.pomodoro_circle.setText(self._format_time(self._pomodoro_remaining))
            except Exception:
                pass
            try:
                if hasattr(self, 'current_task_lbl') and self.current_task_lbl is not None:
                    try:
                        self.current_task_lbl.setVisible(False)
                    except Exception:
                        pass
            except Exception:
                pass
            # show start button again (enabled if selection valid)
            try:
                self._show_start_button()
            except Exception:
                pass
        except Exception:
            pass

    def _adjust_table_to_window(self, title_font: QFont = None):
        """根据当前表格视口宽度和字体计算合适的列宽和每行高度。
        如果提供了 title_font，则使用它来计算标题列的行高（支持换行）。
        """
        try:
            viewport_w = max(200, self.table.viewport().width())
            fm = QFontMetrics(self.table.font())
            title_fm = QFontMetrics(title_font) if title_font else fm

            # 右侧固定列估算宽度
            try:
                status_w = max(80, fm.horizontalAdvance('已完成') + 24)
            except Exception:
                status_w = max(80, self.table.columnWidth(1))
            try:
                prio_w = max(60, fm.horizontalAdvance('888') + 24)
            except Exception:
                prio_w = max(60, self.table.columnWidth(2))

            # 截止日列：扫描表中最长的截止日字符串并计算宽度
            try:
                max_due_text = ''
                for r in range(self.model.rowCount()):
                    row = self.model._rows[r]
                    dd = row.get("due_date")
                    txt = ''
                    if dd:
                        try:
                            txt = dd.strftime('%Y-%m-%d')
                        except Exception:
                            txt = str(dd)
                    if len(txt) > len(max_due_text):
                        max_due_text = txt
                if not max_due_text:
                    max_due_text = 'YYYY-MM-DD'
                due_w = max(100, fm.horizontalAdvance(max_due_text) + 24)
            except Exception:
                due_w = max(100, self.table.columnWidth(3))

            padding = 24
            # Default title width: exactly fit the longest task text using the title font
            try:
                max_title_pixels = 0
                for r in range(self.model.rowCount()):
                    row = self.model._rows[r]
                    text = (row.get("title") or "")
                    pw = title_fm.horizontalAdvance(text)
                    if pw > max_title_pixels:
                        max_title_pixels = pw
                if max_title_pixels <= 0:
                    # fallback to header text width
                    try:
                        hdr0 = self.model.headerData(0, Qt.Horizontal, Qt.DisplayRole) or ''
                        max_title_pixels = title_fm.horizontalAdvance(hdr0)
                    except Exception:
                        max_title_pixels = title_fm.horizontalAdvance('任务')
                # add small padding to account for cell margins
                title_w = max_title_pixels + 24
            except Exception:
                title_w = max(120, viewport_w - (status_w + prio_w + due_w + padding))
            # 应用列宽
            try:
                # 确保列宽至少能容纳表头文字
                hh = self.table.horizontalHeader()
                try:
                    header_fm = QFontMetrics(hh.font())
                except Exception:
                    header_fm = fm
                # 计算表头最小宽度并与内容宽度取最大
                try:
                    hdr0 = self.model.headerData(0, Qt.Horizontal, Qt.DisplayRole) or ''
                except Exception:
                    hdr0 = ''
                hdr0_w = header_fm.horizontalAdvance(hdr0) + 24 if hdr0 else 0
                self.table.setColumnWidth(0, max(title_w, hdr0_w))
            except Exception:
                pass
            try:
                try:
                    hdr1 = self.model.headerData(1, Qt.Horizontal, Qt.DisplayRole) or ''
                except Exception:
                    hdr1 = ''
                hdr1_w = header_fm.horizontalAdvance(hdr1) + 24 if hdr1 else 0
                self.table.setColumnWidth(1, max(status_w, hdr1_w))
            except Exception:
                pass
            try:
                try:
                    hdr2 = self.model.headerData(2, Qt.Horizontal, Qt.DisplayRole) or ''
                except Exception:
                    hdr2 = ''
                hdr2_w = header_fm.horizontalAdvance(hdr2) + 24 if hdr2 else 0
                self.table.setColumnWidth(2, max(prio_w, hdr2_w))
            except Exception:
                pass
            try:
                try:
                    hdr3 = self.model.headerData(3, Qt.Horizontal, Qt.DisplayRole) or ''
                except Exception:
                    hdr3 = ''
                hdr3_w = header_fm.horizontalAdvance(hdr3) + 24 if hdr3 else 0
                self.table.setColumnWidth(3, max(due_w, hdr3_w))
            except Exception:
                pass

            # 确保表头高度足以显示较大字号的文字
            try:
                hh_h_req = header_fm.height() + 12
                try:
                    if hh.height() < hh_h_req:
                        hh.setFixedHeight(hh_h_req)
                except Exception:
                    try:
                        hh.setMinimumHeight(hh_h_req)
                    except Exception:
                        pass
            except Exception:
                pass

            # 为每一行计算所需高度以容纳换行文本（使用 title_fm 来测度标题列）
            default_h = max(fm.height(), title_fm.height()) + 10
            for r in range(self.model.rowCount()):
                try:
                    row = self.model._rows[r]
                    text = (row.get("title") or "")
                    # 计算文字在 title_w 宽度下需要的高度，使用标题字体的度量和换行
                    br = title_fm.boundingRect(0, 0, title_w, 10000, Qt.TextWordWrap, text)
                    needed = br.height() + 12
                    self.table.setRowHeight(r, max(default_h, needed))
                except Exception:
                    try:
                        self.table.setRowHeight(r, default_h)
                    except Exception:
                        pass
        except Exception:
            pass

    # pin button is placed in the control layout; removed custom positioning helper

    def _update_pomodoro_circle_size(self):
        """Set pomodoro circle diameter to 80% of `toto_panel` width."""
        try:
            if not hasattr(self, 'toto_panel') or not hasattr(self, 'pomodoro_circle'):
                return
            panel_w = max(40, int(self.toto_panel.width()))
            diameter = max(40, int(panel_w * 0.8))
            # apply size and adjust stylesheet radius
            try:
                self.pomodoro_circle.setFixedSize(diameter, diameter)
            except Exception:
                pass
            try:
                radius = diameter // 2
                self.pomodoro_circle.setStyleSheet(f"background-color: #ff8c00; border-radius: {radius}px;")
            except Exception:
                pass
            try:
                # set font pixel size to 30% of the circle diameter
                pf = QFont(self.pomodoro_circle.font())
                px = int(diameter * 0.3)
                try:
                    pf.setPixelSize(px)
                except Exception:
                    try:
                        pf.setPointSize(int(px * 0.75))
                    except Exception:
                        pass
                try:
                    self.pomodoro_circle.setFont(pf)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                # adjust the current task label font to 8% of panel width
                if hasattr(self, 'current_task_lbl') and self.current_task_lbl is not None:
                    try:
                        label_font = QFont(self.current_task_lbl.font())
                        lbl_px = max(6, int(panel_w * 0.08))
                        try:
                            label_font.setPixelSize(lbl_px)
                        except Exception:
                            try:
                                label_font.setPointSize(int(lbl_px * 0.75))
                            except Exception:
                                pass
                        try:
                            self.current_task_lbl.setFont(label_font)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def resizeEvent(self, event):
        """在窗口大小改变时重新计算表格列宽与行高，确保内容尽量完整显示。"""
        try:
            super().resizeEvent(event)
        except Exception:
            try:
                QMainWindow.resizeEvent(self, event)
            except Exception:
                pass
        try:
            # 延迟或直接调用调整函数以响应用户拖动改变大小
            self._adjust_table_to_window()
            try:
                self._update_pomodoro_circle_size()
            except Exception:
                pass
            # pin button positioning removed (restored to control layout)
        except Exception:
            pass

    def mousePressEvent(self, event):
        """Clear selection if user clicks anywhere outside the task table."""
        try:
            # start resizing if click in bottom-right corner
            if event.button() == Qt.LeftButton:
                try:
                    p = event.pos()
                    w = self.width()
                    h = self.height()
                    if p.x() >= (w - self._resize_margin) and p.y() >= (h - self._resize_margin):
                        self._resizing = True
                        self._resize_start = event.globalPos()
                        self._start_geom = self.geometry()
                        return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            w = self.childAt(event.pos())
            inside = False
            tmp = w
            while tmp is not None:
                if tmp is self.table:
                    inside = True
                    break
                tmp = tmp.parent()
            if not inside:
                try:
                    sel = self.table.selectionModel()
                    if sel and sel.hasSelection():
                        self.table.clearSelection()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            super().mousePressEvent(event)
        except Exception:
            try:
                QMainWindow.mousePressEvent(self, event)
            except Exception:
                pass

    def mouseMoveEvent(self, event):
        """Handle cursor change and active resizing when dragging bottom-right corner."""
        try:
            if getattr(self, '_resizing', False):
                try:
                    delta = event.globalPos() - self._resize_start
                    new_w = max(100, self._start_geom.width() + delta.x())
                    new_h = max(100, self._start_geom.height() + delta.y())
                    try:
                        self.setGeometry(self._start_geom.x(), self._start_geom.y(), new_w, new_h)
                    except Exception:
                        try:
                            self.resize(new_w, new_h)
                        except Exception:
                            pass
                    return
                except Exception:
                    pass
            # change cursor when near bottom-right corner
            try:
                p = event.pos()
                w = self.width()
                h = self.height()
                if p.x() >= (w - self._resize_margin) and p.y() >= (h - self._resize_margin):
                    try:
                        self.setCursor(Qt.SizeFDiagCursor)
                    except Exception:
                        pass
                else:
                    try:
                        self.unsetCursor()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
        try:
            super().mouseMoveEvent(event)
        except Exception:
            try:
                QMainWindow.mouseMoveEvent(self, event)
            except Exception:
                pass

    def mouseReleaseEvent(self, event):
        try:
            if getattr(self, '_resizing', False):
                try:
                    self._resizing = False
                    self._resize_start = None
                    self._start_geom = None
                    return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            super().mouseReleaseEvent(event)
        except Exception:
            try:
                QMainWindow.mouseReleaseEvent(self, event)
            except Exception:
                pass

    def _toggle_max_restore(self):
        """Toggle between maximized and normal window states."""
        try:
            if self.isMaximized():
                self.showNormal()
                try:
                    self.max_btn.setText("▢")
                except Exception:
                    pass
            else:
                self.showMaximized()
                try:
                    self.max_btn.setText("❐")
                except Exception:
                    pass
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Handle mouse events on the custom title bar for dragging and double-click maximize."""
        try:
            if obj is getattr(self, 'title_bar', None):
                try:
                    if event.type() == QEvent.MouseButtonDblClick:
                        try:
                            self._toggle_max_restore()
                        except Exception:
                            pass
                        return True
                    if event.type() == QEvent.MouseButtonPress and event.buttons() & Qt.LeftButton:
                        try:
                            self._titlebar_drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                        except Exception:
                            self._titlebar_drag_pos = None
                        return True
                    if event.type() == QEvent.MouseMove and getattr(self, '_titlebar_drag_pos', None) is not None and (event.buttons() & Qt.LeftButton):
                        try:
                            newpos = event.globalPos() - self._titlebar_drag_pos
                            self.move(newpos)
                        except Exception:
                            pass
                        return True
                    if event.type() == QEvent.MouseButtonRelease:
                        try:
                            self._titlebar_drag_pos = None
                        except Exception:
                            pass
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        # handle events from central widget and its children to support resizing
        try:
            cw = getattr(self, 'centralWidget', None)
            cwidget = None
            try:
                cwidget = self.centralWidget()
            except Exception:
                cwidget = None
            if cwidget is not None:
                # check if the event originates from centralWidget or its descendant
                tmp = obj
                is_descendant = False
                try:
                    while tmp is not None:
                        if tmp is cwidget:
                            is_descendant = True
                            break
                        tmp = tmp.parent()
                except Exception:
                    is_descendant = False
                if is_descendant:
                    try:
                        # map global position to main window coordinates
                        if hasattr(event, 'globalPos'):
                            g = event.globalPos()
                            local_pt = self.mapFromGlobal(g)
                        else:
                            local_pt = None
                        # Mouse press: start resize if in bottom-right margin
                        if event.type() == QEvent.MouseButtonPress and event.buttons() & Qt.LeftButton:
                            try:
                                if local_pt is not None:
                                    w = self.width()
                                    h = self.height()
                                    if local_pt.x() >= (w - self._resize_margin) and local_pt.y() >= (h - self._resize_margin):
                                        self._resizing = True
                                        self._resize_start = event.globalPos()
                                        self._start_geom = self.geometry()
                                        return True
                            except Exception:
                                pass
                        # Mouse move: perform resizing if active, else update cursor
                        if event.type() == QEvent.MouseMove:
                            try:
                                if getattr(self, '_resizing', False):
                                    delta = event.globalPos() - self._resize_start
                                    new_w = max(100, self._start_geom.width() + delta.x())
                                    new_h = max(100, self._start_geom.height() + delta.y())
                                    try:
                                        self.setGeometry(self._start_geom.x(), self._start_geom.y(), new_w, new_h)
                                    except Exception:
                                        try:
                                            self.resize(new_w, new_h)
                                        except Exception:
                                            pass
                                    return True
                                else:
                                    if local_pt is not None:
                                        w = self.width()
                                        h = self.height()
                                        if local_pt.x() >= (w - self._resize_margin) and local_pt.y() >= (h - self._resize_margin):
                                            try:
                                                self.setCursor(Qt.SizeFDiagCursor)
                                            except Exception:
                                                pass
                                        else:
                                            try:
                                                self.unsetCursor()
                                            except Exception:
                                                pass
                            except Exception:
                                pass
                        # Mouse release: stop resizing
                        if event.type() == QEvent.MouseButtonRelease:
                            try:
                                if getattr(self, '_resizing', False):
                                    self._resizing = False
                                    self._resize_start = None
                                    self._start_geom = None
                                    return True
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            return super().eventFilter(obj, event)
        except Exception:
            return False
