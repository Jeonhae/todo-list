from typing import List, Dict, Any, Optional
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QFont


class TaskTableModel(QAbstractTableModel):
    # default language is Chinese; MainWindow may call set_language to change
    HEADERS = ["任务", "状态", "优先级", "截止日", "用时"]

    _LOCALE = {
        "zh": {
            "HEADERS": ["任务", "状态", "优先级", "截止日", "用时"],
            "DONE": "已完成",
            "TODO": "未完成",
        },
        "en": {
            "HEADERS": ["Task", "Status", "Priority", "Due", "Elapsed"],
            "DONE": "Done",
            "TODO": "Pending",
        },
    }

    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, title_font: Optional[QFont] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._title_font = title_font or QFont()
        self._lang = "zh"

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        r = index.row()
        c = index.column()
        row = self._rows[r]
        if role == Qt.DisplayRole:
            if c == 0:
                return row.get("title", "")
            if c == 1:
                return self._LOCALE[self._lang]["DONE"] if row.get("done") else self._LOCALE[self._lang]["TODO"]
            if c == 2:
                return str(row.get("priority", 0))
            if c == 3:
                dd = row.get("due_date")
                return dd.strftime('%Y-%m-%d') if dd else ""
            if c == 4:
                # elapsed seconds -> HH:MM:SS
                secs = row.get("elapsed_seconds", 0) or 0
                try:
                    secs = int(secs)
                except Exception:
                    secs = 0
                h = secs // 3600
                m = (secs % 3600) // 60
                s = secs % 60
                return f"{h:02d}:{m:02d}:{s:02d}"
        if role == Qt.TextAlignmentRole:
            # center-align status, priority, due-date and elapsed columns
            if c in (1, 2, 3, 4):
                return Qt.AlignCenter
        if role == Qt.ToolTipRole:
            notes = row.get("notes")
            return notes or None
        if role == Qt.FontRole and c == 0:
            return self._title_font
        return None

    def headerData(self, section: int, orientation: int, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None

    def set_language(self, lang: str):
        """Set language for headers and status text. Emits headerDataChanged."""
        if lang not in self._LOCALE:
            return
        self._lang = lang
        self.HEADERS = self._LOCALE[lang]["HEADERS"]
        try:
            # notify views that headers changed
            self.headerDataChanged.emit(Qt.Horizontal, 0, len(self.HEADERS) - 1)
        except Exception:
            pass

    def get_done_text(self):
        return self._LOCALE[self._lang]["DONE"]

    def get_todo_text(self):
        return self._LOCALE[self._lang]["TODO"]

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def get_task_id(self, row: int):
        if 0 <= row < len(self._rows):
            return self._rows[row].get("id")
        return None

    def set_title_font(self, font: QFont):
        self._title_font = font
        # notify view that column 0 data (font) changed
        if self.rowCount() > 0:
            top = self.index(0, 0)
            bottom = self.index(self.rowCount() - 1, 0)
            self.dataChanged.emit(top, bottom, [Qt.FontRole])
