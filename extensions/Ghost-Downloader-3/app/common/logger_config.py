# -*- coding: utf-8 -*-
"""
Ghost Downloader 嵌入式兼容层日志配置
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 当前日志文件名
_current_log_file = None

def get_log_file():
    """获取当前日志文件路径"""
    global _current_log_file
    if _current_log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _current_log_file = LOG_DIR / f"ghost_embedded_{timestamp}.log"
    return _current_log_file

def setup_logging():
    """配置日志系统"""
    try:
        from loguru import logger
        
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台输出
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
        
        # 添加文件输出
        logger.add(
            str(get_log_file()),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            encoding="utf-8"
        )
        
        return logger
    except ImportError:
        # 如果没有loguru，使用标准logging
        import logging
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stderr),
                logging.FileHandler(str(get_log_file()), encoding='utf-8')
            ]
        )
        return logging.getLogger("ghost_embedded")


# 创建全局logger
logger = setup_logging()


def log_qt_compat_info():
    """记录Qt兼容层信息"""
    try:
        import PyQt6.QtCore as QtCore
        logger.info(f"PyQt6版本: {QtCore.PYQT_VERSION_STR}")
        logger.info(f"Qt版本: {QtCore.QT_VERSION_STR}")
        
        # 记录关键枚举是否已映射
        key_attrs = [
            'pyqtSignal', 'pyqtSlot', 'pyqtProperty',
            'Vertical', 'Horizontal', 'AlignCenter',
            'WA_TranslucentBackground', 'WindowMaximized'
        ]
        for attr in key_attrs:
            has_attr = hasattr(QtCore.Qt, attr)
            logger.debug(f"Qt.{attr}: {'✓' if has_attr else '✗'}")
            
    except Exception as e:
        logger.error(f"记录Qt兼容层信息失败: {e}")


def log_exception(e: Exception, context: str = ""):
    """记录异常详情"""
    import traceback
    logger.error(f"=== 异常发生 {'- ' + context if context else ''} ===")
    logger.error(f"异常类型: {type(e).__name__}")
    logger.error(f"异常信息: {e}")
    logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
