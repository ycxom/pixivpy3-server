from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from app.routes import illust, user, pool_routes, key_routes
