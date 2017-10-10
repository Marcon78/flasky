from flask import Blueprint

main = Blueprint("main", __name__)

from . import views, errors
from ..models import Permission


# 为了避免每次调用 render_template() 时都多添加一个模板参数，可以使用上下文处理器。
# 上下文处理器能让变量 Permission 在所有模板中全局可访问。
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
