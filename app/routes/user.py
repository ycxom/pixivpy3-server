from flask import request, jsonify
from app.routes import api_bp
from app.auth import require_api_key
from app.pool import pool

def get_api():
    strategy = request.args.get("lb")
    account = pool.get_account(strategy)
    if not account:
        return None, None
    return account.api, account.name

@api_bp.route("/user/<int:user_id>", methods=["GET"])
@require_api_key
def get_user_detail(user_id):
    """获取用户详情"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    try:
        result = api.user_detail(user_id)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/user/<int:user_id>/illusts", methods=["GET"])
@require_api_key
def get_user_illusts(user_id):
    """获取用户作品"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    offset = request.args.get("offset", 0, type=int)
    try:
        result = api.user_illusts(user_id, offset=offset)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
