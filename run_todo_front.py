import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# import app components
from todo_desktop.models import init_db
from todo_desktop.ui.main_window import MainWindow
import sqlite3

if __name__ == '__main__':
    db_path = os.path.join(os.getcwd(), 'todo_desktop.db')
    # Ensure DB file has the new column (best-effort migration before SQLAlchemy opens)
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            try:
                cur = conn.cursor()
                try:
                    cur.execute("PRAGMA table_info(tasks)")
                    cols = [r[1] for r in cur.fetchall()]
                    if 'elapsed_seconds' not in cols:
                        try:
                            cur.execute('ALTER TABLE tasks ADD COLUMN elapsed_seconds INTEGER DEFAULT 0 NOT NULL')
                            conn.commit()
                        except Exception:
                            pass
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    except Exception:
        pass
    init_db(db_path)
    app = QApplication(sys.argv)
    w = MainWindow(db_path=db_path)
    try:
        w.setGeometry(100, 100, 900, 600)
        w.show()
        # bring to front
        try:
            w.raise_()
            w.activateWindow()
            w.setWindowState(w.windowState() & ~Qt.WindowMinimized)
            w.showNormal()
        except Exception:
            pass
    except Exception as e:
        print('Failed to show window:', e)
    sys.exit(app.exec())
