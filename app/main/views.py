from flask import render_template, redirect, flash, url_for, request, current_app, abort, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from .. import db
from ..models import User, Role, Post, Comment, Permission
from ..decorators import admin_required, permission_required


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config["FLASKY_SLOW_DB_QUERY_TIME"]:
            current_app.logger.warning(
                "Slow query: %s\nParameters: %s\nDuration: %f\nContext: %s\n"
                % (query.statement,
                   query.parameters,
                   query.duration,
                   query.context)
            )
    return response


@main.route("/shutdown")
def server_shutdown():
    if not current_app.testing:
        abort(404)  # Not Found
    # 调用 Werkzeug 在环境中提供的关闭函数。
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if not shutdown:
        abort(500)  # Internal Server Error
    shutdown()
    return "Shutting down..."


@main.route("/", methods=["GET", "POST"])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        # current_user 是一个轻度包装。
        # 数据库需要真正的用户对象，因此要调用 _get_current_object() 方法。
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for(".index"))
    # 渲染的页数从请求的查询字符串（request.args）中获取，如果没有明确指定，则默认渲染第一页。
    # 参数 type=int 保证参数无法转换成整数时，返回默认值。
    page = request.args.get("page", 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        # cookie 以request.cookies 字典的形式存储在请求对象中。
        show_followed = bool(request.cookies.get("show_followed", ""))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    # error_out 参数，当其设为 True 时（默认值），如果请求的页数超出了范围，则会返回404 错误；
    # 如果设为 False，页数超出范围时会返回一个空列表。
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"],
        error_out=False)
    posts = pagination.items
    return render_template("index.html", form=form, posts=posts,
                           show_followed=show_followed,
                           pagination=pagination)


@main.route("/user/<username>")
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    # user.posts 返回的是查询对象，因此可在其上调用过滤器。
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template("user.html", user=user, posts=posts)


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash("Your profile has been updated.")
        return redirect(url_for(".user", username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form)


@main.route("/edit-profile/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash("The profile has been updated.")
        return redirect(url_for(".user", username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template("edit_profile.html", form=form, user=user)


@main.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been published.")
        # 在 url_for() 函数的参数中把 page 设为 -1，用来请求评论的最后一页。
        return redirect(url_for(".post", id=post.id, page=-1))
    page = request.args.get("page", 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config["FLASKY_COMMENTS_PER_PAGE"] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"],
        error_out=False
    )
    comments = pagination.items
    # 注意，post.html 模板接收一个列表作为参数，这个列表就是要渲染的文章。
    return render_template("post.html", posts=[post], form=form,
                           comments=comments, pagination=pagination)


@main.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author_id and \
            not current_user.is_administrator():
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash("The post has been updated.")
        return redirect(url_for(".post", id=post.id))
    form.body.data = post.body
    return render_template("edit_post.html", form=form)


@main.route("/follow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    if current_user.is_following(user):
        flash("You are already following this user.")
        return redirect(url_for(".user", username=username))
    current_user.follow(user)
    flash("You are now following %s." % username)
    return redirect(url_for(".user", username=username))


@main.route("/unfollow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    if not current_user.is_following(user):
        flash("You are not following this user.")
        return redirect(url_for(".user", username=username))
    current_user.unfollow(user)
    flash("You are not following %s anymore." % username)
    return redirect(url_for(".user", username=username))


@main.route("/followers/<username>")
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    page = request.args.get("page", 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"],
        error_out=False
    )
    follows = [{"user": item.follower, "timestamp": item.timestamp}
               for item in pagination.items]
    return render_template("followers.html",
                           user=user,
                           title="Followers of",
                           endpoint=".followers",
                           pagination=pagination,
                           follows=follows)


@main.route("/followed_by/<username>")
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("Invalid user.")
        return redirect(".index")
    page = request.args.get("page", 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"],
        error_out=False
    )
    follows = [{"user": item.followed, "timestamp": item.timestamp}
               for item in pagination.items]
    return render_template("followers.html",
                           user=user,
                           title="Followed by",
                           endpoint=".followed_by",
                           pagination=pagination,
                           follows=follows)


@main.route("/all")
@login_required
def show_all():
    # cookie 只能在响应对象中设置，因此要使用 make_response()方法创建响应对象。
    resp = make_response(redirect(url_for(".index")))
    # 可选的 max_age 参数设置 cookie 的过期时间，单位为秒。
    # 如果不指定参数 max_age，浏览器关闭后 cookie 就会过期。
    # resp.set_cookie("show_followed", "", max_age=30*24*60*60)
    resp.set_cookie("show_followed", "")
    return resp


@main.route("/followed")
@login_required
def show_followed():
    resp = make_response(redirect(url_for(".index")))
    # resp.set_cookie("show_followed", "1", max_age=30*24*60*60)
    resp.set_cookie("show_followed", "1")
    return resp


@main.route("/moderate")
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get("page", 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"],
        error_out=False)
    comments = pagination.items
    return render_template("moderate.html", comments=comments, pagination=pagination, page=page)


@main.route("/moderate/enable/<int:id>")
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for(".moderate", page=request.args.get("page", 1, type=int)))


@main.route("/moderate/disable/<int:id>")
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for(".moderate", page=request.args.get("page", 1, type=int)))
