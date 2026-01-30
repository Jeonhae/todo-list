from typing import List, Dict, Any, Optional
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QFont


class TaskTableModel(QAbstractTableModel):
    HEADERS = ["任务", "状态", "优先级", "截止日"]

    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, title_font: Optional[QFont] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._title_font = title_font or QFont()

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
                return "已完成" if row.get("done") else "未完成"
            if c == 2:
                return str(row.get("priority", 0))
            if c == 3:
                dd = row.get("due_date")
                return dd.strftime('%Y-%m-%d') if dd else ""
        if role == Qt.TextAlignmentRole:
            # center-align status, priority and due-date columns
            if c in (1, 2, 3):
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
