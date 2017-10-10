import unittest
import json
from base64 import b64encode
from flask import url_for
from app import create_app, db
from app.models import Role, User


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # 辅助方法。
    # 返回所有请求都要发送的通用首部，其中包含认证密令和 MIME 类型相关的首部。
    def get_api_headers(self, username, password):
        return {
            "Authorization": "Basic " + b64encode(
                (username + ":" + password).encode("utf-8")).decode("utf-8"),
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def test_no_auth(self):
        resp = self.client.get(url_for("api.get_posts"),
                               content_type="application/json")
        self.assertTrue(resp.status_code == 401)    # Unauthorized

    def test_posts(self):
        # add a user
        r = Role.query.filter_by(name="User").first()
        self.assertIsNotNone(r)
        u = User(email="john@example.com",
                 password="cat",
                 confirmed=True,
                 role=r)
        db.session.add(u)
        db.session.commit()

        # 所有请求主体中发送的数据都要使用 json.dumps() 方法进行编码，
        # 因为 Flask 测试客户端不会自动编码 JSON 格式数据。
        # 类似地，返回的响应主体也是 JSON 格式，处理之前必须使用 json.loads() 方法解码。

        # write an empty post
        resp = self.client.post(url_for("api.new_post"),
                                headers=self.get_api_headers("john@example.com", "cat"),
                                data=json.dumps({"body": ""}))
        self.assertTrue(resp.status_code == 400)    # Bad Request

        # write a post
        resp = self.client.post(url_for("api.new_post"),
                                headers=self.get_api_headers("john@example.com", "cat"),
                                data=json.dumps({
                                    "body": "body of the *blog* post"
                                }))
        self.assertTrue(resp.status_code == 201)    # Created
        url = resp.headers.get("Location")  # Location 中包含了新建的资源，参考 new_post 的 API 设计。
        self.assertIsNotNone(url)

        # get the new post
        resp = self.client.get(url,
                               headers=self.get_api_headers("john@example.com", "cat"))
        self.assertTrue(resp.status_code == 200)    # OK
        json_resp = json.loads(resp.data.decode("utf-8"))
        self.assertTrue(json_resp["url"] == url)
        self.assertTrue(json_resp["body"] == "body of the *blog* post")
        self.assertTrue(json_resp["body_html"] == "<p>body of the <em>blog</em> post</p>")
        json_post = json_resp

        # get the post from the user
        resp = self.client.get(url_for("api.get_user_posts", id=u.id),
                               headers=self.get_api_headers("john@example.com", "cat"))
        self.assertTrue(resp.status_code == 200)    # OK
        json_resp = json.loads(resp.data.decode("utf-8"))
        self.assertIsNotNone(json_resp.get("posts"))
        self.assertTrue(json_resp.get("count", 0) == 1)
        self.assertTrue(json_resp["posts"][0] == json_post)
