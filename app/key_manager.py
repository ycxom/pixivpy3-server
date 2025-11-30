"""
API Key Manager - 管理 API 密钥的创建、验证和访问控制
"""
import secrets
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Tuple


@dataclass
class PoolRestriction:
    """账号池访问限制配置"""
    mode: str = "all"  # "all" | "specific"
    allowed_accounts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典用于序列化"""
        return {
            "mode": self.mode,
            "allowed_accounts": self.allowed_accounts.copy()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PoolRestriction":
        """从字典创建实例"""
        if data is None:
            return cls()
        return cls(
            mode=data.get("mode", "all"),
            allowed_accounts=data.get("allowed_accounts", []) or []
        )


@dataclass
class APIKey:
    """API 密钥数据模型"""
    name: str
    key: str
    access_mode: str = "blacklist"
    allowed_endpoints: List[str] = field(default_factory=list)
    denied_endpoints: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    enabled: bool = True
    pool_restriction: PoolRestriction = field(default_factory=PoolRestriction)

    def to_dict(self) -> dict:
        """转换为字典用于序列化"""
        return {
            "name": self.name,
            "key": self.key,
            "access_mode": self.access_mode,
            "allowed_endpoints": self.allowed_endpoints,
            "denied_endpoints": self.denied_endpoints,
            "created_at": self.created_at,
            "enabled": self.enabled,
            "pool_restriction": self.pool_restriction.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIKey":
        """从字典创建实例"""
        return cls(
            name=data.get("name", ""),
            key=data.get("key", ""),
            access_mode=data.get("access_mode", "blacklist"),
            allowed_endpoints=data.get("allowed_endpoints", []) or [],
            denied_endpoints=data.get("denied_endpoints", []) or [],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
            enabled=data.get("enabled", True),
            pool_restriction=PoolRestriction.from_dict(data.get("pool_restriction")),
        )


class KeyManager:
    """API 密钥管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._keys: List[APIKey] = []
        return cls._instance

    @staticmethod
    def generate_key() -> str:
        """生成 32 字符的随机 API Key，带 pk_ 前缀"""
        random_part = secrets.token_hex(16)
        return f"pk_{random_part}"

    def load_from_config(self, api_keys_data: List[dict]):
        """从配置数据加载 API Keys"""
        self._keys = [APIKey.from_dict(k) for k in (api_keys_data or [])]

    def list_keys(self) -> List[APIKey]:
        """列出所有 API Keys"""
        return self._keys.copy()

    def get_key(self, key_value: str) -> Optional[APIKey]:
        """根据 key 值获取 APIKey"""
        for k in self._keys:
            if k.key == key_value:
                return k
        return None

    def get_key_by_name(self, name: str) -> Optional[APIKey]:
        """根据名称获取 APIKey"""
        for k in self._keys:
            if k.name == name:
                return k
        return None

    def create_key(
        self,
        name: str,
        access_mode: str = "blacklist",
        allowed_endpoints: List[str] = None,
        denied_endpoints: List[str] = None,
        pool_mode: str = "all",
        allowed_accounts: List[str] = None,
    ) -> Tuple[Optional[APIKey], str]:
        """创建新的 API Key，返回 (api_key, error_message)"""
        if self.get_key_by_name(name):
            return None, "Key name already exists"

        if access_mode not in ("whitelist", "blacklist"):
            return None, "Invalid access mode"

        if pool_mode not in ("all", "specific"):
            return None, "Invalid pool mode"

        # 验证 specific 模式必须有账号
        if pool_mode == "specific" and not allowed_accounts:
            return None, "At least one account must be selected for specific mode"

        pool_restriction = PoolRestriction(
            mode=pool_mode,
            allowed_accounts=allowed_accounts or []
        )

        api_key = APIKey(
            name=name,
            key=self.generate_key(),
            access_mode=access_mode,
            allowed_endpoints=allowed_endpoints or [],
            denied_endpoints=denied_endpoints or [],
            pool_restriction=pool_restriction,
        )
        self._keys.append(api_key)
        self._save_to_config()
        return api_key, ""

    def update_key(
        self,
        name: str,
        access_mode: str = None,
        allowed_endpoints: List[str] = None,
        denied_endpoints: List[str] = None,
        enabled: bool = None,
        pool_mode: str = None,
        allowed_accounts: List[str] = None,
    ) -> Tuple[bool, str]:
        """更新 API Key 配置，返回 (success, error_message)"""
        api_key = self.get_key_by_name(name)
        if not api_key:
            return False, "Key not found"

        if access_mode is not None:
            if access_mode not in ("whitelist", "blacklist"):
                return False, "Invalid access mode"
            api_key.access_mode = access_mode

        if allowed_endpoints is not None:
            api_key.allowed_endpoints = allowed_endpoints

        if denied_endpoints is not None:
            api_key.denied_endpoints = denied_endpoints

        if enabled is not None:
            api_key.enabled = enabled

        # 处理池限制更新
        if pool_mode is not None:
            if pool_mode not in ("all", "specific"):
                return False, "Invalid pool mode"
            
            # 如果更新为 specific 模式，检查是否有账号
            new_accounts = allowed_accounts if allowed_accounts is not None else api_key.pool_restriction.allowed_accounts
            if pool_mode == "specific" and not new_accounts:
                return False, "At least one account must be selected for specific mode"
            
            api_key.pool_restriction.mode = pool_mode
            if allowed_accounts is not None:
                api_key.pool_restriction.allowed_accounts = allowed_accounts
        elif allowed_accounts is not None:
            # 仅更新账号列表
            if api_key.pool_restriction.mode == "specific" and not allowed_accounts:
                return False, "At least one account must be selected for specific mode"
            api_key.pool_restriction.allowed_accounts = allowed_accounts

        self._save_to_config()
        return True, ""

    def delete_key(self, name: str) -> bool:
        """删除 API Key"""
        api_key = self.get_key_by_name(name)
        if not api_key:
            return False

        self._keys.remove(api_key)
        self._save_to_config()
        return True

    def get_allowed_accounts(self, key_value: str) -> Tuple[Optional[str], List[str]]:
        """获取 API Key 的账号池限制配置，返回 (mode, allowed_account_names)"""
        api_key = self.get_key(key_value)
        if not api_key:
            return None, []
        return api_key.pool_restriction.mode, api_key.pool_restriction.allowed_accounts.copy()

    def remove_account_from_all_keys(self, account_name: str):
        """从所有 API Key 的 allowed_accounts 中移除指定账号"""
        for api_key in self._keys:
            if account_name in api_key.pool_restriction.allowed_accounts:
                api_key.pool_restriction.allowed_accounts.remove(account_name)
        self._save_to_config()

    def check_access(self, key_value: str, endpoint: str) -> Tuple[bool, str]:
        """检查 API Key 是否有权访问指定端点"""
        # 每次检查时从配置重新加载，确保配置变更立即生效
        self._reload_from_config()
        
        api_key = self.get_key(key_value)

        if not api_key:
            return False, "Invalid API key"

        if not api_key.enabled:
            return False, "API key is disabled"

        normalized_endpoint = self._normalize_endpoint(endpoint)

        if api_key.access_mode == "whitelist":
            if self._match_endpoint(normalized_endpoint, api_key.allowed_endpoints):
                return True, ""
            return False, "Access denied to this endpoint"
        else:
            if self._match_endpoint(normalized_endpoint, api_key.denied_endpoints):
                return False, "Access denied to this endpoint"
            return True, ""
    
    def _reload_from_config(self):
        """从配置文件重新加载 API Keys"""
        from app.config import config
        config.reload()
        self._keys = [APIKey.from_dict(k) for k in (config.api_keys or [])]

    def _normalize_endpoint(self, endpoint: str) -> str:
        """规范化端点路径，移除动态参数"""
        normalized = re.sub(r"/\d+", "/<id>", endpoint)
        normalized = normalized.split("?")[0]
        return normalized

    def _match_endpoint(self, endpoint: str, patterns: List[str]) -> bool:
        """检查端点是否匹配任一模式"""
        for pattern in patterns:
            if pattern.endswith("/*"):
                prefix = pattern[:-1]
                if endpoint.startswith(prefix):
                    return True
            elif pattern == endpoint:
                return True
        return False

    def _save_to_config(self):
        """保存到配置文件"""
        from app.config import config

        config.set_api_keys([k.to_dict() for k in self._keys])


key_manager = KeyManager()
