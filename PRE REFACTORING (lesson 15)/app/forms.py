# most flask extentions use flask_name as their top level input
from flask_wtf import FlaskForm, RecaptchaField
# the below 4 are imported directly from wtforms, since the flask extention does not provide a custom version
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, \
    Length

from app.models import User


class LoginForm(FlaskForm):
    # we're using the flask WTF extentions which lets us create userforms
    # below variables will be the fields in our form
    username = StringField('Username', validators=[DataRequired()])
    # "validators" ensures field is not submitted empty
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    fav_animal = StringField('Favorite animal')
    submit = SubmitField('Register')

    # any methods created with validate_ upfront are taken by WTF addon as custom validators and are invoked in addition to stock validators above
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a diff username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a diff email.')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('submit')
    random_file = FileField('Random filez')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a diff username')


# used for follow and unfollow buttons. We swap the "submit" value in the user profile html page
class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[DataRequired(), Length(min=1, max=400)])
    submit = SubmitField('Submit')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class ChangeAttrForm(FlaskForm):
    attr = StringField('Attr:')
    submit = SubmitField('Submit')