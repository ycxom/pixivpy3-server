import os
from flask import Flask, jsonify, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import config
from app.pool import pool
from app.key_manager import key_manager
from app.routes import api_bp
from app.routes.ui import ui_bp

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.getenv("SECRET_KEY", "pixiv-api-secret-key-change-me")
    
    # 支持 nginx 反向代理，正确处理 X-Forwarded-* 头
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # 注册蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(ui_bp)
    
    # 健康检查
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "accounts": len(pool.accounts)})
    
    # 根路径重定向到 UI
    @app.route("/")
    def index():
        return redirect("/ui/")
    
    return app

def main():
    # 加载账号池
    pool.load_from_config()
    
    # 加载 API Keys
    key_manager.load_from_config(config.api_keys)
    
    # 启动自动刷新（每50分钟刷新一次，Pixiv token 有效期约1小时）
    pool.start_auto_refresh(interval=3000)
    
    # 创建应用
    app = create_app()
    
    # 启动信息
    print("=" * 50)
    print("Pixiv API Server - Multi-Account Load Balancer")
    print(f"Host: {config.server.get('host', '0.0.0.0')}")
    print(f"Port: {config.server.get('port', 6523)}")
    print(f"Token (UI): Bearer {config.auth_token}")
    print(f"API Keys: {len(key_manager.list_keys())}")
    print(f"Strategy: {config.lb_strategy}")
    print(f"Accounts: {len(pool.accounts)}")
    print("=" * 50)
    
    host = config.server.get("host", "0.0.0.0")
    port = config.server.get("port", 6523)
    debug = config.server.get("debug", False)
    
    # 支持 IPv6: 使用 "::" 监听所有 IPv4 和 IPv6 地址
    # 或在 config.yaml 中设置 host: "::"
    if host == "0.0.0.0" and config.server.get("ipv6", False):
        host = "::"
    
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()
