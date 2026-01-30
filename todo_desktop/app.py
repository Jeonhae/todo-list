import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import qInstallMessageHandler


# 安装一个简单的 Qt 日志处理器以过滤掉已知的无害启动消息（例如 "Can't find filter element"），
# 这样启动时不会在控制台打印这些噪声信息。
def _qt_msg_handler(mode, context, message):
    try:
        if "Can't find filter element" in message:
            return
    except Exception:
        pass
    try:
        sys.stderr.write(str(message) + "\n")
    except Exception:
        pass


qInstallMessageHandler(_qt_msg_handler)
from .models import init_db  # noqa: E402
from .ui.main_window import MainWindow  # noqa: E402


def main():
    db_path = os.path.join(os.getcwd(), "todo_desktop.db")
    init_db(db_path)

    app = QApplication(sys.argv)

    # 使用系统默认的无衬线/通用界面字体（Qt 会返回平台推荐的 UI 字体）
    try:
        sys_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        app.setFont(sys_font)
    except Exception:
        pass

    w = MainWindow(db_path=db_path)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
