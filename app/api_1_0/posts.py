from flask import request, current_app, url_for, jsonify, g
from . import api
from .. import db
from ..models import Permission, Post
from .errors import forbidden
from .decorators import permission_required

# [GET], 所有博客文章
@api.route("/posts/")
def get_posts():
    page = request.args.get("page", 1, type=int)
    pagination = Post.query.paginate(
        page=page,
        per_page=current_app.config["FLASKY_POSTS_PER_PAGE"],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_posts", page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_posts", page=page+1, _external=True)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev": prev,
        "next": next,
        "count": pagination.total
    })


# [GET], 一篇博客文章
@api.route("/posts/<int:id>")
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())


# [POST], 所有博客文章
@api.route("/posts/", methods=["POST"])
@permission_required(Permission.WRITE_ARTICLES)
def new_post():
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    # 为便于客户端操作，响应的主体中包含了新建的资源。
    # 如此一来，客户端就无需在创建资源后再立即发起一个GET 请求以获取资源。
    return jsonify(post.to_json()), 201, \
           {"Location": url_for("api.get_post", id=post.id, _external=True)}


# [PUT], 一篇博客文章
@api.route("/posts/<int:id>", methods=["PUT"])
@permission_required(Permission.WRITE_ARTICLES)
def edit_post(id):
    post = Post.query.get_or_404(id)
    if g.current_user != post.author or \
            not g.current_user.is_administrator():
        return forbidden("Insufficient permissions")
    post.body = request.json.get("body", post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())
