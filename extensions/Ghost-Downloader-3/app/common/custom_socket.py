import json

from PySide6.QtCore import QObject, Slot
from PySide6.QtNetwork import QHostAddress
from PySide6.QtWebSockets import QWebSocketServer
from loguru import logger

from app.common.config import VERSION, LATEST_EXTENSION_VERSION, cfg
from app.common.methods import addDownloadTask, bringWindowToTop
from app.view.pop_up_window import ReceivedPopUpWindow


class GhostDownloaderSocketServer(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建 WebSocket 服务器并监听 localhost:14370
        self.server = QWebSocketServer("Ghost Downloader Socket Server", QWebSocketServer.NonSecureMode, parent)

        if self.server.listen(QHostAddress.LocalHost, 14370):
            logger.info(f"Server started on ws://{self.server.serverAddress().toString()}:{self.server.serverPort()}")

        self.server.newConnection.connect(self.onNewConnection)
        self.clients = []
        self._mainWindow = parent

    @Slot()
    def onNewConnection(self):
        client = self.server.nextPendingConnection()
        logger.debug(f"New client connected: {client.peerAddress().toString()}:{client.peerPort()}")

        client.textMessageReceived.connect(self.processTextMessage)
        client.disconnected.connect(self.onClientDisconnected)  # 连接断开时的信号

        client.sendTextMessage(json.dumps({"type": "version", "ClientVersion": VERSION, "LatestExtensionVersion": LATEST_EXTENSION_VERSION}))

        self.clients.append(client)

    @Slot()
    def onClientDisconnected(self):
        client = self.sender()  # 获取断开的客户端
        if client in self.clients:
            self.clients.remove(client)  # 从列表中移除断开的客户端
            logger.debug(f"Client disconnected: {client.peerAddress().toString()}:{client.peerPort()}")

    @Slot(str)
    def processTextMessage(self, message: str):
        """处理客户端发送的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "download")
            
            # 处理心跳消息
            if msg_type == "heartbeat":
                return
            
            # 处理进度查询请求
            if msg_type == "get_progress":
                self._handleProgressRequest(self.sender())
                return
            
            # 处理任务列表查询
            if msg_type == "get_tasks":
                self._handleTasksRequest(self.sender())
                return
            
            # 处理下载任务
            url = data.get("url", "")
            if not url:
                return
                
            headers = data.get("headers", {})
            if headers and "range" in headers:
                headers.pop("range", None)  # 浏览器插件会自动加上range头，导致下载失败
            
            referer = data.get("referer")
            if referer:
                headers["referer"] = referer
            
            filename = data.get("filename")

            if cfg.enableRaiseWindowWhenReceiveMsg.value:
                mainWindow = self.parent()
                bringWindowToTop(mainWindow)
                mainWindow.showAddTaskDialog(url, headers)
            else:
                addDownloadTask(url, filename, headers=headers)
                if filename:
                    ReceivedPopUpWindow.showPopUpWindow(filename, self.parent())
                else:
                    ReceivedPopUpWindow.showPopUpWindow(url, self.parent())

        except Exception as e:
            logger.error(f"Error processing message: {repr(e)}")
    
    def _handleProgressRequest(self, client):
        """处理进度查询请求"""
        try:
            mainWindow = self._mainWindow
            if not mainWindow or not hasattr(mainWindow, 'taskInterface'):
                client.sendTextMessage(json.dumps({"type": "progress", "error": "No task interface"}))
                return
            
            taskInterface = mainWindow.taskInterface
            cards = taskInterface.cards if hasattr(taskInterface, 'cards') else []
            
            # 统计活跃任务和总进度
            active_tasks = []
            total_speed = 0
            
            for card in cards:
                if card.status == "working":
                    task_info = {
                        "fileName": card.fileName,
                        "url": card.url,
                        "status": card.status,
                        "progress": card.task.progress if card.task else 0,
                        "fileSize": card.fileSize if hasattr(card, 'fileSize') else 0,
                    }
                    
                    # 计算速度
                    if card.task and hasattr(card.task, 'historySpeed'):
                        speed = sum(card.task.historySpeed) / 10 if card.task.historySpeed else 0
                        task_info["speed"] = speed
                        total_speed += speed
                    
                    active_tasks.append(task_info)
                
                elif card.status == "finished":
                    active_tasks.append({
                        "fileName": card.fileName,
                        "url": card.url,
                        "status": "finished",
                        "progress": card.fileSize if hasattr(card, 'fileSize') else 0,
                        "fileSize": card.fileSize if hasattr(card, 'fileSize') else 0,
                    })
            
            response = {
                "type": "progress",
                "globalSpeed": total_speed,
                "activeCount": len([t for t in active_tasks if t.get("status") == "working"]),
                "tasks": active_tasks
            }
            
            client.sendTextMessage(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error handling progress request: {e}")
            client.sendTextMessage(json.dumps({"type": "progress", "error": str(e)}))
    
    def _handleTasksRequest(self, client):
        """处理任务列表请求"""
        try:
            mainWindow = self._mainWindow
            if not mainWindow or not hasattr(mainWindow, 'taskInterface'):
                client.sendTextMessage(json.dumps({"type": "tasks", "error": "No task interface"}))
                return
            
            taskInterface = mainWindow.taskInterface
            cards = taskInterface.cards if hasattr(taskInterface, 'cards') else []
            
            tasks = []
            for card in cards:
                task_info = {
                    "fileName": card.fileName,
                    "url": card.url,
                    "status": card.status,
                    "filePath": str(card.filePath) if hasattr(card, 'filePath') else "",
                    "fileSize": card.fileSize if hasattr(card, 'fileSize') else 0,
                    "progress": card.task.progress if card.task and hasattr(card.task, 'progress') else 0,
                }
                tasks.append(task_info)
            
            response = {
                "type": "tasks",
                "tasks": tasks,
                "downloadFolder": cfg.downloadFolder.value
            }
            
            client.sendTextMessage(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error handling tasks request: {e}")
            client.sendTextMessage(json.dumps({"type": "tasks", "error": str(e)}))
