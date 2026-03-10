# coding: utf-8
from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """ pyqtSignal bus """
    addTaskSignal = pyqtSignal(str, str, str, dict, str, int, bool, str)  # url, fileName, filePath, headers, status, preBlockNum, notCreateHistoryFile, fileSize
    allTaskFinished = pyqtSignal()
    appErrorSig = pyqtSignal(str)
    showMainWindow = pyqtSignal()

signalBus = SignalBus()
