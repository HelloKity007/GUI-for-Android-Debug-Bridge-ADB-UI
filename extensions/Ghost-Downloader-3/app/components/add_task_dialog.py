import os
import re
import requests
from pathlib import Path
from threading import Thread

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QEvent
from PyQt6.QtGui import QColor, QResizeEvent
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem
from qfluentwidgets import (
    PushSettingCard,
    RangeSettingCard,
    MessageBox,
    InfoBar,
    InfoBarPosition,
    FluentStyleSheet,
)
from qfluentwidgets.common.icon import FluentIcon as FIF

from app.components.custom_mask_dialog_base import MaskDialogBase
from .Ui_AddTaskOptionDialog import Ui_AddTaskOptionDialog
from .custom_dialogs import EditHeadersDialog
from .select_folder_setting_card import SelectFolderSettingCard
from ..common.config import cfg, Headers
from ..common.methods import getReadableSize, getLinkInfo, addDownloadTask

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


class AddTaskOptionDialog(MaskDialogBase, Ui_AddTaskOptionDialog):

    _instance = None  # type: 'AddTaskOptionDialog'
    _initialized: bool = False  # 记录是否被 close
    __addTableRowSignal = pyqtSignal(
        str, str, str
    )  # fileName, fileSize, Url, 同理因为int最大值仅支持到2^31 PyQt无法定义int64 故只能使用str代替
    __gotWrong = pyqtSignal(str, int)  # error, index

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.customHeaders = Headers.copy()

        FluentStyleSheet.DIALOG.apply(self.widget)
        self._hBoxLayout.setContentsMargins(100, 75, 100, 75)
        self.widget.setContentsMargins(11, 11, 11, 11)

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self.setClosableOnMaskClicked(True)

        self.setupUi(self.widget)

        self.verticalLayout.setSpacing(8)
        self.widget.setWidget(self.scrollWidget)
        self.widget.setWidgetResizable(True)

        # Choose Folder Card
        self.downloadFolderCard = SelectFolderSettingCard(
            cfg.downloadFolder, cfg.historyDownloadFolder, self.widget
        )

        self.blockNumCard = RangeSettingCard(
            cfg.preBlockNum, FIF.CLOUD, self.tr("下载线程数"), "", self.widget
        )

        # Edit customHeaders Card
        self.editHeadersCard = PushSettingCard(
            self.tr("编辑请求标头"),
            FIF.EDIT,
            self.tr("自定义请求标头"),
            "",
            self.widget,
        )

        self.verticalLayout.insertWidget(4, self.downloadFolderCard)
        self.verticalLayout.insertWidget(5, self.blockNumCard)
        self.verticalLayout.insertWidget(6, self.editHeadersCard)

        self.__connectSignalToSlot()

    def eventFilter(self, obj, e: QEvent):
        if obj is self.window():
            if e.type() == QEvent.Resize:
                re = QResizeEvent(e)
                self.resize(re.size())
        elif obj is self.windowMask:
            if (
                e.type() == QEvent.MouseButtonRelease
                and e.button() == Qt.MouseButton.LeftButton
                and self.isClosableOnMaskClicked()
            ):
                self.close()

        return super().eventFilter(obj, e)

    @classmethod
    def showAddTaskOptionDialog(
        cls, urlContent: str = "", parent: "QWidget" = None, headers: dict = None
    ):
        # 检查单例是否已被删除
        if cls._initialized and cls._instance is not None:
            try:
                # 尝试访问对象以检查是否有效
                _ = cls._instance.linkTextEdit.toPlainText()
                if urlContent and not urlContent in _.split("\n"):
                    _ += "\n" + urlContent
                    cls._instance.linkTextEdit.setPlainText(_)
            except (RuntimeError, AttributeError):
                # 对象已被删除，重置单例状态
                cls._initialized = False
                cls._instance = None
        
        if not cls._initialized or cls._instance is None:
            cls._instance = AddTaskOptionDialog(
                parent=parent
            )  # 防止 nuitka 打包时因 cls 未定义而报错
            cls._initialized = True
            cls._instance.linkTextEdit.setPlainText(urlContent)

        if (
            headers
        ):  # TODO headers 处理不合理, 应该每个 Item 都有自己的 headers, 要不然容易下不了
            cls._instance.customHeaders = headers

        cls._instance.exec()

    def closeEvent(self, event):
        self.__whenClosed()
        super().closeEvent(event)

    @classmethod
    def __whenClosed(cls):
        cls._initialized = False
        cls._instance = None

    def __connectSignalToSlot(self):
        # self.downloadFolderCard.clicked.connect(
        #     self.__onDownloadFolderCardClicked)

        self.noButton.clicked.connect(self.close)
        self.yesButton.clicked.connect(self.__onYesButtonClicked)
        self.laterAction.triggered.connect(self.__onLaterActionTriggered)
        self.taskTableWidget.itemChanged.connect(self.__onTaskTableWidgetItemChanged)
        self.linkTextEdit.textChanged.connect(self.__onLinkTextChanged)
        self.__addTableRowSignal.connect(self.__addTableRow)
        self.__gotWrong.connect(self.__handleWrong)
        self.editHeadersCard.clicked.connect(self.__onEditHeadersCardClicked)
        
        # XBH任务ID输入框信号连接 - 改为延迟触发
        self._xbh_timer = QTimer()
        self._xbh_timer.setSingleShot(True)
        self._xbh_timer.timeout.connect(self.__onXbhIdSubmitted)
        self.xbhIdEdit.textChanged.connect(self.__onXbhTextChanged)
        self.radioGuangzhou.toggled.connect(self.__onServerRegionChanged)
        self.radioChangsha.toggled.connect(self.__onServerRegionChanged)
        
        # 设置默认服务器地区
        self.__setDefaultServerRegion()

    def __handleWrong(self, error: str, index: int):
        InfoBar.error(
            title=self.tr("错误"),
            content=self.tr("解析第 {} 个链接时遇到错误: {}").format(index, error),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=10000,
            parent=self.parent(),
        )

    def __onEditHeadersCardClicked(self):
        newHeaders, ok = EditHeadersDialog(
            self, initialHeaders=self.customHeaders
        ).getHeaders()
        if newHeaders and ok:
            self.customHeaders = newHeaders

    def __setDefaultServerRegion(self):
        """设置默认服务器地区"""
        default_region = cfg.defaultServerRegion.value
        if default_region == "广州":
            self.radioGuangzhou.setChecked(True)
        else:
            self.radioChangsha.setChecked(True)

    def __onServerRegionChanged(self):
        """服务器地区改变时保存设置"""
        if self.radioGuangzhou.isChecked():
            cfg.defaultServerRegion.value = "广州"
        else:
            cfg.defaultServerRegion.value = "长沙"

    def __onXbhTextChanged(self, text: str):
        """输入框内容改变时触发延迟解析"""
        # 检查是否有分隔符（逗号或空格）
        has_separator = (',' in text or '，' in text or ' ' in text)
        
        # 有分隔符时1秒触发，否则3秒触发
        delay = 1000 if has_separator else 3000
        
        # 重置定时器
        self._xbh_timer.stop()
        self._xbh_timer.start(delay)
    
    def __onXbhIdSubmitted(self):
        """定时器触发时解析任务ID"""
        xbhId = self.xbhIdEdit.text()
        self.__onXbhIdChanged(xbhId)
    
    def __onXbhIdChanged(self, xbhId: str):
        """任务ID输入改变时解析下载链接（在线程中执行）"""
        xbhId = xbhId.strip()
        if not xbhId:
            return

        # 解析多个任务ID（支持英文逗号,中文逗号，空格分隔）
        xbhId = xbhId.replace('，', ',').replace(' ', ',')
        task_ids = [tid.strip() for tid in xbhId.split(',') if tid.strip()]
        
        if not task_ids:
            return
        
        # 检查第一个ID是否是有效格式
        first_id = task_ids[0]
        if not (first_id.startswith("pgz_") or first_id.startswith("pcs_")):
            return

        # 获取服务器地址
        if self.radioGuangzhou.isChecked():
            server_url = "http://192.168.1.9:8283"
        else:
            server_url = "http://192.168.21.2:8080"

        # 在线程中执行网络请求
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
            
            # 返回主线程处理结果
            QTimer.singleShot(0, lambda: self.__onXbhFetched(results, len(task_ids)))
        
        # 启动线程
        Thread(target=fetch_urls, daemon=True).start()
    
    def __onXbhFetched(self, results, total_tasks):
        """在线程中获取到结果后处理"""
        total_urls = 0
        for task_id, text, error in results:
            if text:
                count = self.__parseXbhResponse(text, task_id)
                total_urls += count
            elif error:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr(f"任务ID [{task_id}] 解析失败: {error}"),
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    parent=self
                )
        
        if total_urls > 0:
            InfoBar.success(
                title=self.tr("成功"),
                content=self.tr(f"从 {total_tasks} 个任务ID共解析出 {total_urls} 个下载链接"),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                parent=self
            )

    def __parseXbhResponse(self, text: str, taskId: str) -> int:
        """解析XBH API返回的文本内容，返回解析出的URL数量"""
        # 按分号分割成多个文件信息
        pairs = text.split(';')

        existing_urls = self.linkTextEdit.toPlainText().split('\n')
        existing_urls = [url.strip() for url in existing_urls if url.strip()]

        new_urls = []
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue

            # 格式: key,value
            if ',' in pair:
                parts = pair.split(',', 1)
                if len(parts) == 2:
                    filename = parts[0].strip()
                    url = parts[1].strip()
                    if url and url not in existing_urls and url not in new_urls:
                        new_urls.append(url)

        if new_urls:
            # 添加到链接输入框
            current_text = self.linkTextEdit.toPlainText()
            if current_text and not current_text.endswith('\n'):
                current_text += '\n'
            current_text += '\n'.join(new_urls)
            self.linkTextEdit.setPlainText(current_text)

        return len(new_urls)

    def __onYesButtonClicked(self):
        path = Path(self.downloadFolderCard.contentLabel.text())

        # 检测路径是否有权限写入
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                MessageBox(self.tr("错误"), repr(e), self)
        else:
            if not os.access(path, os.W_OK):
                MessageBox(
                    self.tr("错误"), self.tr("似乎是没有权限向此目录写入文件"), self
                )

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

        self.close()

    def __onLaterActionTriggered(self):
        path = Path(self.downloadFolderCard.contentLabel.text())

        # 检测路径是否有权限写入
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                MessageBox(self.tr("错误"), repr(e), self)
        else:
            if not os.access(path, os.W_OK):
                MessageBox(
                    self.tr("错误"), self.tr("似乎是没有权限向此目录写入文件"), self
                )

        for i in range(self.taskTableWidget.rowCount()):
            item = self.taskTableWidget.item(i, 0)
            fileName = item.text() if item.text() != item.data(1) else None

            addDownloadTask(
                item.data(1),
                fileName,
                str(path),
                self.customHeaders,
                "paused",
                self.blockNumCard.configItem.value,
            )

        self.close()

    def __onDownloadFolderCardClicked(self):
        """download folder card clicked slot"""
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"), "./")
        if not folder or self.downloadFolderCard.contentLabel.text() == folder:
            return

        self.downloadFolderCard.setContent(folder)

    def __onLinkTextChanged(self):
        if hasattr(self, "_timer"):
            self._timer.stop()

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.__progressTextChange)
        self._timer.start(1000)  # 1秒后处理

    def __handleUrl(self, url: str, index: int):
        try:
            _url, fileName, fileSize = getLinkInfo(url, self.customHeaders)
            # 查找是否存在该 URL 的行
            for i in range(self.taskTableWidget.rowCount()):
                if self.taskTableWidget.item(i, 0).data(1) == url:
                    # 更新文件名和文件大小
                    self.taskTableWidget.item(i, 0).setText(fileName)
                    self.taskTableWidget.item(i, 1).setText(
                        getReadableSize(int(fileSize))
                    )
                    return
            # 如果不存在则添加新行
            self.__addTableRowSignal.emit(fileName, str(fileSize), url)
        except Exception as e:
            self.__gotWrong.emit(repr(e), index)

    def __addTableRow(self, fileName: str, fileSize: str, url: str):
        """add table row slot"""
        self.taskTableWidget.insertRow(self.taskTableWidget.rowCount())
        _ = QTableWidgetItem(fileName)
        _.setData(1, url)  # 记录 Url
        _.setData(2, fileName)  # 设置默认值, 当用户修改后的内容为空是，使用默认值替换
        self.taskTableWidget.setItem(self.taskTableWidget.rowCount() - 1, 0, _)
        _ = QTableWidgetItem(getReadableSize(int(fileSize)))
        _.setFlags(Qt.ItemFlag.ItemIsEnabled)  # 禁止编辑
        self.taskTableWidget.setItem(self.taskTableWidget.rowCount() - 1, 1, _)

        # self.taskTableWidget.resizeColumnsToContents()

    def __onTaskTableWidgetItemChanged(self, item: QTableWidgetItem):
        """task table widget item changed slot"""
        if item.text() == "":
            item.setText(item.data(2))

    def __progressTextChange(self):
        """link text changed slot"""
        self.threads = []

        self.yesButton.setEnabled(False)

        text: list = self.linkTextEdit.toPlainText().split("\n")

        # 获取当前输入的URL列表
        currentUrls = [url.strip() for url in text if url.strip()]
        # 获取之前的URL列表
        previousUrls = [
            self.taskTableWidget.item(i, 0).data(1)
            for i in range(self.taskTableWidget.rowCount())
        ]

        # 找出新增、删除和修改的URL
        addedUrls = set(currentUrls) - set(previousUrls)
        removedUrls = set(previousUrls) - set(currentUrls)
        modifiedUrls = set(currentUrls).intersection(set(previousUrls))

        # 删除被删除的URL的行（从后向前遍历）
        for url in removedUrls:
            for i in range(self.taskTableWidget.rowCount() - 1, -1, -1):  # 从后向前遍历
                if self.taskTableWidget.item(i, 0).data(1) == url:
                    self.taskTableWidget.removeRow(i)
                    break

        # 重新生成被编辑过的URL的行
        for url in modifiedUrls:
            for i in range(self.taskTableWidget.rowCount()):
                if self.taskTableWidget.item(i, 0).data(1) == url:
                    item = self.taskTableWidget.item(i, 0)
                    if item.text() != item.data(2):  # 如果用户修改了文件名
                        self.__handleUrl(url, i + 1)  # 重新处理URL
                    break

        # 添加新增的URL的行
        for index, url in enumerate(currentUrls, start=1):
            if url in addedUrls:
                _ = urlRe.search(url)
                if _:
                    self.__addTableRow(
                        url, "0", url
                    )  # 新增卡片并设置文件名和文件大小为“正在获取...”
                    self.threads.append(
                        Thread(target=self.__handleUrl, args=(url, index), daemon=True)
                    )
                else:
                    InfoBar.warning(
                        title=self.tr("警告"),
                        content=self.tr("第{}个链接无效!").format(index),
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=1000,
                        parent=self.parent(),
                    )

        self.yesButton.setEnabled(True)

        if self.threads:
            for thread in self.threads:
                thread.start()

            Thread(target=self.__waitForThreads, daemon=True).start()

    def __waitForThreads(self):
        for thread in self.threads:
            thread.join()
