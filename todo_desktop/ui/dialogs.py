from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QDialogButtonBox,
    QDateEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("任务")
        self.resize(400, 200)
        self.task = task

        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.prio_spin = QSpinBox()
        self.prio_spin.setRange(0, 10)
        self.due_check = QCheckBox("设置截止日期")
        self.due_check.setChecked(True)
        self.due_edit = QDateEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setDate(QDate.currentDate())

        layout.addRow("标题：", self.title_edit)
        layout.addRow("备注：", self.notes_edit)
        layout.addRow("优先级：", self.prio_spin)
        layout.addRow(self.due_check)
        layout.addRow("截止日期：", self.due_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.due_check.toggled.connect(self.due_edit.setEnabled)

        if task:
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes or "")
            self.prio_spin.setValue(task.priority or 0)
            if task.due_date:
                self.due_check.setChecked(True)
                self.due_edit.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))
            else:
                self.due_check.setChecked(False)
                self.due_edit.setEnabled(False)

    def get_values(self):
        title = self.title_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        priority = self.prio_spin.value()
        if self.due_check.isChecked():
            due_qdate = self.due_edit.date()
            due = datetime(due_qdate.year(), due_qdate.month(), due_qdate.day())
        else:
            due = None
        if not title:
            title = "(未命名)"
        return title, notes, priority, due
