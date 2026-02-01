from PySide6.QtCore import QObject, Signal, QTimer


class PomodoroController(QObject):
    """Simple Pomodoro timer controller.

    Signals:
    - tick(int): emitted every second with remaining seconds
    - finished(str): emitted when a session finishes with the finished mode ('focus' or 'break')
    """

    tick = Signal(int)
    finished = Signal(str)

    def __init__(self, focus_seconds: int = 25 * 60, break_seconds: int = 5 * 60, parent=None):
        super().__init__(parent)
        self.focus_seconds = int(focus_seconds)
        self.break_seconds = int(break_seconds)
        self._mode = 'focus'
        self._remaining = 0
        self._running = False
        self._paused = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timeout)

    def start(self, mode: str = 'focus'):
        self._mode = mode
        self._remaining = int(self.focus_seconds if mode == 'focus' else self.break_seconds)
        self._running = True
        self._paused = False
        self._timer.start()
        self.tick.emit(self._remaining)

    def stop(self):
        self._timer.stop()
        self._running = False
        self._paused = False

    def pause(self):
        if self._running and not self._paused:
            self._timer.stop()
            self._paused = True

    def resume(self):
        if self._running and self._paused:
            self._timer.start()
            self._paused = False

    def is_active(self) -> bool:
        return self._timer.isActive()

    def remaining(self) -> int:
        return int(self._remaining)

    def mode(self) -> str:
        return self._mode

    def _on_timeout(self):
        if not self._running:
            return
        self._remaining = max(0, int(self._remaining) - 1)
        self.tick.emit(self._remaining)
        if self._remaining <= 0:
            # stop and notify
            self._timer.stop()
            self._running = False
            self._paused = False
            self.finished.emit(self._mode)
