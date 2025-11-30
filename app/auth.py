from functools import wraps
from flask import request, jsonify, g
from app.config import config


def require_auth(f):
    """Token 鉴权装饰器 - 用于 UI 控制台和管理接口"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token != f"Bearer {config.auth_token}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def require_api_key(f):
    """API Key 鉴权装饰器 - 用于 API 调用"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.key_manager import key_manager
        
        auth_header = request.headers.get("Authorization", "")
        
        # 提取 API Key
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "API key required"}), 401
        
        key_value = auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 检查访问权限
        endpoint = request.path
        allowed, error = key_manager.check_access(key_value, endpoint)
        
        if not allowed:
            if error in ("Invalid API key", "API key is disabled"):
                return jsonify({"error": error}), 401
            return jsonify({"error": error}), 403
        
        # 将 API Key 值存储到请求上下文，供后续使用
        g.api_key_value = key_value
        
        return f(*args, **kwargs)
    return decorated
