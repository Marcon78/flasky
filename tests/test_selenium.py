import unittest
import re
import threading
import time
from selenium import webdriver
from app import create_app, db
from app.models import Role, User, Post

# default_port = 8080

class SeleniumTestCase(unittest.TestCase):
    client = None

    # setUpClass() 类方法在这个类中的全部测试运行前执行。
    @classmethod
    def setUpClass(cls):
        # start Firefox
        try:
            # 使用 Selenium 提供的 webdriver API 启动一个Firefox 实例。
            # cls.client = webdriver.Chrome()
            cls.client = webdriver.Firefox()
        except:
            pass

        # skip these tests if the browser could not be started
        if cls.client:
            # create the application
            cls.app = create_app("testing")
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # suppress logging to keep unittest output clean
            import logging
            logger = logging.getLogger("werkzeug")
            logger.setLevel("ERROR")

            # create the database and populate with some fake data
            db.create_all()
            Role.insert_roles()
            User.generate_fake(10)
            Post.generate_fake(10)

            # add an administrator user
            admin_role = Role.query.filter_by(permissions=0xff).first()
            admin = User(email="john@example.com",
                         username="john", password="cat",
                         role=admin_role, confirmed=True)
            db.session.add(admin)
            db.session.commit()

            # start the Flask server in a thread
            # threading.Thread(target=cls.app.run, kwargs={"port": default_port}).start()
            threading.Thread(target=cls.app.run).start()

            # give the server a second to ensure it is up
            time.sleep(1)

    # tearDownClass() 类方法在这个类中的全部测试运行后执行。
    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # stop the flask server and the browser
            # cls.client.get("http://localhost:%d/shutdown" % default_port)
            cls.client.get("http://localhost:5000/shutdown")
            cls.client.close()

            # destroy database
            db.session.remove()
            db.drop_all()

            # remove application context
            cls.app_context.pop()


    def setUp(self):
        if not self.client:
            self.skipTest("Web browser not available")

    def tearDown(self):
        pass

    def test_admin_home_page(self):
        # navigate to home page
        # self.client.get("http://localhost:%d/" % default_port)
        self.client.get("http://localhost:5000/")
        # 检查页面源码。
        self.assertTrue(re.search("Hello,\s+Stranger!", self.client.page_source))

        # navigate to login page
        # 试使用 find_element_by_link_text() 方法查找“Log In”链接，
        # 然后在这个链接上调用 click() 方法，从而在浏览器中触发一次真正的点击。
        self.client.find_element_by_link_text("Log In").click()
        self.assertTrue("<h1>Login</h1>" in self.client.page_source)

        # login
        # 使用 find_element_by_name() 方法通过名字找到表单中的电子邮件和密码字段，
        # 然后再使用 send_keys() 方法在各字段中填入值。
        self.client.find_element_by_name("email").send_keys("john@example.com")
        self.client.find_element_by_name("password").send_keys("cat")
        self.client.find_element_by_name("submit").click()
        self.assertTrue(re.search("Hello,\s+john!", self.client.page_source))

        # navigate to the user's profile page
        self.client.find_element_by_link_text("Profile").click()
        self.assertTrue("<h1>john</h1>" in self.client.page_source)
