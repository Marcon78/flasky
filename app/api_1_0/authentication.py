from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User, AnonymousUser
from . import api
from .errors import unauthorized, forbidden


auth = HTTPBasicAuth()


# Flask-HTTPAuth 不对验证用户密令所需的步骤做任何假设，因此所需的信息在回调函数中提供。
@auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == "":
        g.current_user = AnonymousUser()
        # return True
        return False
    if password == "":
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


# 如果认证密令不正确，服务器向客户端返回 401 错误。
# 默认情况下，Flask-HTTPAuth 自动生成这个状态码，
# 但为了和 API 返回的其他错误保持一致，可以自定义这个错误响应，
@auth.error_handler
def auth_error():
    return unauthorized("Invalid credentials")


# 在 before_request 处理程序中使用一次 login_required 修饰器，
# 应用到整个蓝本，api 蓝本中的所有路由都能进行自动认证。
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
            not g.current_user.confirmed:
        return forbidden("Unconfirmed account")


@api.route("/token")
def get_token():
    # 为了避免客户端使用旧令牌申请新令牌，
    # 要在视图函数中检查 g.token_used 变量的值，如果使用令牌进行认证就拒绝请求。
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized("Invalid credentials")
    return jsonify(
        {
            "token": g.current_user.generate_auth_token(expiration=3600),
            "expiration": 3600
        })
