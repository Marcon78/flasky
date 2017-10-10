from flask import jsonify
from app.exceptions import ValidationError
from . import api


def bad_request(msg):
    resp = jsonify({"error": "bad request", "message": msg})
    resp.status_code = 400
    return resp


def unauthorized(msg):
    resp = jsonify({"error": "unauthorized", "message": msg})
    resp.status_code = 401
    return resp


def forbidden(msg):
    resp = jsonify({"error": "forbidden", "message": msg})
    resp.status_code = 403
    return resp


# 使用 errorhandler 修饰器，
# 这个修饰器从 api 蓝本中调用，只有当处理蓝本中的路由时抛出了异常才会调用这个处理程序。
# 全局异常处理程序。处理 ValidationError 异常。
@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])
