from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from microblog.models import User



class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About Me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Apply')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('This username is already in use.')


class PostForm(FlaskForm):
    post = TextAreaField('Say something:', validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Send message')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])
    # I don't need to have 'Submit' button. 'ENTER' is sufficient here.

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
                # determines from where Flask-WTF gets form submission.
                # The default is 'request.form' which is where Flask puts values
                # submitted via 'POST request'. Via 'GET request' can be found
                # in 'request.args':
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
                # Token CSRF protection added to the for via 'form.hidden_tag()'.
            kwargs['csrf_enabled'] = False
                # This protection has to be 'disable' search to works here.
        super(SearchForm, self).__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(0, 240)])
    submit = SubmitField('Sent message')
