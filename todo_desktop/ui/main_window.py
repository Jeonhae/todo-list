from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QPushButton, QLabel, QMessageBox, QHeaderView, QAbstractItemView, QToolTip, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont, QFontMetrics, QIcon
import os
from pathlib import Path
from .task_model import TaskTableModel

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
        "lang_btn": "中文",
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
        "lang_btn": "EN",
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
        # 初始化计数
        self.total_count = 0
        self.pending_count = 0
        self.completed_count = 0
        central = QWidget()
        self.setCentralWidget(central)
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
        self.lang_btn = QPushButton(self._tr("lang_btn"))
        self.lang_btn.setFixedWidth(64)
        self.lang_btn.setFlat(True)
        self.lang_btn.setToolTip("切换语言 / Switch language")
        self.lang_btn.clicked.connect(self._toggle_language)
        ctrl_layout.addWidget(self.lang_btn)
        ctrl_layout.addWidget(self.font_spin)
        ctrl_layout.addWidget(self.pin_btn)
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

    def _toggle_language(self):
        try:
            self.lang = "en" if self.lang == "zh" else "zh"
            # update model and UI texts
            try:
                self.model.set_language(self.lang)
            except Exception:
                pass
            # update various widgets
            try:
                self.setWindowTitle(self._tr("title"))
                self.add_btn.setText(self._tr("add"))
                self.edit_btn.setText(self._tr("edit"))
                self.del_btn.setText(self._tr("delete"))
                self.pin_btn.setToolTip(self._tr("pin_tooltip"))
                self.font_spin.setToolTip(self._tr("font_tooltip"))
                self.lang_btn.setText(self._tr("lang_btn"))
                # refresh status and table
                self.refresh()
            except Exception:
                pass
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
        except Exception:
            pass

    def mousePressEvent(self, event):
        """Clear selection if user clicks anywhere outside the task table."""
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
