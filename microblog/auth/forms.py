import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from microblog.models import User
from flask import flash


class LoginForm(FlaskForm): # they know how render themselves as HTML.
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    """When I add any methods that match the pattern 'validate_<field_name>',
    WTForms takes those as custom 'validators' and invokes them in addition to
    the stock 'validators'."""
    def validate_username(self, username):
        user = User.query.filter_by(username=self.username.data).first()
        if user is not None:
            raise ValidationError('Already used. Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('This email already has been used. Please use a different one.')

    # def validate_password(self, password):
    #     # there is problem w/ 'password'. 'HTML Input field' sent instead of password.
    #     pattern = re.compile(r'^(?=.*[a-zA-Z])(?=.*[0-9]+)\w{5,}$')
    #     flash(password)
    #     if not bool(pattern.search(str(password))):
    #         raise ValidationError(
    #             'The password should contain at least one'
    #             + ' letter and one digit and has at least length of 5'
    #         )


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Recover Password')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Submit')
