# -*- coding: utf-8 -*-
"""
PyQt6/PyQt6 兼容层
使得 Ghost Downloader 可以在 PyQt6 环境中运行

PyQt6 将大部分枚举移到了子枚举类中，如:
- Qt.Orientation.Vertical -> Qt.Orientation.Vertical
- QEasingCurve.OutCubic -> QEasingCurve.Type.OutCubic
- QFont.Normal -> QFont.Weight.Normal

本兼容层通过 __getattr__ 动态处理这些差异
"""
import sys

# 检测当前环境
_USING_PYQT6 = False

def _log(msg):
    """简单日志输出"""
    try:
        from app.common.logger_config import logger
        logger.debug(f"[qt_compat] {msg}")
    except:
        print(f"[qt_compat] {msg}")

def _make_compat_class(original_class, enum_mappings):
    """
    创建兼容类，动态处理枚举访问
    enum_mappings: dict, key是PySide6风格名称，value是(PyQt6枚举类, PyQt6枚举值)
    """
    class CompatClass(original_class):
        def __getattr__(self, name):
            if name in enum_mappings:
                enum_class, enum_attr = enum_mappings[name]
                return getattr(enum_class, enum_attr)
            raise AttributeError(f"{original_class.__name__} has no attribute '{name}'")
    
    # 类属性访问
    original_getattr = None
    if hasattr(original_class, '__getattr__'):
        original_getattr = original_class.__getattr__
    
    def class_getattr(cls, name):
        if name in enum_mappings:
            enum_class, enum_attr = enum_mappings[name]
            return getattr(enum_class, enum_attr)
        if original_getattr:
            return original_getattr(name)
        raise AttributeError(f"{original_class.__name__} has no attribute '{name}'")
    
    # 直接在类上设置属性（更简单的方式）
    for name, (enum_class, enum_attr) in enum_mappings.items():
        try:
            setattr(original_class, name, getattr(enum_class, enum_attr))
        except AttributeError:
            pass
    
    return original_class

