"""
API Key Manager 单元测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.key_manager import APIKey, KeyManager


class TestAPIKey:
    """测试 APIKey 数据类"""
    
    def test_create_api_key(self):
        """测试创建 API Key"""
        key = APIKey(name="test", key="pk_abc123")
        assert key.name == "test"
        assert key.key == "pk_abc123"
        assert key.access_mode == "blacklist"
        assert key.enabled is True
    
    def test_to_dict(self):
        """测试序列化为字典"""
        key = APIKey(
            name="test",
            key="pk_abc123",
            access_mode="whitelist",
            allowed_endpoints=["/api/search"],
            denied_endpoints=[]
        )
        d = key.to_dict()
        assert d["name"] == "test"
        assert d["key"] == "pk_abc123"
        assert d["access_mode"] == "whitelist"
        assert d["allowed_endpoints"] == ["/api/search"]
    
    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "name": "test",
            "key": "pk_xyz789",
            "access_mode": "blacklist",
            "allowed_endpoints": [],
            "denied_endpoints": ["/api/download"],
            "enabled": False
        }
        key = APIKey.from_dict(data)
        assert key.name == "test"
        assert key.key == "pk_xyz789"
        assert key.access_mode == "blacklist"
        assert key.denied_endpoints == ["/api/download"]
        assert key.enabled is False


class TestKeyManager:
    """测试 KeyManager 类"""
    
    @pytest.fixture
    def manager(self):
        """创建测试用的 KeyManager"""
        # 重置单例
        KeyManager._instance = None
        km = KeyManager()
        km._keys = []
        # Mock _save_to_config 避免实际写入文件
        km._save_to_config = lambda: None
        return km
    
    def test_generate_key(self, manager):
        """测试生成 Key"""
        key = manager.generate_key()
        assert key.startswith("pk_")
        assert len(key) == 35  # pk_ + 32 hex chars
    
    def test_generate_key_uniqueness(self, manager):
        """测试生成的 Key 唯一性"""
        keys = [manager.generate_key() for _ in range(100)]
        assert len(set(keys)) == 100  # 所有 key 都应该唯一
    
    def test_create_key(self, manager):
        """测试创建 Key"""
        key = manager.create_key("test_key")
        assert key is not None
        assert key.name == "test_key"
        assert key.key.startswith("pk_")
        assert len(manager.list_keys()) == 1
    
    def test_create_duplicate_key(self, manager):
        """测试创建重复名称的 Key"""
        manager.create_key("test_key")
        result = manager.create_key("test_key")
        assert result is None
        assert len(manager.list_keys()) == 1
    
    def test_create_key_invalid_mode(self, manager):
        """测试创建无效访问模式的 Key"""
        result = manager.create_key("test", access_mode="invalid")
        assert result is None
    
    def test_get_key(self, manager):
        """测试获取 Key"""
        created = manager.create_key("test_key")
        found = manager.get_key(created.key)
        assert found is not None
        assert found.name == "test_key"
    
    def test_get_key_not_found(self, manager):
        """测试获取不存在的 Key"""
        result = manager.get_key("pk_nonexistent")
        assert result is None
    
    def test_delete_key(self, manager):
        """测试删除 Key"""
        manager.create_key("test_key")
        assert len(manager.list_keys()) == 1
        result = manager.delete_key("test_key")
        assert result is True
        assert len(manager.list_keys()) == 0
    
    def test_delete_key_not_found(self, manager):
        """测试删除不存在的 Key"""
        result = manager.delete_key("nonexistent")
        assert result is False
    
    def test_update_key(self, manager):
        """测试更新 Key"""
        manager.create_key("test_key", access_mode="blacklist")
        result = manager.update_key("test_key", access_mode="whitelist")
        assert result is True
        key = manager.get_key_by_name("test_key")
        assert key.access_mode == "whitelist"
    
    def test_update_key_endpoints(self, manager):
        """测试更新 Key 端点列表"""
        manager.create_key("test_key")
        manager.update_key("test_key", allowed_endpoints=["/api/search"])
        key = manager.get_key_by_name("test_key")
        assert key.allowed_endpoints == ["/api/search"]


class TestAccessControl:
    """测试访问控制逻辑"""
    
    @pytest.fixture
    def manager(self):
        """创建测试用的 KeyManager"""
        KeyManager._instance = None
        km = KeyManager()
        km._keys = []
        km._save_to_config = lambda: None
        return km
    
    def test_whitelist_allowed(self, manager):
        """测试白名单模式 - 允许的端点"""
        key = manager.create_key(
            "test",
            access_mode="whitelist",
            allowed_endpoints=["/api/search", "/api/ranking"]
        )
        allowed, error = manager.check_access(key.key, "/api/search")
        assert allowed is True
        assert error == ""
    
    def test_whitelist_denied(self, manager):
        """测试白名单模式 - 不允许的端点"""
        key = manager.create_key(
            "test",
            access_mode="whitelist",
            allowed_endpoints=["/api/search"]
        )
        allowed, error = manager.check_access(key.key, "/api/download")
        assert allowed is False
        assert "denied" in error.lower()
    
    def test_blacklist_allowed(self, manager):
        """测试黑名单模式 - 允许的端点"""
        key = manager.create_key(
            "test",
            access_mode="blacklist",
            denied_endpoints=["/api/download"]
        )
        allowed, error = manager.check_access(key.key, "/api/search")
        assert allowed is True
    
    def test_blacklist_denied(self, manager):
        """测试黑名单模式 - 禁止的端点"""
        key = manager.create_key(
            "test",
            access_mode="blacklist",
            denied_endpoints=["/api/download"]
        )
        allowed, error = manager.check_access(key.key, "/api/download")
        assert allowed is False
    
    def test_invalid_key(self, manager):
        """测试无效 Key"""
        allowed, error = manager.check_access("pk_invalid", "/api/search")
        assert allowed is False
        assert "Invalid" in error
    
    def test_disabled_key(self, manager):
        """测试禁用的 Key"""
        key = manager.create_key("test")
        manager.update_key("test", enabled=False)
        allowed, error = manager.check_access(key.key, "/api/search")
        assert allowed is False
        assert "disabled" in error.lower()
    
    def test_wildcard_endpoint(self, manager):
        """测试通配符端点匹配"""
        key = manager.create_key(
            "test",
            access_mode="blacklist",
            denied_endpoints=["/api/proxy/*"]
        )
        allowed, error = manager.check_access(key.key, "/api/proxy/status")
        assert allowed is False
    
    def test_normalize_endpoint(self, manager):
        """测试端点规范化"""
        key = manager.create_key(
            "test",
            access_mode="whitelist",
            allowed_endpoints=["/api/illust/<id>"]
        )
        # /api/illust/12345 应该被规范化为 /api/illust/<id>
        allowed, error = manager.check_access(key.key, "/api/illust/12345")
        assert allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
