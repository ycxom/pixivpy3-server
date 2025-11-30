import threading
import time
from pathlib import Path
from pixivpy3 import AppPixivAPI
from app.config import config
from app.gppt_auth import gppt_auth, GPPT_AVAILABLE


def get_proxy_settings():
    """获取代理配置"""
    proxy_cfg = config._data.get("proxy", {})
    if not proxy_cfg.get("enabled", False):
        return None
    
    http_proxy = proxy_cfg.get("http", "")
    https_proxy = proxy_cfg.get("https", "") or http_proxy
    
    if http_proxy:
        return {
            "http": http_proxy,
            "https": https_proxy
        }
    return None


class ProxiedAppPixivAPI(AppPixivAPI):
    """支持代理的 AppPixivAPI"""
    
    def set_proxy(self, proxies):
        """设置代理"""
        if proxies:
            self.requests_kwargs = {"proxies": proxies}
            print(f"[Pixiv] Proxy set: {proxies}")
        else:
            self.requests_kwargs = {}


class PixivAccount:
    """单个 Pixiv 账号"""
    def __init__(self, name, refresh_token=None, username=None, password=None):
        self.name = name
        self.refresh_token = refresh_token
        self.username = username
        self.password = password
        self.api = ProxiedAppPixivAPI()
        # 设置代理
        self.api.set_proxy(get_proxy_settings())
        self.request_count = 0
        self.last_request_time = 0
        self.last_refresh_time = 0  # 上次刷新 token 的时间
        self.lock = threading.Lock()
        self.authenticated = False
    
    def auth(self, auto_gppt=False):
        """
        认证账号
        auto_gppt: 是否自动尝试 gppt 登录（启动时为 False，手动添加时为 True）
        """
        # 优先使用 refresh_token
        if self.refresh_token:
            if self._auth_with_token(self.refresh_token):
                return True
        
        # 尝试从缓存获取 token
        if self.username:
            cached = gppt_auth.get_cached_token(self.username)
            if cached and self._auth_with_token(cached):
                self.refresh_token = cached
                return True
        
        # 仅在 auto_gppt=True 时尝试 gppt 登录
        if auto_gppt and self.username and self.password and GPPT_AVAILABLE:
            return self._auth_with_gppt()
        
        return False
    
    def _auth_with_token(self, token):
        try:
            self.api.auth(refresh_token=token)
            self.authenticated = True
            self.last_refresh_time = time.time()
            # 更新 refresh_token（pixivpy3 认证后会更新）
            if hasattr(self.api, 'refresh_token') and self.api.refresh_token:
                self.refresh_token = self.api.refresh_token
            print(f"[Pool] Account [{self.name}] authenticated with token")
            return True
        except Exception as e:
            print(f"[Pool] Account [{self.name}] token auth failed: {e}")
            self.authenticated = False
            return False
    
    def _auth_with_gppt(self):
        gppt_config = config._data.get("gppt", {})
        headless = gppt_config.get("headless", True)
        
        print(f"[Pool] Account [{self.name}] trying gppt login...")
        if headless:
            token, err = gppt_auth.login_headless(self.username, self.password)
        else:
            token, err = gppt_auth.login_with_credentials(self.username, self.password)
        
        if token:
            self.refresh_token = token
            return self._auth_with_token(token)
        
        print(f"[Pool] Account [{self.name}] gppt login failed: {err}")
        return False
    
    def refresh(self):
        """刷新 token"""
        # 先尝试用 pixivpy3 自带的刷新
        if self.refresh_token:
            if self._auth_with_token(self.refresh_token):
                return True
        
        # 如果失败，尝试用 gppt 刷新
        if self.refresh_token and GPPT_AVAILABLE:
            new_token, err = gppt_auth.refresh_token(self.refresh_token)
            if new_token:
                self.refresh_token = new_token
                return self._auth_with_token(new_token)
        return False
    
    def check_and_refresh(self, refresh_interval=3500):
        """
        检查并刷新 token
        refresh_interval: 刷新间隔（秒），默认约1小时（Pixiv token 有效期约1小时）
        """
        if time.time() - self.last_refresh_time > refresh_interval:
            print(f"[Pool] Account [{self.name}] token may expire, refreshing...")
            return self.refresh()
        return True
    
    def record_request(self):
        with self.lock:
            self.request_count += 1
            self.last_request_time = time.time()

