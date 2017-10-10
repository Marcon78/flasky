import os
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db
from app.models import Permission, User, Role, Post, Follow, Comment

COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage
    # branch=True 选项开启分支覆盖分析，
    # 除了跟踪哪行代码已经执行外，还要检查每个条件语句的 True 分支和 False 分支是否都执行了。
    # include 选项用来限制程序包中文件的分析范围，只对这些文件中的代码进行覆盖检测。
    COV = coverage.coverage(branch=True, include="app/*")
    COV.start()

app = create_app(os.getenv("FLASK_CONFIG") or "default")

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Post=Post, Follow=Follow,
                Permission=Permission, Comment=Comment)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)


# 在 Flask-Script 中，自定义命令很简单。
# 若想为 test 命令添加一个布尔值选项，只需在 test() 函数中添加一个布尔值参数即可。
# Flask-Script 根据参数名确定选项名，并据此向函数中传入 True 或False。
@manager.command
def test(coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get("FLASK_COVERAGE"):
        import sys
        # 为了检测的准确性，设定完环境变量 FLASK_COVERAGE 后，脚本会重启。
        # 再次运行时，脚本顶端的代码发现已经设定了环境变量，于是立即启动覆盖检测。
        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover("tests")
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print("Coverage Summary:")
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, "tmp/coverage")
        COV.html_report(directory=covdir)
        print("HTML version: file://%s/index.html" % covdir)
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app,
                                      restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import upgrade
    from app.models import Role, User

    # migrate database to latest revision
    upgrade()

    # create user roles
    Role.insert_roles()

    # create self-follows for all users
    User.add_self_follows()

if __name__ == "__main__":
    manager.run()
