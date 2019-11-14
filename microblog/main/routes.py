"""'View functions': are mapped to one or more route URLs so that Flask knows
what logic to execute when a client 'requests' a given URL."""

from datetime import datetime
from guess_language import guess_language
from flask import render_template, flash, redirect, url_for, request, g
from flask import current_app, jsonify
from flask_login import current_user, login_required
from flask_babel import get_locale
from microblog import db
from microblog.main import bp
from microblog.main.forms import EditProfileForm, PostForm, SearchForm, MessageForm
from microblog.models import User, Post, Message, Notification
from microblog.translate import translate



@bp.before_app_request # Executing a bit of generic logic ahead of a request being dispatched
                # to a view function is such a common task in web applications that
                # Flask offers it as a native feature ('@app.before_request').
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # In this point I don't need 'db.session.add()' because when I reference
        # 'current_user', Flask-Login invokes user loader callback function '@login.user_loader'
        # 'load_user' which runs a database query that puts the target user in the database session.
        # So I don't need to add the user again in this function because it is already there.
        db.session.commit()

        # 'Search' form should be in navigation bar, visible in all pages, so I need to
        # create instance of its class regardless of the page the user is viewing.
        # Instead of creating this 'SearchForm' object in every route and then passing
        # the form to all templates as an argument 'render_template(.. form=form)'
        # I'm going to store it in the 'g' container - this object exists during
        # all the life of a 'request'. When the 'before request handler' ends,
        # the 'g' object (and so my SearchForm) is alive. It is seen globally so
        # I don't need to add as argument in 'render_template()' calls.
        # ( there are different 'g' objects for different requests and clients ).
        g.search_form = SearchForm()

    # Configuration of localization (prefered language):
    g.locale = str(get_locale())
                    # decorated ('@babel.localeselector') function returning
                    # selected language and locale for a given request.
      # adding it to the 'g' object I can access it from the 'base' template:
      # 'moment.lang(g.locale)' adding to the 'block scripts'.



@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():

    form = PostForm()

    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash('Your message was posted succesfully!')
        return redirect(url_for('main.index'))
                # Why redirect instead of render_template...
                # because of refreshing issue in the browser.. bla...bla...blabla...
                # trick: POST/Redirect/GET pattern... To avoid inserting duplicate
                # posts when a user refreshes the page after submitting a web form.

    page = request.args.get('page', 1, type=int)
    posts = (
        current_user.followed_posts()
        .paginate(page, current_app.config['POSTS_PER_PAGE'], 0)
    )
    next_url = (
        url_for('main.index', page=posts.next_num)
        if posts.has_next else None
    )
    prev_url = (
        url_for('main.index', page=posts.prev_num)
        if posts.has_prev else None
    )

    return render_template('index.html', form=form, posts=posts.items,
                        next_url=next_url, prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
        page = request.args.get('page', 1, type=int)
        posts = (
            Post.query.order_by(Post.timestamp.desc())
            .paginate(page,current_app.config['POSTS_PER_PAGE'], False)
        )
        next_url = (
            url_for('main.explore', page=posts.next_num)
            if posts.has_next else None
        )
        prev_url = (
            url_for('main.explore', page=posts.prev_num)
            if posts.has_prev else None
        )

        return render_template('index.html', posts=posts.items,
                            next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = (
        user.posts.order_by(Post.timestamp.desc())
        .paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    )
    next_url = (
        url_for('main.user', username=user.username, page=posts.next_num)
        if posts.has_next else None
    )
    prev_url = (
        url_for('main.user', username=user.username, page=posts.prev_num)
        if posts.has_prev else None
    )

    return render_template('user.html', user=user, posts=posts.items,
                    next_url=next_url, prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():

    form = EditProfileForm(current_user.username)
                                # argument sends to '__init__' to set 'original_username'
                                # that will serve for future form validation after
                                # sent 'form' by user. (# main/forms.py --> EditProfileForm)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(f'User {username} not found.')
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself.')
        return redirect(url_for('main.index'))
    current_user.follow(user)
    db.session.commit()
    flash(f'You are following {username}!')
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(f'User {username} not found.')
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(f'You cannot unfollow yourself.')
        return redirect(url_for('main.index'))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You are not following {username}')
    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    """'jsonify' returns HTTP Response object."""
    return jsonify({'text': translate(
                                request.form['text'],
                                request.form['source_language'],
                                request.form['dest_language']
                                )# 'request.form' in this case will be sent to this function by JS.
    # outcome: translated text - is in form of HTTP Response object (client can get it by 'response['text']').
})


@bp.route('/search') # 'main.search' attached to the '/search' route, so that user can send
        # search request entering searching words under 'q' variable in URL (like in Google).
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    flash(request.args)
    page = request.args.get('page', 1, type=int)
    # 'g.search_form.q' - refers to the field named 'q' in the 'SearchForm' class in 'forms.py'
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = (
        url_for('main.search', q=g.search_form.q.data, page=page+1)
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    )
    prev_url = (
        url_for('main.search', q=g.search_form.q.data, page=page-1)
        if page > 1 else None
    )

    return render_template('search.html', posts=posts, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()

    return render_template('user_popup.html', user=user)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):

    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash('Your message has been sent.')
        return redirect(url_for('main.user', username=recipient))

    return render_template('send_message.html', form=form, recipient=recipient)


@bp.route('/message')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
                # above makes all messages sent before 'datetime.utcnow()'
                # percived as read.
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()

    # Take 'page' argument from URL:
    page = request.args.get('page', 1, type=int)

    messages = (
        current_user.get_messages()
        .order_by(Message.timestamp.desc())
        .paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    )

    next_url = (
        url_for('main.messages', page=messages.next_num)
        if messages.has_next else None
    )
    prev_url = (
        url_for('main.messages', page=messages.prev_num)
        if messages.has_prev else None
    )

    return render_template('messages.html', messages=messages.items,
                next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = (
        current_user.notifications
        .filter(Notification.timestamp > since)
        .order_by(Notification.timestamp.asc())
    )
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
        } for n in notifications])
