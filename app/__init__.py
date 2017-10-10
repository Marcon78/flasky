from flask import Flask
from config import config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_mail import Mail
from flask_pagedown import PageDown

db = SQLAlchemy()
lm = LoginManager()
bootstrap = Bootstrap()
moment = Moment()
mail = Mail()
pagedown = PageDown()

lm.session_protection = "strong"
lm.login_view = "auth.login"    # 登录端点


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    lm.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    pagedown.init_app(app)

    # 注册蓝图
    from .main import main as blueprint_main
    app.register_blueprint(blueprint_main)

    from .auth import auth as blueprint_auth
    app.register_blueprint(blueprint_auth, url_prefix="/auth")

    from .api_1_0 import api as blueprint_api_1_0
    app.register_blueprint(blueprint_api_1_0, url_prefix="/api/v1.0")

    return app
