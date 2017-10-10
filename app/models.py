from datetime import datetime
from flask import current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_login import UserMixin, AnonymousUserMixin
from markdown import markdown
from . import db, lm
from .exceptions import ValidationError
import bleach


class Permission:
    FOLLOW            = 0x01    # 0b00000001：关注用户 —— 关注其他用户。
    COMMENT           = 0x02    # 0b00000010：在他人的文章中发表评论 —— 在他人撰写的文章中发布评论。
    WRITE_ARTICLES    = 0x04    # 0b00000100：写文章 —— 写原创文章。
    MODERATE_COMMENTS = 0x08    # 0b00001000：管理他人发表的评论 —— 查处他人发表的不当评论。
    ADMINISTER        = 0x80    # 0b10000000：管理员权限 —— 管理网站。
                                # 0b00000000（0x00）：匿名 —— 未登录的用户。在程序中只有阅读权限。
                                # 0b00000111（0x07）：用户 —— 具有发布文章、发表评论和关注其他用户的权限。这是新用户的默认角色。
                                # 0b00001111（0x0f）：协管员 —— 增加审查不当评论的权限。
                                # 0b11111111（0xff）：管理员 —— 具有所有权限，包括修改其他用户所属角色的权限。


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    # 位标志。各操作都对应一个位位置，能执行某项操作的角色，其位会被设为 1。
    permissions = db.Column(db.Integer)
    # relationship 的第一个参数表明这个关系的另一端是哪个模型；
    # backref 参数向 User 模型中添加一个 role 属性，从而定义反向关系；
    # lazy 参数指定如何加载相关记录。可选值有：
    #     select（首次访问时按需加载）
    #     immediate（源对象加载后就加载）
    #     joined（加载记录，但使用联结）
    #     subquery（立即加载，但使用子查询）
    #     noload（永不加载）
    #     dynamic（不加载记录，但提供加载记录的查询）
    users = db.relationship("User", backref="role", lazy="dynamic")

    @staticmethod
    def insert_roles():
        roles = {
            "User": (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            "Moderator": (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            "Administrator": (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            # role.permissions = roles[r][0]
            # role.default = roles[r][1]
            role.permissions, role.default = roles[r]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return "<Role %r>" % self.name


class Follow(db.Model):
    __tablename__ = "follows"
    # 联合主键
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    # 注意：datetime.utcnow 后面没有()，
    # 因为 db.Column() 的 default 参数可以接受函数作为默认值，
    # 所以每次需要生成默认值时，db.Column() 都会调用指定的函数。
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship("Post", backref="author", lazy="dynamic")
    # 为了消除外键间的歧义，定义关系时必须使用可选参数 foreign_keys 指定的外键。
    # 而且，db.backref() 参数并不是指定这两个关系之间的引用关系，而是回引Follow 模型。
    #
    # db.backref() 中的 lazy 设定为 "joined" 模式，就可在一次数据库查询中完成这些操作。
    # 如果把 lazy 设为默认值 "select"，那么首次访问 follower 和 followed 属性时才会加载对应的用户，
    # 而且每个属性都需要一个单独的查询，这就意味着获取全部被关注用户时需要增加 100 次额外的数据库查询。
    #
    # lazy 使用的是 dynamic，因此关系属性不会直接返回记录，而是返回查询对象，所以在执行查询之前还可以添加额外的过滤器。
    #
    # cascade 参数配置在父对象上执行的操作对相关对象的影响。
    followed = db.relationship("Follow",
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref("follower", lazy="joined"),
                               lazy="dynamic",
                               cascade="all, delete-orphan")
    followers = db.relationship("Follow",
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref("followed", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
    comments = db.relationship("Comment",
                               backref="author",
                               lazy="dynamic")

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        self.followed.append(Follow(followed=self))

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute.")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"confirm": self.id})

    def confirm(self, token):
        # 解密令牌时，无需 expires_in。
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("confirm") != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"reset": self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("reset") != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({"change_email": self.id, "new_email": new_email})

    def change_email(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("change_email") != self.id:
            return False
        new_email = data.get("new_email")
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        db.session.commit()
        return True

    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # followed_posts() 方法定义为属性，因此调用时无需加 ()。如此一来，所有关系的句法都一样了。
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    def to_json(self):
        json_user = {
            "url": url_for("api.get_user", id=self.id, _external=True),
            "username": self.username,
            "member_since": self.member_since,
            "last_seen": self.last_seen,
            "posts": url_for("api.get_user_posts", id=self.id, _external=True),
            "followed_posts": url_for("api.get_user_followed_posts", id=self.id, _external=True),
            "post_count": self.posts.count()
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.id}).decode('ascii')
        # return s.dumps({"id": self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data["id"])

    def __repr__(self):
        return "<User %r>" % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    comments = db.relationship("Comment", backref="post", lazy="dynamic")

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(100):
            u = User.query.offset(randint(0, user_count-1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym",
                        "b", "blockquote",
                        "code",
                        "em",
                        "i",
                        "li",
                        "ol",
                        "pre",
                        "strong",
                        "ul",
                        "h1", "h2", "h3",
                        "p"]
        # 由于 Markdown 规范没有为自动生成链接提供官方支持，
        # 因此需要使用由 Bleach 提供的 linkify() 函数把纯文本中的 URL 转换成适当的 <a> 链接。
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format="html"),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_post = {
            "url": url_for("api.get_post", id=self.id, _external=True),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author": url_for("api.get_user", id=self.author_id, _external=True),
            "comments": url_for("api.get_post_comments", id=self.id, _external=True),
            "comment_count": self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get("body")
        if body is None or body == "":
            # 在这种情况下，抛出异常才是处理错误的正确方式，
            # 因为 from_json() 方法并没有掌握处理问题的足够信息，唯有把错误交给调用者，由上层代码处理这个错误。
            raise ValidationError("post does not have a body")
        return Post(body=body)


# on_changed_body 函数注册在 Post 的 body 字段上，是 SQLAlchemy "set" 事件的监听程序，
# 这意味着只要这个类实例的 body 字段设了新值，函数就会自动被调用。
db.event.listen(Post.body, "set", Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

    @staticmethod
    def on_change_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym", "b", "code", "em", "i", "strong"]
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format="html"),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            "url": url_for("api.get_comment", id=self.id, _external=True),
            "post": url_for("api.get_post", id=self.post_id, _external=True),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author": url_for("api.get_user", id=self.author_id, _external=True)
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get("body")
        if body is None or body == "":
            raise ValidationError("comment does not have a body")
        return Comment(body=body)


# on_changed_body 函数注册在 Post 的 body 字段上，是 SQLAlchemy "set" 事件的监听程序，
# 这意味着只要这个类实例的 body 字段设了新值，函数就会自动被调用。
db.event.listen(Comment.body, "set", Comment.on_change_body)

# 将 AnonymousUser 设为用户未登录时 current_user 的值。
# 这样程序不用先检查用户是否登录，就能自由调用 current_user.can() 和 current_user.is_administrator()。
lm.anonymous_user = AnonymousUser


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
