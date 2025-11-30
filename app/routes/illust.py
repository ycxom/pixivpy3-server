from flask import request, jsonify, send_file, g
from app.routes import api_bp
from app.auth import require_api_key
from app.pool import pool
from app.key_manager import key_manager
import tempfile
import os

def get_api():
    """根据 API Key 的池限制获取账号"""
    strategy = request.args.get("lb")
    
    # 获取当前请求的 API Key 值
    key_value = getattr(g, 'api_key_value', None)
    
    if key_value:
        # 获取该 Key 的池限制配置
        pool_mode, allowed_accounts = key_manager.get_allowed_accounts(key_value)
        if pool_mode:
            account = pool.get_account_for_key(pool_mode, allowed_accounts, strategy)
        else:
            # Key 不存在，使用默认行为
            account = pool.get_account(strategy)
    else:
        # 没有 API Key 上下文，使用默认行为
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
        # 创建临时目录，不使用 with 语句以避免文件锁定问题
        tmpdir = tempfile.mkdtemp()
        api.download(url, path=tmpdir)
        filename = os.path.basename(url)
        filepath = os.path.join(tmpdir, filename)
        
        # 读取文件内容到内存，然后删除临时文件
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        # 清理临时文件
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        
        # 从内存返回文件
        from io import BytesIO
        return send_file(
            BytesIO(file_data),
            mimetype="image/jpeg",
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
