# -*- coding: utf-8 -*-
"""
@Description: PySide6 统一兼容层
@Version: 1.0.0
@Date: 2026-03-22
@Author: AI Assistant
@FilePath: utils/qt_compat.py

统一使用 PySide6，提供与 PyQt6 兼容的别名
"""

# PySide6 核心模块
from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QTimer, QProcess,
    QFileSystemWatcher, QMetaObject, Q_ARG, QMimeData,
    QStandardPaths, QEvent, QPointF, QEasingCurve,
    QObject, QUrl, QSize, QPoint, QRect, QMargins,
    QByteArray, QIODevice, QBuffer, QDir, QFile,
    QSettings, QLocale, QTranslator, QCoreApplication,
    Property, QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QAbstractAnimation,
    QSortFilterProxyModel, QAbstractItemModel, QModelIndex,
    QItemSelectionModel, QItemSelection,
)

from PySide6.QtGui import (
    QFont, QColor, QPalette, QDrag, QShortcut, QKeySequence,
    QPixmap, QIcon, QImage, QPainter, QPen, QBrush,
    QAction, QCursor, QClipboard, QDesktopServices,
    QFontMetrics, QFontDatabase, QTextDocument,
    QMouseEvent, QKeyEvent, QWheelEvent, QResizeEvent,
    QCloseEvent, QShowEvent, QHideEvent, QFocusEvent,
    QPaintEvent, QDragEnterEvent, QDragLeaveEvent,
    QDragMoveEvent, QDropEvent, QContextMenuEvent,
    QPointingDevice, QGuiApplication,
)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QStackedLayout, QStackedWidget, QSplitter,
    QPushButton, QToolButton, QRadioButton, QCheckBox,
    QLabel, QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser,
    QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QProgressBar, QProgressDialog,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTabBar, QToolBar, QStatusBar, QMenuBar,
    QMenu, QMessageBox, QInputDialog, QFileDialog, QColorDialog,
    QFontDialog, QErrorMessage, QDialogButtonBox,
    QScrollArea, QScrollBar, QFrame, QGroupBox,
    QSizePolicy, QSpacerItem, QAbstractItemView,
    QAbstractScrollArea, QAbstractButton, QAbstractSpinBox,
    QStyle, QStyleOption, QStyleOptionButton,
    QCompleter, QSystemTrayIcon, QWhatsThis, QToolTip,
    QDockWidget, QMdiArea, QMdiSubWindow,
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QCalendarWidget, QDateEdit, QTimeEdit, QDateTimeEdit,
    QUndoStack, QUndoCommand, QUndoView,
)

# 网络模块
try:
    from PySide6.QtNetwork import (
        QNetworkAccessManager, QNetworkRequest, QNetworkReply,
        QTcpSocket, QUdpSocket, QHostAddress, QHostInfo,
        QSslConfiguration, QSslSocket,
    )
except ImportError:
    pass

# WebSockets 模块
try:
    from PySide6.QtWebSockets import QWebSocket, QWebSocketServer
except ImportError:
    pass

# SVG 模块
try:
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtSvgWidgets import QSvgWidget
except ImportError:
    pass

# XML 模块
try:
    from PySide6.QtXml import QDomDocument, QDomElement, QDomNode
except ImportError:
    pass

# Test 模块
try:
    from PySide6.QtTest import QTest
except ImportError:
    pass


# PyQt6 兼容别名
pyqtSignal = Signal
pyqtSlot = Slot
pyqtProperty = Property


def get_enum_value(enum_val):
    """
    获取枚举值，兼容 PySide6 和 PyQt6 的枚举差异
    PySide6: Qt.AlignCenter (直接是 int)
    PyQt6: Qt.AlignmentFlag.AlignCenter (需要 .value)
    """
    if hasattr(enum_val, 'value'):
        return enum_val.value
    return enum_val
