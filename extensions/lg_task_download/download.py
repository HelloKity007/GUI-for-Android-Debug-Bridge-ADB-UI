#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import threading
import urllib.parse
import urllib.request
import concurrent.futures
import io

#$XBH_AI_PATCH_START
# 修复 Windows CMD 环境下的编码兼容性问题
# 强制 stdout/stderr 使用 UTF-8 编码，errors='replace' 避免编码失败
#$XBH_AI_PATCH_MODIFY
if sys.platform == 'win32':
    # Windows 环境下强制 UTF-8 输出，不兼容字符替换为 ?
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
#$XBH_AI_PATCH_END

TO_ENCODE = {
    "低存储检测对策": "%E4%BD%8E%E5%AD%98%E5%82%A8%E6%A3%80%E6%B5%8B%E5%AF%B9%E7%AD%96",
    "资料卡": "%E8%B5%84%E6%96%99%E5%8D%A1",
    "请解压": "%E8%AF%B7%E8%A7%A3%E5%8E%8B",
    "芯片": "%E8%8A%AF%E7%89%87",
    "刷机": "%E5%88%B7%E6%9C%BA",
    "差分": "%E5%B7%AE%E5%88%86",
    "屏参": "%E5%B1%8F%E5%8F%82",
    "电脑": "%E7%94%B5%E8%84%91",
    "文件": "%E6%96%87%E4%BB%B6",
    "工厂": "%E5%B7%A5%E5%8E%82",
    "方法": "%E6%96%B9%E6%B3%95",
    "闪烁": "%E9%97%AA%E7%83%81",
    "灵动": "%E7%81%B5%E5%8A%A8",
    "升级": "%E5%8D%87%E7%BA%A7",
    "系统": "%E7%B3%BB%E7%BB%9F",
    "固件": "%E5%9B%BA%E4%BB%B6",
    "烧录": "%E7%83%A7%E5%BD%95",
    "软件": "%E8%BD%AF%E4%BB%B6",
    "客户": "%E5%AE%A2%E6%88%B7",
    "生产": "%E7%94%9F%E4%BA%A7",
    "维修": "%E7%BB%B4%E4%BF%AE",
    "串口": "%E4%B8%B2%E5%8F%A3",
    "【": "%E3%80%90",
    "】": "%E3%80%91",
    "（": "%EF%BC%88",
    "）": "%EF%BC%89",
    "盘": "%E7%9B%98",
    "及": "%E5%8F%8A",
    "包": "%E5%8C%85",
    "使": "%E4%BD%BF",
    "用": "%E7%94%A8",
    "前": "%E5%89%8D",
    "为": "%E4%B8%BA",
}

SERVERS = {
    "gz": "http://192.168.1.9:8283/auditServer/commServer/resource/downloadTaskTxt",
    "cs": "http://192.168.21.2:8080/auditServer/commServer/resource/downloadTaskTxt",
}


def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    return {}


def encode_url(value):
    for char, encoded in TO_ENCODE.items():
        value = value.replace(char, encoded)
    return value


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


