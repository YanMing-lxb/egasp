import json
import time
import threading
import toml
import logging
import urllib.request
from rich import print
from pathlib import Path
from packaging import version
from datetime import timedelta
from platformdirs import user_cache_dir

from egasp.version import __project_name__, __version__


API_URL = f"https://api.github.com/repos/YanMing-lxb/{__project_name__}/releases/latest"


class UpdateChecker:

    def __init__(self, time_out, cache_time):
        self.logger = logging.getLogger(__name__)
        self.versions = []
        self.cache_time = cache_time * 3600
        self.time_out = time_out

        cache_path = Path(user_cache_dir(__project_name__, ensure_exists=True))
        self.cache_file = cache_path / f"{__project_name__}_version_cache.toml"
        
        self._thread = None
        self._result = None

    def _load_cached_version(self):
        try:
            cache_path = Path(self.cache_file)
            if not cache_path.exists():
                return None

            cache_time_remaining = round(self.cache_time - (time.time() - cache_path.stat().st_mtime), 4)
            delta = timedelta(seconds=cache_time_remaining)
            total_seconds = delta.total_seconds()
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)

            if cache_path.exists() and (cache_time_remaining > 0):
                with cache_path.open('r') as f:
                    data = toml.load(f)
                    self.logger.info(f"读取版本缓存文件中的版本号，缓存有效期: {int(hours):02} h {int(minutes):02} min {int(seconds):02} s")
                    self.logger.info("版本缓存文件路径: " + str(self.cache_file))
                    return data.get("latest_version")
        except Exception as e:
            self.logger.error("加载缓存版本时出错: " + str(e))
        return None

    def _update_version_cache(self, latest_version):
        try:
            with open(self.cache_file, 'w') as f:
                toml.dump({"latest_version": latest_version}, f)
        except Exception as e:
            self.logger.error("更新版本缓存时出错: " + str(e))

    def _get_latest_version(self, __project_name__, api_url):
        start_time = time.time()
        
        try:
            headers = {
                'User-Agent': f'{__project_name__} Update Checker',
                'Accept': 'application/vnd.github.v3+json'
            }
            req = urllib.request.Request(api_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=self.time_out) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if 'tag_name' not in data:
                    raise ValueError("Invalid GitHub API response")
                    
                latest_version = data['tag_name'].lstrip('v')
                parsed_version = version.parse(latest_version)
                
                self.logger.info("通过 GitHub API 获取最新版本成功")
                return parsed_version
                
        except urllib.error.HTTPError as e:
            if e.code == 403 and 'X-RateLimit-Remaining' in e.headers:
                reset_time = time.strftime("%Y-%m-%d %H:%M:%S", 
                    time.localtime(int(e.headers['X-RateLimit-Reset'])))
                self.logger.error(f"API速率限制，重置时间：{reset_time}")
            else:
                self.logger.error(f"请求失败，状态码：{e.code}")
        except json.JSONDecodeError:
            self.logger.error("响应数据解析失败")
        except KeyError:
            self.logger.error("响应中缺少版本信息")
        except Exception as e:
            self.logger.error(f"获取GitHub版本失败：{str(e)}")
        finally:
            self.logger.info(f"请求耗时：{time.time()-start_time} 秒")
        
        return None   

    def _check_for_updates_thread(self):
        """在后台线程中执行版本检查"""
        try:
            latest_version = self._load_cached_version()

            if latest_version:
                latest_version = version.parse(latest_version)
            else:
                latest_version = self._get_latest_version(__project_name__, API_URL)
                if latest_version:
                    self._update_version_cache(str(latest_version))
                else:
                    self._result = None
                    return

            current_version = version.parse(__version__)
            self._result = (current_version, latest_version)
        except Exception as e:
            self.logger.error(f"后台版本检查失败: {e}")
            self._result = None

    def check_for_updates_async(self):
        """异步启动版本检查"""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._check_for_updates_thread, daemon=True)
            self._thread.start()

    def check_for_updates(self):
        """同步检查更新（保持原有接口兼容性）"""
        latest_version = self._load_cached_version()

        if latest_version:
            latest_version = version.parse(latest_version)
        else:
            latest_version = self._get_latest_version(__project_name__, API_URL)
            if latest_version:
                self._update_version_cache(str(latest_version))
            else:
                return

        current_version = version.parse(__version__)

        if current_version < latest_version:
            print(f"有新版本可用: [bold green]{latest_version}[/bold green] " + f"当前版本: [bold red]{current_version}[/bold red]")
            print(f"python库请运行 [bold green]'pip install --upgrade {__project_name__}'[/bold green] 进行更新，独立可执行文件则请去 https://github.com/YanMing-lxb/egasp/releases/latest 下载")
        else:
            print(f"当前版本: [bold green]{current_version}[/bold green]")

    def get_async_result(self):
        """获取异步检查的结果并显示"""
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        if self._result is not None:
            current_version, latest_version = self._result
            if current_version < latest_version:
                print(f"\n有新版本可用: [bold green]{latest_version}[/bold green] " + f"当前版本: [bold red]{current_version}[/bold red]")
                print(f"python库请运行 [bold green]'pip install --upgrade {__project_name__}'[/bold green] 进行更新，独立可执行文件则请去 https://github.com/YanMing-lxb/egasp/releases/latest 下载")
            else:
                print(f"\n当前版本: [bold green]{current_version}[/bold green]")
