#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logcat 管理器 v2 - 简化架构，可靠运行
使用 threading.Thread + 队列模式，避免 QThread 信号问题
"""

import subprocess
import sys
import os
import threading
import queue
import logging
from datetime import datetime
from typing import Optional, Callable, List

logger = logging.getLogger("logcat_manager")


class LogcatManager:
    """
    Logcat 管理器 v2
    - 使用 threading.Thread 而非 QThread（避免信号/槽问题）
    - 使用 Queue 传递数据
    - 主线程定时器轮询队列
    """

    BATCH_SIZE = 50
    POLL_INTERVAL_MS = 100

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._process: Optional[subprocess.Popen] = None
        self._running: bool = False
        self._lock = threading.Lock()

        # 数据队列
        self._log_queue: queue.Queue = queue.Queue()
        self._status_queue: queue.Queue = queue.Queue()

        # 回调函数
        self._on_logs: Optional[Callable[[List[str]], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_status: Optional[Callable[[bool, str], None]] = None

        # 定时器（由调用方设置）
        self._timer = None

        logger.info("LogcatManager v2 初始化完成")

    def set_callbacks(self,
                      on_logs: Callable[[List[str]], None] = None,
                      on_error: Callable[[str], None] = None,
                      on_status: Callable[[bool, str], None] = None):
        """设置回调函数"""
        self._on_logs = on_logs
        self._on_error = on_error
        self._on_status = on_status

    def set_timer(self, timer):
        """设置 QTimer 用于轮询队列"""
        self._timer = timer
        if timer:
            timer.timeout.connect(self._poll_queues)

    def _poll_queues(self):
        """轮询队列并调用回调（主线程中执行）"""
        # 处理日志队列
        logs = []
        try:
            while True:
                line = self._log_queue.get_nowait()
                logs.append(line)
                if len(logs) >= self.BATCH_SIZE:
                    break
        except queue.Empty:
            pass

        if logs and self._on_logs:
            try:
                self._on_logs(logs)
            except Exception as e:
                logger.error(f"日志回调异常: {e}")

        # 处理状态队列
        try:
            while True:
                running, message = self._status_queue.get_nowait()
                if self._on_status:
                    try:
                        self._on_status(running, message)
                    except Exception as e:
                        logger.error(f"状态回调异常: {e}")
        except queue.Empty:
            pass

    def start(self, adb_path: str, device_id: str) -> bool:
        """启动 logcat（非阻塞）"""
        logger.info(f"启动 logcat: adb={adb_path}, device={device_id}")

        # 如果已在运行，先停止
        if self.is_running():
            self.stop()
            # 等待旧线程结束（最多 1 秒）
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

        # 验证参数
        if not adb_path or not os.path.exists(adb_path):
            error = f"ADB 路径无效: {adb_path}"
            logger.error(error)
            self._status_queue.put((False, error))
            return False

        if not device_id:
            error = "未指定设备 ID"
            logger.error(error)
            self._status_queue.put((False, error))
            return False

        # 清空队列
        self._clear_queues()

        # 启动工作线程
        with self._lock:
            self._running = True

        self._thread = threading.Thread(
            target=self._worker_thread,
            args=(adb_path, device_id),
            daemon=True
        )
        self._thread.start()

        # 启动定时器
        if self._timer:
            self._timer.start(self.POLL_INTERVAL_MS)

        return True

    def stop(self):
        """停止 logcat（非阻塞）"""
        logger.info("请求停止 logcat")

        with self._lock:
            self._running = False

        # 终止子进程
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception as e:
                logger.warning(f"终止进程异常: {e}")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        with self._lock:
            return self._running

    def cleanup(self):
        """清理资源"""
        self.stop()
        if self._timer:
            self._timer.stop()

    def _clear_queues(self):
        """清空队列"""
        try:
            while True:
                self._log_queue.get_nowait()
        except queue.Empty:
            pass

        try:
            while True:
                self._status_queue.get_nowait()
        except queue.Empty:
            pass

    def _worker_thread(self, adb_path: str, device_id: str):
        """工作线程 - 流式读取 logcat"""
        logger.info(f"工作线程启动: device={device_id}")
        self._status_queue.put((True, f"Logcat 已启动 (设备: {device_id})"))

        try:
            cmd = [adb_path, '-s', device_id, 'logcat', '-v', 'threadtime']
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=creationflags
            )

            logger.info(f"Logcat 进程已启动, PID: {self._process.pid}")

            # 读取输出
            while self._is_running_safe():
                if self._process.poll() is not None:
                    break

                try:
                    line = self._process.stdout.readline()
                    if line:
                        line = line.rstrip('\n\r')
                        if line:
                            self._log_queue.put(line)
                    else:
                        # 无数据，短暂等待
                        import time
                        time.sleep(0.01)
                except Exception as e:
                    logger.error(f"读取 logcat 输出异常: {e}")
                    break

        except FileNotFoundError:
            error = f"找不到 ADB: {adb_path}"
            logger.error(error)
            self._status_queue.put((False, error))
        except Exception as e:
            error = f"Logcat 异常: {str(e)}"
            logger.exception(error)
            self._status_queue.put((False, error))
        finally:
            # 清理进程
            self._cleanup_process()
            with self._lock:
                self._running = False
            self._status_queue.put((False, "Logcat 已停止"))
            logger.info("工作线程退出")

    def _is_running_safe(self) -> bool:
        """线程安全检查运行状态"""
        with self._lock:
            return self._running

    def _cleanup_process(self):
        """清理进程"""
        if self._process:
            try:
                if self._process.poll() is None:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait(timeout=1)
            except Exception as e:
                logger.warning(f"清理进程异常: {e}")
            finally:
                self._process = None