class AccountPool:
    """多账号负载均衡池"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pool()
        return cls._instance
    
    def _init_pool(self):
        self.accounts = []
        self.lock = threading.Lock()
        self.index = 0

    def load_from_config(self):
        """从 config.yaml 加载账号"""
        # 初始化 gppt 缓存目录
        gppt_config = config._data.get("gppt", {})
        if gppt_config.get("enabled", False):
            cache_dir = gppt_config.get("token_cache_dir", "./tokens")
            gppt_auth.cache_dir = Path(cache_dir)
            gppt_auth.cache_dir.mkdir(exist_ok=True)
        
        # 从 config.yaml 加载
        for acc in config.pixiv_accounts:
            if acc.get("enabled", True):
                self.add_account(
                    refresh_token=acc.get("refresh_token"),
                    name=acc.get("name"),
                    username=acc.get("username"),
                    password=acc.get("password"),
                    save=False  # 启动时不重复保存
                )
        
        print(f"[Pool] Loaded {len(self.accounts)} accounts from config.yaml")
    
    def add_account(self, refresh_token=None, name=None, username=None, password=None, auto_gppt=False, save=True):
        """
        添加账号
        auto_gppt: 是否自动尝试 gppt 登录
        save: 是否保存到 config.yaml
        """
        name = name or f"account_{len(self.accounts)}"
        account = PixivAccount(name, refresh_token, username, password)
        if account.auth(auto_gppt=auto_gppt):
            self.accounts.append(account)
            if save:
                config.add_account(name, account.refresh_token, username)
            return True
        return False
    
    def update_proxy(self):
        """更新所有账号的代理设置"""
        proxies = get_proxy_settings()
        for acc in self.accounts:
            acc.api.set_proxy(proxies)
        print(f"[Pool] Updated proxy for {len(self.accounts)} accounts")
    
    def remove_account(self, name):
        with self.lock:
            self.accounts = [a for a in self.accounts if a.name != name]
        config.remove_account(name)
        # 从所有 API Key 的 allowed_accounts 中移除该账号
        from app.key_manager import key_manager
        key_manager.remove_account_from_all_keys(name)

    def get_available_account_names(self):
        """获取所有可用账号名称列表"""
        return [a.name for a in self.accounts if a.authenticated]
    
    def get_account(self, strategy=None):
        """获取账号（支持多种策略）"""
        if not self.accounts:
            return None
        
        strategy = strategy or config.lb_strategy
        
        if strategy == "least_used":
            return self._get_least_used()
        return self._get_round_robin()

    def get_account_for_key(self, pool_mode, allowed_accounts, strategy=None):
        """
        根据 API Key 的池限制获取账号
        pool_mode: "all" 或 "specific"
        allowed_accounts: 允许的账号名称列表（仅 specific 模式有效）
        strategy: 负载均衡策略
        """
        # 获取可用账号列表
        if pool_mode == "all":
            available = [a for a in self.accounts if a.authenticated]
        else:
            # specific 模式：仅使用允许的账号
            available = [a for a in self.accounts if a.authenticated and a.name in allowed_accounts]
        
        if not available:
            return None
        
        strategy = strategy or config.lb_strategy
        
        if strategy == "least_used":
            return self._get_least_used_from(available)
        return self._get_round_robin_from(available)

    def _get_round_robin_from(self, accounts):
        """从指定账号列表中轮询获取"""
        with self.lock:
            account = accounts[self.index % len(accounts)]
            self.index += 1
        account.check_and_refresh()
        account.record_request()
        return account

    def _get_least_used_from(self, accounts):
        """从指定账号列表中获取最少使用的"""
        with self.lock:
            account = min(accounts, key=lambda a: a.request_count)
        account.check_and_refresh()
        account.record_request()
        return account
    
    def _get_round_robin(self):
        with self.lock:
            account = self.accounts[self.index % len(self.accounts)]
            self.index += 1
        # 检查并刷新 token
        account.check_and_refresh()
        account.record_request()
        return account
    
    def _get_least_used(self):
        with self.lock:
            account = min(self.accounts, key=lambda a: a.request_count)
        # 检查并刷新 token
        account.check_and_refresh()
        account.record_request()
        return account
    
    def status(self):
        return [{
            "name": a.name,
            "authenticated": a.authenticated,
            "request_count": a.request_count,
            "last_request": a.last_request_time,
            "has_credentials": bool(a.username)
        } for a in self.accounts]
    
    def refresh_account(self, name):
        """刷新指定账号的 token"""
        for acc in self.accounts:
            if acc.name == name:
                if acc.refresh():
                    # 刷新成功后更新配置文件
                    config.add_account(acc.name, acc.refresh_token, acc.username)
                    return True
        return False
    
    def refresh_all(self):
        """刷新所有账号的 token"""
        success = 0
        for acc in self.accounts:
            if acc.refresh():
                config.add_account(acc.name, acc.refresh_token, acc.username)
                success += 1
        print(f"[Pool] Refreshed {success}/{len(self.accounts)} accounts")
        return success
    
    def start_auto_refresh(self, interval=3000):
        """
        启动自动刷新任务
        interval: 刷新间隔（秒），默认50分钟
        """
        import threading
        
        def refresh_loop():
            while True:
                time.sleep(interval)
                print(f"[Pool] Auto refresh triggered")
                self.refresh_all()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        print(f"[Pool] Auto refresh started, interval: {interval}s")

pool = AccountPool()