class MultiThreadDownloader:
    def __init__(self, url, filepath, num_threads):
        self.url = url
        self.filepath = filepath
        self.num_threads = num_threads
        self.total_size = 0
        self.downloaded = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.last_percent = -1
        self.finished_chunks = 0
        self.total_chunks = 0
        self.last_print_time = 0
    
    def get_file_size(self):
        try:
            req = urllib.request.Request(self.url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req) as response:
                self.total_size = int(response.headers.get('Content-Length', 0))
                return self.total_size
        except Exception:
            return 0
    
    def update_progress(self, chunk_size):
        with self.lock:
            self.downloaded += chunk_size
            
            current_time = time.time()
            if current_time - self.last_print_time < 0.1:
                return
            
            if self.total_size > 0:
                percent = int((self.downloaded * 100) / self.total_size)
                if percent != self.last_percent:
                    self.last_percent = percent
                    self.last_print_time = current_time
                    self._print_progress()
    
    def _print_progress(self):
        downloaded_str = format_size(self.downloaded)
        total_str = format_size(self.total_size)
        
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            speed = self.downloaded / elapsed
            speed_str = format_size(speed) + "/s"
        else:
            speed_str = "0 B/s"
        
        bar_width = 25
        filled = int(bar_width * self.downloaded / self.total_size) if self.total_size > 0 else 0
        #$XBH_AI_PATCH_START
        # bar = '█' * filled + '░' * (bar_width - filled)
        #$XBH_AI_PATCH_MODIFY
        # 使用 ASCII 字符替代 Unicode 进度条字符，兼容 GBK/CMD 环境
        bar = '#' * filled + '-' * (bar_width - filled)
        #$XBH_AI_PATCH_END
        name = os.path.basename(self.filepath)[:15]

        #$XBH_AI_PATCH_START
        # sys.stdout.write(f"\r[{bar}] {self.last_percent}% {downloaded_str}/{total_str} {speed_str} {name}")
        # sys.stdout.flush()
        #$XBH_AI_PATCH_MODIFY
        # 使用 print 替代 sys.stdout.write，确保刷新和换行
        print(f"\r[{bar}] {self.last_percent}% {downloaded_str}/{total_str} {speed_str} {name}", end='', flush=True)
        #$XBH_AI_PATCH_END
    
    def download_chunk(self, start_pos, end_pos):
        try:
            req = urllib.request.Request(self.url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Range', f'bytes={start_pos}-{end_pos}')
            
            with urllib.request.urlopen(req) as response:
                with open(self.filepath, 'rb+') as f:
                    f.seek(start_pos)
                    while True:
                        block = response.read(1024 * 64)
                        if not block:
                            break
                        f.write(block)
                        self.update_progress(len(block))
            
            with self.lock:
                self.finished_chunks += 1
            
            return True
        except Exception as e:
            print(f"\n下载块失败 {start_pos}-{end_pos}: {e}")
            return False
    
    def download(self):
        self.total_size = self.get_file_size()
        
        if self.total_size == 0:
            return self._single_download()
        
        if self.total_size < 1024 * 1024:
            return self._single_download()
        
        chunk_size = self.total_size // self.num_threads
        
        chunks = []
        for i in range(self.num_threads):
            start_pos = i * chunk_size
            if i == self.num_threads - 1:
                end_pos = self.total_size - 1
            else:
                end_pos = (i + 1) * chunk_size - 1
            
            if start_pos >= self.total_size:
                break
            
            chunks.append((start_pos, end_pos))
        
        self.total_chunks = len(chunks)
        
        if len(chunks) == 1:
            return self._single_download()
        
        print(f"分块下载: {len(chunks)} 个块")
        
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        with open(self.filepath, 'wb') as f:
            f.seek(self.total_size - 1)
            f.write(b'\0')
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            results = list(executor.map(lambda c: self.download_chunk(c[0], c[1]), chunks))
        
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        return all(results)
    
    def _single_download(self):
        try:
            req = urllib.request.Request(self.url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req) as response:
                self.total_size = int(response.headers.get('Content-Length', 0))
                
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                
                with open(self.filepath, 'wb') as f:
                    while True:
                        block = response.read(1024 * 64)
                        if not block:
                            break
                        f.write(block)
                        self.update_progress(len(block))
                
                sys.stdout.write("\n")
                sys.stdout.flush()
                return True
        except Exception as e:
            print(f"\n下载失败: {e}")
            return False


def download_file_with_progress(args):
    key, value, local_path, num_threads = args
    filename = os.path.basename(value)
    escaped_value = encode_url(value)
    filepath = os.path.join(local_path, key, filename)
    
    print(f"开始下载: {filename}")
    
    downloader = MultiThreadDownloader(escaped_value, filepath, num_threads)
    success = downloader.download()
    
    if success:
        return (True, filename, downloader.total_size)
    else:
        return (False, filename, 0)


def auto_detect_server(task_name):
    print(f"正在自动检测服务器: {task_name}...")
    for server_key, api_url in SERVERS.items():
        try:
            url = f"{api_url}?taskName={task_name}"
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=5) as response:
                text = response.read().decode('utf-8').strip()
                if text and text != "null":
                    server_name = "广州" if server_key == "gz" else "长沙"
                    print(f"  -> 检测到 {server_name} 服务器 ({server_key})")
                    return server_key
        except Exception as e:
            print(f"  -> {server_key} 服务器不可用: {e}")
    return None


def main():
    config = load_config()
    cwd = os.getcwd()
    
    parser = argparse.ArgumentParser(description="Download task files")
    parser.add_argument("task_id", nargs="?", help="Task ID (e.g., PGZ_1773620515679)")
    parser.add_argument("-s", "--server", choices=["auto", "gz", "cs"], 
                        default=None, 
                        help="Server region: auto=自动识别, gz=广州, cs=长沙")
    parser.add_argument("-o", "--output", 
                        default=config.get("output", "."), 
                        help="Output directory (default: config.json or current directory)")
    parser.add_argument("-t", "--threads", type=int, 
                        default=config.get("threads", 8), 
                        help="Number of download threads per file (default: 8)")
    
    args = parser.parse_args()
    
    if not args.task_id:
        parser.print_help()
        return
    
    task_name = args.task_id
    
    server = args.server if args.server else config.get("server", "auto")
    
    if server == "auto":
        server = auto_detect_server(task_name)
        if not server:
            print("自动检测失败，请手动指定服务器 (-s gz 或 -s cs)")
            return
    
    output_path = args.output
    if output_path == ".":
        output_path = cwd
    
    local_path = os.path.abspath(output_path)
    num_threads = args.threads
    
    api_url = SERVERS[server]
    server_name = "广州" if server == "gz" else "长沙"
    
    print(f"任务ID: {task_name}")
    print(f"服务器: {server_name} ({server})")
    print(f"下载目录: {local_path}")
    print(f"线程数: {num_threads}")
    print("-" * 50)
    
    url = f"{api_url}?taskName={task_name}"
    
    try:
        with urllib.request.urlopen(url) as response:
            text = response.read().decode('utf-8')
    except Exception as e:
        print(f"获取任务信息失败: {e}")
        return
    
    pairs = text.split(';')
    download_tasks = []
    
    for pair in pairs:
        if not pair.strip():
            continue
        parts = pair.split(',', 1)
        if len(parts) == 2:
            key, value = parts
            download_tasks.append((key, value, local_path, num_threads))
    
    print(f"共 {len(download_tasks)} 个文件待下载\n")
    
    total_files = len(download_tasks)
    completed = 0
    success_count = 0
    total_size = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, total_files)) as executor:
        futures = [executor.submit(download_file_with_progress, task) for task in download_tasks]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result[0]:
                success_count += 1
                total_size += result[2]
            completed += 1
            print(f"\n进度: {completed}/{total_files} 文件已完成 ({format_size(total_size)} 已下载)")
    
    print("-" * 50)
    print(f"下载完成: {success_count}/{total_files} 文件成功 (共 {format_size(total_size)})")


if __name__ == "__main__":
    main()
