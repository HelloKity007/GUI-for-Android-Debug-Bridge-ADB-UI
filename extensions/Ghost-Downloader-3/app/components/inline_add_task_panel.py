# -*- coding: utf-8 -*-
"""
@Description: 内嵌式新建任务面板 - 替代弹出对话框
@Version: 1.0.0
@Date: 2026-03-24
@Author: AI Assistant
@FilePath: extensions/Ghost-Downloader-3/app/components/inline_add_task_panel.py
"""
import os
import re
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame,
    QTableWidgetItem, QHeaderView, QFileDialog
)
from qfluentwidgets import (
    PlainTextEdit, LineEdit, PushButton, PrimaryPushButton,
    ToolButton, TableWidget, BodyLabel, CardWidget,
    RangeSettingCard, PushSettingCard, InfoBar, InfoBarPosition,
    FluentIcon as FIF
)
from PySide6.QtWidgets import QRadioButton, QButtonGroup

import requests

from ..common.config import cfg, Headers
from ..common.methods import getReadableSize, getLinkInfo, addDownloadTask
from .select_folder_setting_card import SelectFolderSettingCard
from .custom_dialogs import EditHeadersDialog

# URL正则表达式
urlRe = re.compile(
    r"""
    ^
    (https?://)                                                         # 协议
    (?:
        \S+ (?::\S*)? @                                                 # 用户信息 e.g., user:pass@
    )?
    (
            # a. IPv6
        \[
            (?:
                (?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}
                |
                (?!.*::.*::)
                    (?:
                        (?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4}
                    )?
                    ::
                    (?:
                        (?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4}
                    )?
                |
                # IPv4 映射
                (?:(?:[0-9a-f]{1,4}:){6})?
                (?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}
                (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)
            )
        ]
        |
        (?:
            (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) \.
        ){3}
        (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)                        # b.IP 地址
        |
        localhost                                                       # c. Localhost
        |                                                                     # d.域名
        (?: (?:[a-z¡-￿0-9]-*)*[a-z¡-￿0-9]+ | xn--[a-z0-9-]+ )                   # 域名标签 (e.g., "example", "xn--ls8h", "你好")
        (?: \. (?: (?:[a-z¡-￿0-9]-*)*[a-z¡-￿0-9]+ | xn--[a-z0-9-]+ ) )*         # 后续子域名
        ( \. (?: [a-z¡-￿]{2,} | xn--[a-z0-9-]+ ) )                             # 顶级域名
        |
    )
    (?::\d{2,5})?                                                       # 端口
    (?:/ \S*)?                                                          # 路径
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)


class InlineAddTaskPanel(CardWidget):
    """内嵌式新建任务面板"""

    # 信号
    __addTableRowSignal = Signal(str, str, str)  # fileName, fileSize, Url
    __gotWrong = Signal(str, int)  # error, index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InlineAddTaskPanel")

        self.customHeaders = Headers.copy()
        self._optionsExpanded = False
        self._optionsHeight = 200  # 展开后的高度

        self.setupUi()
        self._connectSignals()
        self._setDefaultServerRegion()

    def setupUi(self):
        """设置界面"""
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(12, 12, 12, 12)
        self.mainLayout.setSpacing(8)

        # ========== 第一行：下载链接输入 ==========
        self.urlLabel = BodyLabel(self.tr("下载链接"), self)
        self.mainLayout.addWidget(self.urlLabel)

        self.linkTextEdit = PlainTextEdit(self)
        self.linkTextEdit.setPlaceholderText(
            self.tr("输入下载链接，多个链接请换行分隔")
        )
        self.linkTextEdit.setMaximumHeight(60)
        self.linkTextEdit.setLineWrapMode(PlainTextEdit.LineWrapMode.NoWrap)
        self.mainLayout.addWidget(self.linkTextEdit)

        # ========== 第二行：任务ID输入 + 服务器选择 ==========
        self.xbhLayout = QHBoxLayout()
        self.xbhLayout.setSpacing(10)

        self.xbhIdLabel = BodyLabel(self.tr("任务ID:"), self)
        self.xbhLayout.addWidget(self.xbhIdLabel)

        self.xbhIdEdit = LineEdit(self)
        self.xbhIdEdit.setPlaceholderText(self.tr("pgz_xxx 或 pcs_yyy，支持逗号分隔多个"))
        self.xbhIdEdit.setMinimumWidth(180)
        self.xbhLayout.addWidget(self.xbhIdEdit, 1)

        # 服务器选择
        self.serverLabel = BodyLabel(self.tr("服务器:"), self)
        self.xbhLayout.addWidget(self.serverLabel)

        self.serverGroup = QButtonGroup(self)

        self.radioGuangzhou = QRadioButton(self.tr("广州"), self)
        self.radioGuangzhou.setStyleSheet(
            "QRadioButton { font-weight: normal; padding: 4px 8px; } "
            "QRadioButton:checked { background-color: #e3f2fd; border-radius: 4px; }"
        )
        self.serverGroup.addButton(self.radioGuangzhou)
        self.xbhLayout.addWidget(self.radioGuangzhou)

        self.radioChangsha = QRadioButton(self.tr("长沙"), self)
        self.radioChangsha.setStyleSheet(
            "QRadioButton { font-weight: normal; padding: 4px 8px; } "
            "QRadioButton:checked { background-color: #e3f2fd; border-radius: 4px; }"
        )
        self.serverGroup.addButton(self.radioChangsha)
        self.xbhLayout.addWidget(self.radioChangsha)

        self.mainLayout.addLayout(self.xbhLayout)

        # ========== 第三行：开始下载按钮 + 展开箭头 ==========
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(4)

        self.startButton = PrimaryPushButton(self.tr("开始下载"), self)
        self.startButton.setIcon(FIF.DOWNLOAD)
        self.startButton.setEnabled(False)
        self.buttonLayout.addWidget(self.startButton, 1)

        self.expandButton = ToolButton(FIF.CHEVRON_DOWN_MED, self)
        self.expandButton.setToolTip(self.tr("展开更多选项"))
        self.expandButton.setFixedSize(32, 32)
        self.buttonLayout.addWidget(self.expandButton)

        self.mainLayout.addLayout(self.buttonLayout)

        # ========== 可折叠选项区域 ==========
        self.optionsWidget = QWidget(self)
        self.optionsWidget.setObjectName("optionsWidget")
        self.optionsLayout = QVBoxLayout(self.optionsWidget)
        self.optionsLayout.setContentsMargins(0, 8, 0, 0)
        self.optionsLayout.setSpacing(8)

        # 分隔线
        self.separator = QFrame(self.optionsWidget)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.optionsLayout.addWidget(self.separator)

        # 任务列表表格
        self.taskTableWidget = TableWidget(self.optionsWidget)
        self.taskTableWidget.setColumnCount(2)
        self.taskTableWidget.setHorizontalHeaderItem(0, QTableWidgetItem(self.tr("文件名")))
        self.taskTableWidget.setHorizontalHeaderItem(1, QTableWidgetItem(self.tr("大小")))
        self.taskTableWidget.verticalHeader().setVisible(False)
        self.taskTableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.taskTableWidget.setMaximumHeight(120)
        self.optionsLayout.addWidget(self.taskTableWidget)

        # 下载目录选择
        self.downloadFolderCard = SelectFolderSettingCard(
            cfg.downloadFolder, cfg.historyDownloadFolder, self.optionsWidget
        )
        self.optionsLayout.addWidget(self.downloadFolderCard)

        # 线程数设置
        self.blockNumCard = RangeSettingCard(
            cfg.preBlockNum, FIF.CLOUD, self.tr("下载线程数"), "", self.optionsWidget
        )
        self.optionsLayout.addWidget(self.blockNumCard)

        # 自定义请求头
        self.editHeadersCard = PushSettingCard(
            self.tr("编辑请求标头"),
            FIF.EDIT,
            self.tr("自定义请求标头"),
            "",
            self.optionsWidget,
        )
        self.optionsLayout.addWidget(self.editHeadersCard)

        self.mainLayout.addWidget(self.optionsWidget)

        # 初始隐藏选项区域
        self.optionsWidget.setVisible(False)
        self.optionsWidget.setMaximumHeight(0)

    def _connectSignals(self):
        """连接信号"""
        # 展开/收起按钮
        self.expandButton.clicked.connect(self._toggleOptions)

        # 开始下载
        self.startButton.clicked.connect(self._onStartClicked)

        # 链接文本变化
        self.linkTextEdit.textChanged.connect(self._onLinkTextChanged)

        # 表格行信号
        self.__addTableRowSignal.connect(self._addTableRow)
        self.__gotWrong.connect(self._handleWrong)

        # 任务ID输入
        self._xbh_timer = QTimer()
        self._xbh_timer.setSingleShot(True)
        self._xbh_timer.timeout.connect(self._onXbhIdSubmitted)
        self.xbhIdEdit.textChanged.connect(self._onXbhTextChanged)

        # 服务器选择
        self.radioGuangzhou.toggled.connect(self._onServerRegionChanged)
        self.radioChangsha.toggled.connect(self._onServerRegionChanged)

        # 编辑请求头
        self.editHeadersCard.clicked.connect(self._onEditHeadersClicked)

        # 表格项修改
        self.taskTableWidget.itemChanged.connect(self._onTaskTableItemChanged)

    def _toggleOptions(self):
        """切换选项区域展开/收起"""
        self._optionsExpanded = not self._optionsExpanded

        if self._optionsExpanded:
            self.optionsWidget.setVisible(True)
            self.optionsWidget.setMaximumHeight(16777215)  # 取消高度限制
            self.expandButton.setIcon(FIF.UP)
            self.expandButton.setToolTip(self.tr("收起选项"))
        else:
            self.optionsWidget.setVisible(False)
            self.optionsWidget.setMaximumHeight(0)
            self.expandButton.setIcon(FIF.CHEVRON_DOWN_MED)
            self.expandButton.setToolTip(self.tr("展开更多选项"))

    def _setDefaultServerRegion(self):
        """设置默认服务器地区"""
        default_region = cfg.defaultServerRegion.value
        if default_region == "广州":
            self.radioGuangzhou.setChecked(True)
        else:
            self.radioChangsha.setChecked(True)

    def _onServerRegionChanged(self):
        """服务器地区改变时保存设置"""
        if self.radioGuangzhou.isChecked():
            cfg.defaultServerRegion.value = "广州"
        else:
            cfg.defaultServerRegion.value = "长沙"

    def _onXbhTextChanged(self, text: str):
        """任务ID输入变化"""
        has_separator = (',' in text or '，' in text or ' ' in text)
        delay = 1000 if has_separator else 3000
        self._xbh_timer.stop()
        self._xbh_timer.start(delay)

    def _onXbhIdSubmitted(self):
        """任务ID提交"""
        xbhId = self.xbhIdEdit.text().strip()
        if not xbhId:
            return

        # 解析多个任务ID
        xbhId = xbhId.replace('，', ',').replace(' ', ',')
        task_ids = [tid.strip() for tid in xbhId.split(',') if tid.strip()]

        if not task_ids:
            return

        first_id = task_ids[0]
        if not (first_id.startswith("pgz_") or first_id.startswith("pcs_")):
            return

        # 获取服务器地址
        if self.radioGuangzhou.isChecked():
            server_url = "http://192.168.1.9:8283"
        else:
            server_url = "http://192.168.21.2:8080"

        def fetch_urls():
            results = []
            for task_id in task_ids:
                api_url = f"{server_url}/auditServer/commServer/resource/downloadTaskTxt?taskName={task_id}"
                try:
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        text = response.text.strip()
                        if text:
                            results.append((task_id, text, None))
                except Exception as e:
                    results.append((task_id, None, str(e)))

            QTimer.singleShot(0, lambda r=results, t=len(task_ids): self._onXbhFetched(r, t))

        Thread(target=fetch_urls, daemon=True).start()

    def _onXbhFetched(self, results, total_tasks):
        """任务ID获取结果"""
        total_urls = 0
        for task_id, text, error in results:
            if text:
                count = self._parseXbhResponse(text, task_id)
                total_urls += count
            elif error:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr(f"任务ID [{task_id}] 解析失败: {error}"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    parent=self
                )

        if total_urls > 0:
            InfoBar.success(
                title=self.tr("成功"),
                content=self.tr(f"从 {total_tasks} 个任务ID共解析出 {total_urls} 个下载链接"),
                orient=Qt.Horizontal,
                isClosable=True,
                parent=self
            )

    def _parseXbhResponse(self, text: str, taskId: str) -> int:
        """解析XBH API返回"""
        pairs = text.split(';')
        existing_urls = self.linkTextEdit.toPlainText().split('\n')
        existing_urls = [url.strip() for url in existing_urls if url.strip()]

        new_urls = []
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            if ',' in pair:
                parts = pair.split(',', 1)
                if len(parts) == 2:
                    url = parts[1].strip()
                    if url and url not in existing_urls and url not in new_urls:
                        new_urls.append(url)

        if new_urls:
            current_text = self.linkTextEdit.toPlainText()
            if current_text and not current_text.endswith('\n'):
                current_text += '\n'
            current_text += '\n'.join(new_urls)
            self.linkTextEdit.setPlainText(current_text)

        return len(new_urls)

    def _onLinkTextChanged(self):
        """链接文本变化"""
        if hasattr(self, "_link_timer"):
            self._link_timer.stop()

        self._link_timer = QTimer()
        self._link_timer.setSingleShot(True)
        self._link_timer.timeout.connect(self._processLinkText)
        self._link_timer.start(1000)

    def _processLinkText(self):
        """处理链接文本"""
        self.threads = []
        self.startButton.setEnabled(False)

        text = self.linkTextEdit.toPlainText().split("\n")
        currentUrls = [url.strip() for url in text if url.strip()]
        previousUrls = [
            self.taskTableWidget.item(i, 0).data(1)
            for i in range(self.taskTableWidget.rowCount())
        ]

        addedUrls = set(currentUrls) - set(previousUrls)
        removedUrls = set(previousUrls) - set(currentUrls)

        # 删除被移除的行
        for url in removedUrls:
            for i in range(self.taskTableWidget.rowCount() - 1, -1, -1):
                if self.taskTableWidget.item(i, 0).data(1) == url:
                    self.taskTableWidget.removeRow(i)
                    break

        # 添加新行
        for index, url in enumerate(currentUrls, start=1):
            if url in addedUrls:
                if urlRe.search(url):
                    self._addTableRow(url, "0", url)
                    self.threads.append(
                        Thread(target=self._handleUrl, args=(url, index), daemon=True)
                    )
                else:
                    InfoBar.warning(
                        title=self.tr("警告"),
                        content=self.tr("第{}个链接无效!").format(index),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=1000,
                        parent=self.window() if self.window() else self
                    )

        self.startButton.setEnabled(bool(currentUrls))

        if self.threads:
            for thread in self.threads:
                thread.start()

    def _handleUrl(self, url: str, index: int):
        """处理单个URL"""
        try:
            _url, fileName, fileSize = getLinkInfo(url, self.customHeaders)
            for i in range(self.taskTableWidget.rowCount()):
                if self.taskTableWidget.item(i, 0).data(1) == url:
                    self.taskTableWidget.item(i, 0).setText(fileName)
                    self.taskTableWidget.item(i, 1).setText(
                        getReadableSize(int(fileSize))
                    )
                    return
            self.__addTableRowSignal.emit(fileName, str(fileSize), url)
        except Exception as e:
            self.__gotWrong.emit(repr(e), index)

    def _addTableRow(self, fileName: str, fileSize: str, url: str):
        """添加表格行"""
        self.taskTableWidget.insertRow(self.taskTableWidget.rowCount())
        item = QTableWidgetItem(fileName)
        item.setData(1, url)
        item.setData(2, fileName)
        self.taskTableWidget.setItem(self.taskTableWidget.rowCount() - 1, 0, item)

        sizeItem = QTableWidgetItem(getReadableSize(int(fileSize)))
        sizeItem.setFlags(Qt.ItemIsEnabled)
        self.taskTableWidget.setItem(self.taskTableWidget.rowCount() - 1, 1, sizeItem)

    def _onTaskTableItemChanged(self, item: QTableWidgetItem):
        """表格项变化"""
        if item.text() == "":
            item.setText(item.data(2))

    def _handleWrong(self, error: str, index: int):
        """处理错误"""
        InfoBar.error(
            title=self.tr("错误"),
            content=self.tr("解析第 {} 个链接时遇到错误: {}").format(index, error),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=10000,
            parent=self.window() if self.window() else self
        )

    def _onEditHeadersClicked(self):
        """编辑请求头"""
        newHeaders, ok = EditHeadersDialog(
            self, initialHeaders=self.customHeaders
        ).getHeaders()
        if newHeaders and ok:
            self.customHeaders = newHeaders

    def _onStartClicked(self):
        """开始下载"""
        path = Path(self.downloadFolderCard.contentLabel.text())

        # 检测路径权限
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                InfoBar.error(
                    title=self.tr("错误"),
                    content=repr(e),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    parent=self.window() if self.window() else self
                )
                return
        else:
            if not os.access(path, os.W_OK):
                InfoBar.error(
                    title=self.tr("错误"),
                    content=self.tr("似乎没有权限向此目录写入文件"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    parent=self.window() if self.window() else self
                )
                return

        # 添加下载任务
        for i in range(self.taskTableWidget.rowCount()):
            item = self.taskTableWidget.item(i, 0)
            fileName = item.text() if item.text() != item.data(1) else None

            addDownloadTask(
                item.data(1),
                fileName,
                str(path),
                self.customHeaders,
                preBlockNum=self.blockNumCard.configItem.value,
            )

        # 清空输入
        self.linkTextEdit.clear()
        self.xbhIdEdit.clear()
        self.taskTableWidget.setRowCount(0)
        self.startButton.setEnabled(False)

        InfoBar.success(
            title=self.tr("成功"),
            content=self.tr("已添加下载任务"),
            orient=Qt.Horizontal,
            isClosable=True,
            parent=self.window() if self.window() else self
        )

    def tr(self, text):
        """翻译"""
        return text

