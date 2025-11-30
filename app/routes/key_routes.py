"""
API Key 管理路由 - 仅管理员可访问（使用 Token 认证）
"""
from flask import request, jsonify
from app.routes import api_bp
from app.auth import require_auth
from app.key_manager import key_manager


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
                "enabled": k.enabled
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
    
    api_key = key_manager.create_key(
        name=name,
        access_mode=access_mode,
        allowed_endpoints=allowed_endpoints,
        denied_endpoints=denied_endpoints
    )
    
    if not api_key:
        return jsonify({"error": "Key name already exists"}), 400
    
    return jsonify({
        "success": True,
        "key": {
            "name": api_key.name,
            "key": api_key.key,
            "access_mode": api_key.access_mode,
            "created_at": api_key.created_at
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
    
    success = key_manager.update_key(
        name=name,
        access_mode=access_mode,
        allowed_endpoints=data.get("allowed_endpoints"),
        denied_endpoints=data.get("denied_endpoints"),
        enabled=data.get("enabled")
    )
    
    if not success:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({"success": True})


@api_bp.route("/keys/<name>", methods=["DELETE"])
@require_auth
def delete_key(name):
    """删除 API Key"""
    success = key_manager.delete_key(name)
    
    if not success:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({"success": True})
