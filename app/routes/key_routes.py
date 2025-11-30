"""
API Key 管理路由 - 仅管理员可访问（使用 Token 认证）
"""
from flask import request, jsonify
from app.routes import api_bp
from app.auth import require_auth
from app.key_manager import key_manager
from app.pool import pool


@api_bp.route("/keys", methods=["GET"])
@require_auth
def list_keys():
    """列出所有 API Keys"""
    keys = key_manager.list_keys()
    return jsonify({
        "keys": [
            {
                "name": k.name,
                "key": k.key[:10] + "..." + k.key[-4:],  # 部分隐藏
                "key_full": k.key,  # 完整 key（管理员可见）
                "access_mode": k.access_mode,
                "allowed_endpoints": k.allowed_endpoints,
                "denied_endpoints": k.denied_endpoints,
                "created_at": k.created_at,
                "enabled": k.enabled,
                "pool_restriction": k.pool_restriction.to_dict()
            }
            for k in keys
        ]
    })


@api_bp.route("/keys", methods=["POST"])
@require_auth
def create_key():
    """创建新的 API Key"""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    
    if not name:
        return jsonify({"error": "Key name is required"}), 400
    
    access_mode = data.get("access_mode", "blacklist")
    if access_mode not in ("whitelist", "blacklist"):
        return jsonify({"error": "Invalid access mode"}), 400
    
    allowed_endpoints = data.get("allowed_endpoints", [])
    denied_endpoints = data.get("denied_endpoints", [])
    
    # 池限制参数
    pool_mode = data.get("pool_mode", "all")
    allowed_accounts = data.get("allowed_accounts", [])
    
    api_key, error = key_manager.create_key(
        name=name,
        access_mode=access_mode,
        allowed_endpoints=allowed_endpoints,
        denied_endpoints=denied_endpoints,
        pool_mode=pool_mode,
        allowed_accounts=allowed_accounts
    )
    
    if not api_key:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "success": True,
        "key": {
            "name": api_key.name,
            "key": api_key.key,
            "access_mode": api_key.access_mode,
            "created_at": api_key.created_at,
            "pool_restriction": api_key.pool_restriction.to_dict()
        }
    })


@api_bp.route("/keys/<name>", methods=["PUT"])
@require_auth
def update_key(name):
    """更新 API Key 配置"""
    data = request.get_json() or {}
    
    access_mode = data.get("access_mode")
    if access_mode and access_mode not in ("whitelist", "blacklist"):
        return jsonify({"error": "Invalid access mode"}), 400
    
    success, error = key_manager.update_key(
        name=name,
        access_mode=access_mode,
        allowed_endpoints=data.get("allowed_endpoints"),
        denied_endpoints=data.get("denied_endpoints"),
        enabled=data.get("enabled"),
        pool_mode=data.get("pool_mode"),
        allowed_accounts=data.get("allowed_accounts")
    )
    
    if not success:
        status_code = 404 if error == "Key not found" else 400
        return jsonify({"error": error}), status_code
    
    return jsonify({"success": True})


@api_bp.route("/keys/<name>", methods=["DELETE"])
@require_auth
def delete_key(name):
    """删除 API Key"""
    success = key_manager.delete_key(name)
    
    if not success:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({"success": True})


@api_bp.route("/pool/accounts", methods=["GET"])
@require_auth
def get_pool_accounts():
    """获取账号池中所有可用账号名称"""
    account_names = pool.get_available_account_names()
    return jsonify({
        "accounts": account_names
    })
