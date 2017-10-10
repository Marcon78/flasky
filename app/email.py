from threading import Thread
from flask import render_template, current_app
from flask_mail import Message
from . import mail


def send_async_email(app, msg):
    # flask_mail 中的 send() 函数使用 current_app，因此必须激活程序上下文。
    # 不过，在不同线程中执行 mail.send() 函数时，程序上下文要使用 app.app_context() 人工创建。
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    # 变量 current_app 是通过线程内的本地代理对象(LocalProxy)实现的，实际上是一个轻度包装，
    # 需要调用 _get_current_object() 来获取真正的应用对象。
    app = current_app._get_current_object()
    msg = Message(subject=app.config["FLASKY_MAIL_SUBJECT_PREFIX"] + " " + subject,
                  sender=app.config["FLASKY_MAIL_SENDER"],
                  recipients=[to])
    msg.body = render_template(template + ".txt", **kwargs)
    msg.html = render_template(template + ".html", **kwargs)

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()

    return thr
