from flask import request, current_app, url_for, jsonify, g
from . import api
from ..models import User, Post


# [GET], 一个用户
@api.route("/users/<int:id>")
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


# [GET], 一个用户发布的博客文章
@api.route("/users/<int:id>/posts/")
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_user_posts", id=id, page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_user_posts", id=id, page=page+1, _external=True)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev": prev,
        "next": next,
        "count": pagination.total
    })


# [GET], 一个用户所关注用户发布的文章
@api.route("/users/<int:id>/timeline/")
def get_user_followed_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.followed_posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_user_followed_posts", id=id, page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_user_followed_posts", id=id, page=page+1, _external=True)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev": prev,
        "next": next,
        "count": pagination.total
    })
