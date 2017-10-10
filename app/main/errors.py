from flask import render_template, request, jsonify
from . import main


# 注册程序全局的错误处理程序
@main.app_errorhandler(403)
def forbidden(e):
    # 在错误处理程序中根据客户端请求的格式改写响应，这种技术称为“内容协商”。
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        resp = jsonify({"error": "forbidden"})
        resp.status_code = 403
        return resp
    return render_template("403.html"), 403


@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        resp = jsonify({"error": "not found"})
        resp.status_code = 404
        return resp
    # return render_template("../templates/404.html"), 404
    return render_template("404.html"), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        resp = jsonify({"error": "internal server error"})
        resp.status_code = 500
        return resp
    # return render_template("../templates/500.html"), 500
    return render_template("500.html"), 500
