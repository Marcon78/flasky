import re
import unittest
from flask import url_for
from app import create_app, db
from app.models import Role, User


class FlaskClientTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        resp = self.client.get(url_for("main.index"))
        # self.assertTrue(b"Stranger" in resp.data)
        # 注意，默认情况下 get_data() 得到的响应主体是一个字节数组，
        # 传入参数 as_text=True 后得到的是一个更易于处理的 Unicode 字符串。
        self.assertTrue("Strange" in resp.get_data(as_text=True))

    def test_register_and_login(self):
        # register a new account
        resp = self.client.post(url_for("auth.register"),
                                data={
                                    "email": "john@example.com",
                                    "username": "john",
                                    "password": "cat",
                                    "password2": "cat"
                                })
        # 检查响应的状态码是否为 302，这个代码表示重定向。
        self.assertTrue(resp.status_code == 302)

        # login with the new account
        # 参数 follow_redirects=True，让测试客户端和浏览器一样，自动向重定向的 URL 发起 GET 请求。
        # 指定这个参数后，返回的不是 302 状态码，而是请求重定向的 URL 返回的响应。
        resp = self.client.post(url_for("auth.login"),
                                data={
                                    "email": "john@example.com",
                                    "password": "cat"
                                },
                                follow_redirects=True)
        # 直接搜索字符串'Hello, john!' 并没有用，因为这个字符串由动态部分和静态部分组成，而且两部分之间有额外的空白。
        # 为了避免测试时空白引起的问题，使用更为灵活的正则表达式。
        self.assertTrue(re.search(b"Hello,\s+john!", resp.data))
        # self.assertTrue(re.search("Hello,\s+john!", resp.data))
        self.assertTrue(b"You have not confirmed your account yet" in resp.data)
        # self.assertTrue("You have not confirmed your account yet" in resp.data)

        # send a confirmation token
        user = User.query.filter_by(email="john@example.com").first()
        token = user.generate_confirmation_token()
        resp = self.client.get(url_for("auth.confirm", token=token),
                               follow_redirects=True)
        self.assertTrue(b"You have confirmed your account" in resp.data)
        # self.assertTrue("You have confirmed your account" in resp.data)

        # log out
        resp = self.client.get(url_for("auth.logout"),
                               follow_redirects=True)
        self.assertTrue(b"You have been logged out" in resp.data)
        # self.assertTrue("You have been logged out" in resp.data)
