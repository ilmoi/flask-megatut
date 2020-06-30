# most flask extentions use flask_name as their top level input
from flask_wtf import FlaskForm, RecaptchaField
# the below 4 are imported directly from wtforms, since the flask extention does not provide a custom version
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, \
    Length

from app.models import User


class ChangeAttrForm(FlaskForm):
    attr = StringField('Attr:')
    submit = SubmitField('Submit')