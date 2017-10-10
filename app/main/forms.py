from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField, ValidationError, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, Regexp
from flask_pagedown.fields import PageDownField
from ..models import User, Role


class NameForm(FlaskForm):
    name = StringField("What is your name?", validators=[DataRequired()])
    submit = SubmitField("Submit")


class EditProfileForm(FlaskForm):
    name = StringField("Real name", validators=[Length(0, 64)])
    location = StringField("Location", validators=[Length(0, 64)])
    about_me = TextAreaField("About me")
    submit = SubmitField("Submit")


class EditProfileAdminForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(),
                                             Length(1, 64),
                                             Email()])
    username = StringField("Username", validators=[DataRequired(),
                                                   Length(1, 64),
                                                   Regexp("^[a-zA-Z][a-zA-Z0-9_.]*$",
                                                          message="Usernames must have only letters, numbers, "
                                                                  "dots or underscores.")])
    confirmed = BooleanField("Confirmed")
    # SelectField 实例必须在其 choices 属性中设置各选项。
    # 选项必须是一个由元组组成的列表，各元组都包含两个元素：选项的标识符和显示在控件中的文本字符串。
    # 元组中的标识符是角色的id，
    # 因为这是个整数，所以在 SelectField 构造函数中添加 coerce=int 参数，从而把字段的值转换为整数，而不使用默认的字符串。
    role = SelectField("Role", coerce=int)
    name = StringField("Real name", validators=[Length(0, 64)])
    location = StringField("Location", validators=[Length(0, 64)])
    about_me = TextAreaField("About me")
    submit = SubmitField("Submit")
    
    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.field_by(email=field.data).first():
            raise ValidationError("Email already registered.")

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.field_by(username=field.data).first():
            raise ValidationError("Username already in use.")


class PostForm(FlaskForm):
    # body = TextAreaField("What's on your mind?", validators=[DataRequired()])
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField("Submit")


class CommentForm(FlaskForm):
    body = StringField("Enter your comment", validators=[DataRequired()])
    submit = SubmitField("Submit")