try:
    # 尝试导入 PyQt6
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtWidgets import *
    from PyQt6.QtNetwork import *
    _USING_PYQT6 = True
    
    # PyQt6 -> PyQt6 名称兼容
    # PyQt6 使用 pyqtSignal/pyqtSlot/pyqtProperty，PyQt6 使用 pyqtSignal/pyqtSlot/pyqtProperty
    import PyQt6.QtCore as _QtCore
    import PyQt6.QtGui as _QtGui
    
    # 立即添加 Qt 到 QtGui（必须在任何其他代码导入 QtGui.Qt 之前）
    _QtGui.Qt = _QtCore.Qt
    
    _QtCore.pyqtSignal = _QtCore.pyqtSignal
    _QtCore.pyqtSlot = _QtCore.pyqtSlot
    _QtCore.pyqtProperty = _QtCore.pyqtProperty
    
    # 将别名注入到全局命名空间
    pyqtSignal = pyqtSignal
    pyqtSlot = pyqtSlot
    pyqtProperty = pyqtProperty
    
    # ==================== Qt 枚举兼容 ====================
    _QT_ENUM_MAPPINGS = {
        # Orientation
        'Vertical': ('Qt.Orientation', 'Vertical'),
        'Horizontal': ('Qt.Orientation', 'Horizontal'),
        # AlignmentFlag
        'AlignLeft': ('Qt.AlignmentFlag', 'AlignLeft'),
        'AlignRight': ('Qt.AlignmentFlag', 'AlignRight'),
        'AlignHCenter': ('Qt.AlignmentFlag', 'AlignHCenter'),
        'AlignTop': ('Qt.AlignmentFlag', 'AlignTop'),
        'AlignBottom': ('Qt.AlignmentFlag', 'AlignBottom'),
        'AlignVCenter': ('Qt.AlignmentFlag', 'AlignVCenter'),
        'AlignCenter': ('Qt.AlignmentFlag', 'AlignCenter'),
        'AlignJustify': ('Qt.AlignmentFlag', 'AlignJustify'),
        'AlignAbsolute': ('Qt.AlignmentFlag', 'AlignAbsolute'),
        'AlignBaseline': ('Qt.AlignmentFlag', 'AlignBaseline'),
        # FocusPolicy
        'TabFocus': ('Qt.FocusPolicy', 'TabFocus'),
        'ClickFocus': ('Qt.FocusPolicy', 'ClickFocus'),
        'StrongFocus': ('Qt.FocusPolicy', 'StrongFocus'),
        'NoFocus': ('Qt.FocusPolicy', 'NoFocus'),
        'WheelFocus': ('Qt.FocusPolicy', 'WheelFocus'),
        # ScrollBarPolicy
        'ScrollBarAsNeeded': ('Qt.ScrollBarPolicy', 'ScrollBarAsNeeded'),
        'ScrollBarAlwaysOff': ('Qt.ScrollBarPolicy', 'ScrollBarAlwaysOff'),
        'ScrollBarAlwaysOn': ('Qt.ScrollBarPolicy', 'ScrollBarAlwaysOn'),
        # WindowType
        'Window': ('Qt.WindowType', 'Window'),
        'Dialog': ('Qt.WindowType', 'Dialog'),
        'Sheet': ('Qt.WindowType', 'Sheet'),
        'Drawer': ('Qt.WindowType', 'Drawer'),
        'Popup': ('Qt.WindowType', 'Popup'),
        'Tool': ('Qt.WindowType', 'Tool'),
        'ToolTip': ('Qt.WindowType', 'ToolTip'),
        'SplashScreen': ('Qt.WindowType', 'SplashScreen'),
        'SubWindow': ('Qt.WindowType', 'SubWindow'),
        'WindowStaysOnTopHint': ('Qt.WindowType', 'WindowStaysOnTopHint'),
        'FramelessWindowHint': ('Qt.WindowType', 'FramelessWindowHint'),
        # MouseButton
        'LeftButton': ('Qt.MouseButton', 'LeftButton'),
        'RightButton': ('Qt.MouseButton', 'RightButton'),
        'MiddleButton': ('Qt.MouseButton', 'MiddleButton'),
        'BackButton': ('Qt.MouseButton', 'BackButton'),
        'ForwardButton': ('Qt.MouseButton', 'ForwardButton'),
        # KeyboardModifier
        'NoModifier': ('Qt.KeyboardModifier', 'NoModifier'),
        'ShiftModifier': ('Qt.KeyboardModifier', 'ShiftModifier'),
        'ControlModifier': ('Qt.KeyboardModifier', 'ControlModifier'),
        'AltModifier': ('Qt.KeyboardModifier', 'AltModifier'),
        'MetaModifier': ('Qt.KeyboardModifier', 'MetaModifier'),
        'KeypadModifier': ('Qt.KeyboardModifier', 'KeypadModifier'),
        # DropAction
        'CopyAction': ('Qt.DropAction', 'CopyAction'),
        'MoveAction': ('Qt.DropAction', 'MoveAction'),
        'LinkAction': ('Qt.DropAction', 'LinkAction'),
        'ActionMask': ('Qt.DropAction', 'ActionMask'),
        'IgnoreAction': ('Qt.DropAction', 'IgnoreAction'),
        # GlobalColor
        'white': ('Qt.GlobalColor', 'white'),
        'black': ('Qt.GlobalColor', 'black'),
        'red': ('Qt.GlobalColor', 'red'),
        'green': ('Qt.GlobalColor', 'green'),
        'blue': ('Qt.GlobalColor', 'blue'),
        'cyan': ('Qt.GlobalColor', 'cyan'),
        'magenta': ('Qt.GlobalColor', 'magenta'),
        'yellow': ('Qt.GlobalColor', 'yellow'),
        'darkRed': ('Qt.GlobalColor', 'darkRed'),
        'darkGreen': ('Qt.GlobalColor', 'darkGreen'),
        'darkBlue': ('Qt.GlobalColor', 'darkBlue'),
        'darkCyan': ('Qt.GlobalColor', 'darkCyan'),
        'darkMagenta': ('Qt.GlobalColor', 'darkMagenta'),
        'darkYellow': ('Qt.GlobalColor', 'darkYellow'),
        'transparent': ('Qt.GlobalColor', 'transparent'),
        'gray': ('Qt.GlobalColor', 'gray'),
        'darkGray': ('Qt.GlobalColor', 'darkGray'),
        'lightGray': ('Qt.GlobalColor', 'lightGray'),
        # PenStyle
        'NoPen': ('Qt.PenStyle', 'NoPen'),
        'SolidLine': ('Qt.PenStyle', 'SolidLine'),
        'DashLine': ('Qt.PenStyle', 'DashLine'),
        'DotLine': ('Qt.PenStyle', 'DotLine'),
        'DashDotLine': ('Qt.PenStyle', 'DashDotLine'),
        'DashDotDotLine': ('Qt.PenStyle', 'DashDotDotLine'),
        # BrushStyle
        'NoBrush': ('Qt.BrushStyle', 'NoBrush'),
        'SolidPattern': ('Qt.BrushStyle', 'SolidPattern'),
        'Dense1Pattern': ('Qt.BrushStyle', 'Dense1Pattern'),
        'Dense2Pattern': ('Qt.BrushStyle', 'Dense2Pattern'),
        'Dense3Pattern': ('Qt.BrushStyle', 'Dense3Pattern'),
        'Dense4Pattern': ('Qt.BrushStyle', 'Dense4Pattern'),
        'Dense5Pattern': ('Qt.BrushStyle', 'Dense5Pattern'),
        'Dense6Pattern': ('Qt.BrushStyle', 'Dense6Pattern'),
        'Dense7Pattern': ('Qt.BrushStyle', 'Dense7Pattern'),
        'HorPattern': ('Qt.BrushStyle', 'HorPattern'),
        'VerPattern': ('Qt.BrushStyle', 'VerPattern'),
        'CrossPattern': ('Qt.BrushStyle', 'CrossPattern'),
        # SizeHint
        'MinimumSize': ('Qt.SizeHint', 'MinimumSize'),
        'PreferredSize': ('Qt.SizeHint', 'PreferredSize'),
        'MaximumSize': ('Qt.SizeHint', 'MaximumSize'),
        'MinimumDescent': ('Qt.SizeHint', 'MinimumDescent'),
        # ItemDataRole
        'DisplayRole': ('Qt.ItemDataRole', 'DisplayRole'),
        'DecorationRole': ('Qt.ItemDataRole', 'DecorationRole'),
        'EditRole': ('Qt.ItemDataRole', 'EditRole'),
        'ToolTipRole': ('Qt.ItemDataRole', 'ToolTipRole'),
        'StatusTipRole': ('Qt.ItemDataRole', 'StatusTipRole'),
        'WhatsThisRole': ('Qt.ItemDataRole', 'WhatsThisRole'),
        'FontRole': ('Qt.ItemDataRole', 'FontRole'),
        'TextAlignmentRole': ('Qt.ItemDataRole', 'TextAlignmentRole'),
        'BackgroundRole': ('Qt.ItemDataRole', 'BackgroundRole'),
        'ForegroundRole': ('Qt.ItemDataRole', 'ForegroundRole'),
        'CheckStateRole': ('Qt.ItemDataRole', 'CheckStateRole'),
        'SizeHintRole': ('Qt.ItemDataRole', 'SizeHintRole'),
        'UserRole': ('Qt.ItemDataRole', 'UserRole'),
        # ItemFlag
        'NoItemFlags': ('Qt.ItemFlag', 'NoItemFlags'),
        'ItemIsSelectable': ('Qt.ItemFlag', 'ItemIsSelectable'),
        'ItemIsEditable': ('Qt.ItemFlag', 'ItemIsEditable'),
        'ItemIsDragEnabled': ('Qt.ItemFlag', 'ItemIsDragEnabled'),
        'ItemIsDropEnabled': ('Qt.ItemFlag', 'ItemIsDropEnabled'),
        'ItemIsUserCheckable': ('Qt.ItemFlag', 'ItemIsUserCheckable'),
        'ItemIsEnabled': ('Qt.ItemFlag', 'ItemIsEnabled'),
        'ItemIsAutoTristate': ('Qt.ItemFlag', 'ItemIsAutoTristate'),
        # CheckState
        'Unchecked': ('Qt.CheckState', 'Unchecked'),
        'PartiallyChecked': ('Qt.CheckState', 'PartiallyChecked'),
        'Checked': ('Qt.CheckState', 'Checked'),
        # TextFlag
        'TextSingleLine': ('Qt.TextFlag', 'TextSingleLine'),
        # TextDontExpandTabs was removed in Qt6 (use TextExpandTabs instead)
        'TextShowMnemonic': ('Qt.TextFlag', 'TextShowMnemonic'),
        'TextWordWrap': ('Qt.TextFlag', 'TextWordWrap'),
        'TextWrapAnywhere': ('Qt.TextFlag', 'TextWrapAnywhere'),
        'TextDontPrint': ('Qt.TextFlag', 'TextDontPrint'),
        # AspectRatioMode
        'IgnoreAspectRatio': ('Qt.AspectRatioMode', 'IgnoreAspectRatio'),
        'KeepAspectRatio': ('Qt.AspectRatioMode', 'KeepAspectRatio'),
        'KeepAspectRatioByExpanding': ('Qt.AspectRatioMode', 'KeepAspectRatioByExpanding'),
        # TransformationMode
        'SmoothTransformation': ('Qt.TransformationMode', 'SmoothTransformation'),
        'FastTransformation': ('Qt.TransformationMode', 'FastTransformation'),
        # ConnectionType
        'AutoConnection': ('Qt.ConnectionType', 'AutoConnection'),
        'DirectConnection': ('Qt.ConnectionType', 'DirectConnection'),
        'QueuedConnection': ('Qt.ConnectionType', 'QueuedConnection'),
        'BlockingQueuedConnection': ('Qt.ConnectionType', 'BlockingQueuedConnection'),
        'UniqueConnection': ('Qt.ConnectionType', 'UniqueConnection'),
        # WidgetAttribute - 关键！用于对话框透明背景等
        'WA_TranslucentBackground': ('Qt.WidgetAttribute', 'WA_TranslucentBackground'),
        'WA_DeleteOnClose': ('Qt.WidgetAttribute', 'WA_DeleteOnClose'),
        'WA_QuitOnClose': ('Qt.WidgetAttribute', 'WA_QuitOnClose'),
        'WA_ShowWithoutActivating': ('Qt.WidgetAttribute', 'WA_ShowWithoutActivating'),
        'WA_Hover': ('Qt.WidgetAttribute', 'WA_Hover'),
        'WA_InputMethodEnabled': ('Qt.WidgetAttribute', 'WA_InputMethodEnabled'),
        'WA_NoSystemBackground': ('Qt.WidgetAttribute', 'WA_NoSystemBackground'),
        'WA_StyleSheet': ('Qt.WidgetAttribute', 'WA_StyleSheet'),
        'WA_StaticContents': ('Qt.WidgetAttribute', 'WA_StaticContents'),
        'WA_NativeWindow': ('Qt.WidgetAttribute', 'WA_NativeWindow'),
        # WindowState
        'WindowNoState': ('Qt.WindowState', 'WindowNoState'),
        'WindowMinimized': ('Qt.WindowState', 'WindowMinimized'),
        'WindowMaximized': ('Qt.WindowState', 'WindowMaximized'),
        'WindowFullScreen': ('Qt.WindowState', 'WindowFullScreen'),
        'WindowActive': ('Qt.WindowState', 'WindowActive'),
    }
    
    # 应用 Qt 枚举映射
    for name, (enum_path, enum_attr) in _QT_ENUM_MAPPINGS.items():
        try:
            parts = enum_path.split('.')
            if parts[0] == 'Qt':
                enum_class = getattr(_QtCore.Qt, parts[1])
                setattr(_QtCore.Qt, name, getattr(enum_class, enum_attr))
        except (AttributeError, IndexError) as e:
            _log(f"映射失败: {name} <- {enum_path}.{enum_attr}: {e}")
    
    _log(f"Qt枚举映射完成，共 {len(_QT_ENUM_MAPPINGS)} 项")
    
    # ==================== QFont 枚举兼容 ====================
    try:
        _QtGui.QFont.Normal = _QtGui.QFont.Weight.Normal
        _QtGui.QFont.Bold = _QtGui.QFont.Weight.Bold
        _QtGui.QFont.Light = _QtGui.QFont.Weight.Light
        _QtGui.QFont.Thin = _QtGui.QFont.Weight.Thin
        _QtGui.QFont.ExtraLight = _QtGui.QFont.Weight.ExtraLight
        _QtGui.QFont.Medium = _QtGui.QFont.Weight.Medium
        _QtGui.QFont.DemiBold = _QtGui.QFont.Weight.DemiBold
        _QtGui.QFont.ExtraBold = _QtGui.QFont.Weight.ExtraBold
        _QtGui.QFont.Black = _QtGui.QFont.Weight.Black
    except AttributeError:
        pass
    
    # ==================== QIcon 枚举兼容 ====================
    try:
        _QtGui.QIcon.Off = _QtGui.QIcon.State.Off
        _QtGui.QIcon.On = _QtGui.QIcon.State.On
        _QtGui.QIcon.Normal = _QtGui.QIcon.Mode.Normal
        _QtGui.QIcon.Disabled = _QtGui.QIcon.Mode.Disabled
        _QtGui.QIcon.Selected = _QtGui.QIcon.Mode.Selected
        _QtGui.QIcon.Active = _QtGui.QIcon.Mode.Active
    except AttributeError:
        pass
    
    # ==================== QEasingCurve 枚举兼容 ====================
    _EASING_MAPPINGS = {
        'Linear': 'Linear',
        'InQuad': 'InQuad', 'OutQuad': 'OutQuad', 'InOutQuad': 'InOutQuad', 'OutInQuad': 'OutInQuad',
        'InCubic': 'InCubic', 'OutCubic': 'OutCubic', 'InOutCubic': 'InOutCubic', 'OutInCubic': 'OutInCubic',
        'InQuart': 'InQuart', 'OutQuart': 'OutQuart', 'InOutQuart': 'InOutQuart', 'OutInQuart': 'OutInQuart',
        'InQuint': 'InQuint', 'OutQuint': 'OutQuint', 'InOutQuint': 'InOutQuint', 'OutInQuint': 'OutInQuint',
        'InSine': 'InSine', 'OutSine': 'OutSine', 'InOutSine': 'InOutSine', 'OutInSine': 'OutInSine',
        'InExpo': 'InExpo', 'OutExpo': 'OutExpo', 'InOutExpo': 'InOutExpo', 'OutInExpo': 'OutInExpo',
        'InCirc': 'InCirc', 'OutCirc': 'OutCirc', 'InOutCirc': 'InOutCirc', 'OutInCirc': 'OutInCirc',
        'InElastic': 'InElastic', 'OutElastic': 'OutElastic', 'InOutElastic': 'InOutElastic', 'OutInElastic': 'OutInElastic',
        'InBack': 'InBack', 'OutBack': 'OutBack', 'InOutBack': 'InOutBack', 'OutInBack': 'OutInBack',
        'InBounce': 'InBounce', 'OutBounce': 'OutBounce', 'InOutBounce': 'InOutBounce', 'OutInBounce': 'OutInBounce',
        'BezierSpline': 'BezierSpline', 'TCBSpline': 'TCBSpline', 'Custom': 'Custom',
    }
    for name, attr in _EASING_MAPPINGS.items():
        try:
            setattr(_QtCore.QEasingCurve, name, getattr(_QtCore.QEasingCurve.Type, attr))
        except AttributeError:
            pass
    
    # ==================== QPalette 枚举兼容 ====================
    try:
        _QtGui.QPalette.Window = _QtGui.QPalette.ColorRole.Window
        _QtGui.QPalette.WindowText = _QtGui.QPalette.ColorRole.WindowText
        _QtGui.QPalette.Base = _QtGui.QPalette.ColorRole.Base
        _QtGui.QPalette.AlternateBase = _QtGui.QPalette.ColorRole.AlternateBase
        _QtGui.QPalette.ToolTipBase = _QtGui.QPalette.ColorRole.ToolTipBase
        _QtGui.QPalette.ToolTipText = _QtGui.QPalette.ColorRole.ToolTipText
        _QtGui.QPalette.Text = _QtGui.QPalette.ColorRole.Text
        _QtGui.QPalette.Button = _QtGui.QPalette.ColorRole.Button
        _QtGui.QPalette.ButtonText = _QtGui.QPalette.ColorRole.ButtonText
        _QtGui.QPalette.BrightText = _QtGui.QPalette.ColorRole.BrightText
        _QtGui.QPalette.Highlight = _QtGui.QPalette.ColorRole.Highlight
        _QtGui.QPalette.HighlightedText = _QtGui.QPalette.ColorRole.HighlightedText
        _QtGui.QPalette.Link = _QtGui.QPalette.ColorRole.Link
        _QtGui.QPalette.PlaceholderText = _QtGui.QPalette.ColorRole.PlaceholderText
        _QtGui.QPalette.Active = _QtGui.QPalette.ColorGroup.Active
        _QtGui.QPalette.Disabled = _QtGui.QPalette.ColorGroup.Disabled
        _QtGui.QPalette.Inactive = _QtGui.QPalette.ColorGroup.Inactive
    except AttributeError:
        pass
    
    # ==================== QPainter 枚举兼容 ====================
    try:
        _QtGui.QPainter.Antialiasing = _QtGui.QPainter.RenderHint.Antialiasing
        _QtGui.QPainter.TextAntialiasing = _QtGui.QPainter.RenderHint.TextAntialiasing
        _QtGui.QPainter.SmoothPixmapTransform = _QtGui.QPainter.RenderHint.SmoothPixmapTransform
        _QtGui.QPainter.HighQualityAntialiasing = _QtGui.QPainter.RenderHint.HighQualityAntialiasing
        _QtGui.QPainter.NonCosmeticDefaultPen = _QtGui.QPainter.RenderHint.NonCosmeticDefaultPen
    except AttributeError:
        pass
    
    # ==================== QStandardPaths 枚举兼容 ====================
    try:
        _QtCore.QStandardPaths.DownloadLocation = _QtCore.QStandardPaths.StandardLocation.DownloadLocation
        _QtCore.QStandardPaths.DocumentsLocation = _QtCore.QStandardPaths.StandardLocation.DocumentsLocation
        _QtCore.QStandardPaths.DesktopLocation = _QtCore.QStandardPaths.StandardLocation.DesktopLocation
        _QtCore.QStandardPaths.HomeLocation = _QtCore.QStandardPaths.StandardLocation.HomeLocation
        _QtCore.QStandardPaths.ApplicationsLocation = _QtCore.QStandardPaths.StandardLocation.ApplicationsLocation
        _QtCore.QStandardPaths.FontsLocation = _QtCore.QStandardPaths.StandardLocation.FontsLocation
        _QtCore.QStandardPaths.MusicLocation = _QtCore.QStandardPaths.StandardLocation.MusicLocation
        _QtCore.QStandardPaths.MoviesLocation = _QtCore.QStandardPaths.StandardLocation.MoviesLocation
        _QtCore.QStandardPaths.PicturesLocation = _QtCore.QStandardPaths.StandardLocation.PicturesLocation
        _QtCore.QStandardPaths.TempLocation = _QtCore.QStandardPaths.StandardLocation.TempLocation
        _QtCore.QStandardPaths.DataLocation = _QtCore.QStandardPaths.StandardLocation.DataLocation
        _QtCore.QStandardPaths.CacheLocation = _QtCore.QStandardPaths.StandardLocation.CacheLocation
        _QtCore.QStandardPaths.GenericCacheLocation = _QtCore.QStandardPaths.StandardLocation.GenericCacheLocation
        _QtCore.QStandardPaths.GenericDataLocation = _QtCore.QStandardPaths.StandardLocation.GenericDataLocation
        _QtCore.QStandardPaths.ConfigLocation = _QtCore.QStandardPaths.StandardLocation.ConfigLocation
        _QtCore.QStandardPaths.AppConfigLocation = _QtCore.QStandardPaths.StandardLocation.AppConfigLocation
        _QtCore.QStandardPaths.AppLocalDataLocation = _QtCore.QStandardPaths.StandardLocation.AppLocalDataLocation
        _QtCore.QStandardPaths.AppDataLocation = _QtCore.QStandardPaths.StandardLocation.AppDataLocation
        _QtCore.QStandardPaths.RuntimeLocation = _QtCore.QStandardPaths.StandardLocation.RuntimeLocation
    except AttributeError:
        pass
    
    # ==================== QFrame 枚举兼容 ====================
    try:
        import PyQt6.QtWidgets as _QtWidgets
        _QtWidgets.QFrame.NoFrame = _QtWidgets.QFrame.Shape.NoFrame
        _QtWidgets.QFrame.Box = _QtWidgets.QFrame.Shape.Box
        _QtWidgets.QFrame.Panel = _QtWidgets.QFrame.Shape.Panel
        _QtWidgets.QFrame.WinPanel = _QtWidgets.QFrame.Shape.WinPanel
        _QtWidgets.QFrame.HLine = _QtWidgets.QFrame.Shape.HLine
        _QtWidgets.QFrame.VLine = _QtWidgets.QFrame.Shape.VLine
        _QtWidgets.QFrame.StyledPanel = _QtWidgets.QFrame.Shape.StyledPanel
        _QtWidgets.QFrame.Plain = _QtWidgets.QFrame.Shadow.Plain
        _QtWidgets.QFrame.Raised = _QtWidgets.QFrame.Shadow.Raised
        _QtWidgets.QFrame.Sunken = _QtWidgets.QFrame.Shadow.Sunken
    except AttributeError:
        pass
    
    # ==================== QSizePolicy 枚举兼容 ====================
    try:
        import PyQt6.QtWidgets as _QtWidgets
        _QtWidgets.QSizePolicy.Fixed = _QtWidgets.QSizePolicy.Policy.Fixed
        _QtWidgets.QSizePolicy.Minimum = _QtWidgets.QSizePolicy.Policy.Minimum
        _QtWidgets.QSizePolicy.Maximum = _QtWidgets.QSizePolicy.Policy.Maximum
        _QtWidgets.QSizePolicy.Preferred = _QtWidgets.QSizePolicy.Policy.Preferred
        _QtWidgets.QSizePolicy.Expanding = _QtWidgets.QSizePolicy.Policy.Expanding
        _QtWidgets.QSizePolicy.MinimumExpanding = _QtWidgets.QSizePolicy.Policy.MinimumExpanding
        _QtWidgets.QSizePolicy.Ignored = _QtWidgets.QSizePolicy.Policy.Ignored
    except AttributeError:
        pass
    
    # ==================== QHeaderView 枚举兼容 ====================
    try:
        import PyQt6.QtWidgets as _QtWidgets
        _QtWidgets.QHeaderView.Interactive = _QtWidgets.QHeaderView.ResizeMode.Interactive
        _QtWidgets.QHeaderView.Stretch = _QtWidgets.QHeaderView.ResizeMode.Stretch
        _QtWidgets.QHeaderView.Fixed = _QtWidgets.QHeaderView.ResizeMode.Fixed
        _QtWidgets.QHeaderView.ResizeToContents = _QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        _log("QHeaderView 枚举映射完成")
    except (AttributeError, ImportError) as e:
        _log(f"QHeaderView 枚举映射失败: {e}")
    
    # ==================== QEvent 枚举兼容 ====================
    try:
        _QtCore.QEvent.Resize = _QtCore.QEvent.Type.Resize
        _QtCore.QEvent.Move = _QtCore.QEvent.Type.Move
        _QtCore.QEvent.Show = _QtCore.QEvent.Type.Show
        _QtCore.QEvent.Hide = _QtCore.QEvent.Type.Hide
        _QtCore.QEvent.Paint = _QtCore.QEvent.Type.Paint
        _QtCore.QEvent.Close = _QtCore.QEvent.Type.Close
        _QtCore.QEvent.MouseButtonPress = _QtCore.QEvent.Type.MouseButtonPress
        _QtCore.QEvent.MouseButtonRelease = _QtCore.QEvent.Type.MouseButtonRelease
        _QtCore.QEvent.MouseMove = _QtCore.QEvent.Type.MouseMove
        _QtCore.QEvent.MouseButtonDblClick = _QtCore.QEvent.Type.MouseButtonDblClick
        _QtCore.QEvent.KeyPress = _QtCore.QEvent.Type.KeyPress
        _QtCore.QEvent.KeyRelease = _QtCore.QEvent.Type.KeyRelease
        _QtCore.QEvent.FocusIn = _QtCore.QEvent.Type.FocusIn
        _QtCore.QEvent.FocusOut = _QtCore.QEvent.Type.FocusOut
        _QtCore.QEvent.Enter = _QtCore.QEvent.Type.Enter
        _QtCore.QEvent.Leave = _QtCore.QEvent.Type.Leave
        _QtCore.QEvent.Wheel = _QtCore.QEvent.Type.Wheel
        _QtCore.QEvent.ContextMenu = _QtCore.QEvent.Type.ContextMenu
        _QtCore.QEvent.ToolTip = _QtCore.QEvent.Type.ToolTip
        _QtCore.QEvent.HoverEnter = _QtCore.QEvent.Type.HoverEnter
        _QtCore.QEvent.HoverLeave = _QtCore.QEvent.Type.HoverLeave
        _QtCore.QEvent.HoverMove = _QtCore.QEvent.Type.HoverMove
        # QEvent.Accept/Ignore are methods, not types - removed in Qt6
        if hasattr(_QtCore.QEvent.Type, 'Ignore'):
            _QtCore.QEvent.Ignore = _QtCore.QEvent.Type.Ignore
        _log("QEvent 枚举映射完成")
    except AttributeError as e:
        _log(f"QEvent 枚举映射失败: {e}")
    
    # 创建 PyQt6 兼容别名
    sys.modules['PyQt6'] = sys.modules['PyQt6']
    sys.modules['PyQt6.QtCore'] = sys.modules['PyQt6.QtCore']
    sys.modules['PyQt6.QtGui'] = sys.modules['PyQt6.QtGui']
    sys.modules['PyQt6.QtWidgets'] = sys.modules['PyQt6.QtWidgets']
    sys.modules['PyQt6.QtNetwork'] = sys.modules['PyQt6.QtNetwork']
    
    # 处理 QtWebSockets（PyQt6 中需要单独导入）
    try:
        from PyQt6.QtWebSockets import *
        sys.modules['PyQt6.QtWebSockets'] = sys.modules['PyQt6.QtWebSockets']
    except ImportError:
        pass
    
except ImportError:
    # 使用原生 PyQt6
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtWidgets import *
    from PyQt6.QtNetwork import *
    try:
        from PyQt6.QtWebSockets import *
    except ImportError:
        pass

# qfluentwidgets 兼容处理
try:
    from qfluentwidgets import *
except ImportError:
    pass

def is_pyqt6():
    """返回是否使用 PyQt6"""
    return _USING_PYQT6

def get_qt_module():
    """返回当前使用的 Qt 模块名"""
    return 'PyQt6' if _USING_PYQT6 else 'PyQt6'
