"""'View functions': are mapped to one or more route URLs so that Flask knows
what logic to execute when a client 'requests' a given URL."""

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse
from microblog import db
from microblog.auth import bp
from microblog.auth.forms import LoginForm, RegistrationForm
from microblog.auth.forms import ResetPasswordRequestForm, ResetPasswordForm
from microblog.models import User
from microblog.auth.email import send_password_reset_email



@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    u = form.username.data
    p = form.password.data
    r = form.remember_me.data

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
                                    #<blueprint name>.<view function name>
        login_user(user, remember=form.remember_me.data)
            # Registers the user as logged in, so that means that any future pages
            # the user navigates to will have the 'current_user' variable set to that user.
            # In the previous Blog it was resolved with 'session.set_cookies' and 'g.user'.
        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
                                # Prevent unsecure behaviour like inserting a URL
                                # to the a malicious site in the 'next' variable.
                                # So the application only redirects when the URL is relative.
                                                    # 'netloc' is a domain part of URL.
                                                    # From https://tools.ietf.org/html/rfc1808.html#section-2.1
                                                    # every URL should follow a specific format:
                                                    # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
                                                    # (what about 3rd party sites that allow shorten URL?)
            next_page = url_for('main.index')

        flash(f'POST method used. - user {u}, remember_me={r}, password={p}')
        flash(f'POST method used. - user {user, user.email, user.id}')
        return redirect(next_page)

    flash(f'{form.errors}')
    flash(f'GET method used.')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You Signed Up succesfully. Now you can login to our service.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)

        flash('Check you email for the instructions to reset your password')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('auth.index'))
    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been changed.')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)
