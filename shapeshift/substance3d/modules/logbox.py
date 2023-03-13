import logging

from PySide2.QtWidgets import (
    QPlainTextEdit,
)
from PySide2.QtCore import (
    QObject,
    Signal,
)


plugin_widgets = []


class QPlainTextEditLogger(QObject):
    append = Signal(str)

    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setFixedHeight(100)
        self.widget.setBackgroundVisible(False)
        self.append.connect(self.widget.appendPlainText)


class QLogHandler(logging.Handler):

    def __init__(self, emitter):
        super().__init__()
        self._emitter = emitter

    @property
    def emitter(self):
        return self._emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.append.emit(msg)
