from flask import request, jsonify, send_file
from app.routes import api_bp
from app.auth import require_api_key
from app.pool import pool
import tempfile
import os

def get_api():
    strategy = request.args.get("lb")
    account = pool.get_account(strategy)
    if not account:
        return None, None
    return account.api, account.name

@api_bp.route("/illust/<int:illust_id>", methods=["GET"])
@require_api_key
def get_illust(illust_id):
    """获取插画详情"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    try:
        result = api.illust_detail(illust_id)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/search", methods=["GET"])
@require_api_key
def search_illust():
    """搜索插画"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    word = request.args.get("word", "")
    offset = request.args.get("offset", 0, type=int)
    try:
        result = api.search_illust(word, offset=offset)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/ranking", methods=["GET"])
@require_api_key
def get_ranking():
    """获取排行榜"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    mode = request.args.get("mode", "day")
    offset = request.args.get("offset", 0, type=int)
    try:
        result = api.illust_ranking(mode=mode, offset=offset)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/recommended", methods=["GET"])
@require_api_key
def get_recommended():
    """获取推荐插画"""
    api, name = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    offset = request.args.get("offset", 0, type=int)
    try:
        result = api.illust_recommended(offset=offset)
        result["_account"] = name
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/download", methods=["GET"])
@require_api_key
def download_image():
    """下载图片"""
    api, _ = get_api()
    if not api:
        return jsonify({"error": "No available account"}), 503
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            api.download(url, path=tmpdir)
            filename = os.path.basename(url)
            filepath = os.path.join(tmpdir, filename)
            return send_file(filepath, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
