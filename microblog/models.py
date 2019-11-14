import os
import base64
from time import time
from datetime import datetime, timedelta
from hashlib import md5
import jwt, json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, url_for
from flask_login import UserMixin
from microblog import db, login
from microblog.search import add_to_index, remove_from_index, query_index



class SearchableMixin(object):

    @classmethod # method that is associated w/ the class and not particular instance.
    def search(cls, expression, page, per_page):

        ids, total = query_index(cls.__tablename__, expression, page, per_page)
                                    # convention: all indexes will be named
                                    # w/ the name Flask-SQLAlchemy assigned to the
                                    # relational table.
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))

        # Returns 'query' and 'total', NOT 'result of query' and 'total' (?)
        """>>>query, total = Post.search('word1 word2', 1, 5)
           >>>query.all()
           [<Post post1>, <Post post2> ...]
           >>>query
           <flask_sqlalchemy.BaseQuery object at 0x04261650>"""
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total
                                                            # 'case' statement ensures that the
                                                            # results from the database come in the
                                                            # same order as the IDs are given. This
                                                            # is important because Elasticsearch
                                                            # query returns results sorted from
                                                            # more to less relevant.
    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query: # equivalent of 'cls.query.all()' ?
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)



class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_page': resources.pages,
                'total_items': resources.total,
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page, **kwargs),
                'next': url_for(
                    endpoint, page=page+1, per_page=per_page, **kwargs)
                    if resources.has_next else None,
                'prev': url_for(
                    endpoint, page=page-1, per_page=per_page, **kwargs)
                    if resources.has_prev else None,
            },
        }
        return data




# Followers assosiation table:
"""This table is not declared as a model, like 'users' and 'posts' tables.
Since this is an auxiliary table that has no data other than 'ForeignKey'."""
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(PaginatedAPIMixin, UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # 'posts' field is not an actual database field, but a high-level view of the
    # relationship between users and posts. This field runs query, so:
    # 'user_name.posts' returns all the posts written by that user.
    posts = db.relationship('Post', backref='author', lazy='dynamic') # 'Post' refers to name of class.
                                    # defines the name of a field that will be added to
                                    # the objects of the 'many' class that points back at
                                    # the 'one' object. This adds 'post.author' expression
                                    # that returns the user given a post.
    followed = db.relationship(
    # SQLAlchemy allows to work with 'followed' relationship as if it was a list: user1.followed.append(user2)
                    'User', secondary=followers,
                    primaryjoin=(followers.c.follower_id == id),
                    secondaryjoin=(followers.c.followed_id == id),
                    backref=db.backref('followers', lazy='dynamic'),
                            # The current way of defining 'backref' is better than just 'backref='followers'
                            # because 'backref' created with the 'lazy="dynamic"' returns a query instead of
                            # the final results of the query. It is useful because I can expand the query before
                            # I execute it to obtain the results - e.x. I can ask that the results from the
                            # relationship come sorted in specific way.
                    lazy='dynamic'
                    )
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id', # I need this to specify which ForeignKey
                                    backref='author', lazy='dynamic') # to use for each relationship, because
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id', # this model has two identical
                                        backref='recipient', lazy='dynamic') # ForeignKeys. Because SQLAlchemy
    last_message_read_time = db.Column(db.DateTime)                          # has no way to know which one is
                                                                             # for 'sent' or 'received' messages.
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
                                                                        # is it good practice skip 'self'?
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self,user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0
                                # 'filter' is lower level to the 'filter_by'.
                                # 'filter_by' can only check for equality to a constant value.
                                # 'filter' can include arbitrary filtering conditions

    def followed_posts(self):
        followed = Post.query.join(
                followers, (followers.c.followed_id == Post.user_id)
                    # assosiation table
                                # 'join' condition.
            ).filter(followers.c.follower_id == self.id)

        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
                                                        # it's necessary because 'jwt.encode()'
                                                        # returns the token as a byte sequence.
                                                        # In application is more convenient
                                                        # to have token as a string.

    @staticmethod # it means that it can be invoked directly from the class.
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                algorithms=['HS256'])['reset_password'] # if invalid exception raises.
        except:
            return None
        return User.query.get(id)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900,1,1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def get_messages(self):
        own = Message.query.filter_by(author=self)
        return self.messages_received.union(own)

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        """I didn't 'db.session.commit()' here it is not good practice to commit
        in random places in the code. Commits are normally issued by high-level
        code such as a route handler.
        http://docs.sqlalchemy.org/en/latest/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it
        """
        return n

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + 'Z',
            'about_me': self.about_me,
            'post_count': self.posts.count(),
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
                'avatar': self.avatar(128),
            }
        }
        if include_email:
            data['email'] = self.email
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
            if new_user and 'password' in data:
                self.set_password(data['password'])

    def __repr__(self):
        return f'<User {self.username}>'



class Post(SearchableMixin, db.Model):
            # Now, I can use the 'reindex()' method to initialize the index
            # from all the posts currently in the database.
            # All methods of 'SearchableMixin' are now available in 'Post'.

    # Configuration refers to Elasticsearch Engine:
    """To implement 'Elasticsearch Engine' I decided that every model that needs
    indexing by 'Elasticsearch' needs to define a '__searchable__' class attribute
    (just variable) that lists the fields that need to be included in the index.
    It helps write my indexing functions in a generic way."""
    __searchable__ = ['body'] # it is just a variable, doesn't have any special behavior.
                            # This variable lets me determine what kind of field I'd
                            # like to scan. In this case I search text in 'body' column.

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
                                        # 'index=True' field is going to be indexed,
                                        # that is useful if I want to retrieve posts in chronological order.
                                        # (I don't understand why)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # 'user.id': 'user' is name of table.
                                                            # A model is given by its database table name,
                                                            # for which SQLAlchemy automatically uses lowercase
                                                            # characters and, for multi-word model names,
                                                            # snake case (snake_case).
    language = db.Column(db.String(5))


    def __repr__(self):
        return f'<Post {self.body}>'



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.body}'



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        """So that caller doesn't have to worry about JSON deserialization."""
        return json.loads(str(self.payload_json))



# Flask-Login knows nothing about databases therefore it expects that the
# application will configure a user 'loader function', that can be load a user ID:
@login.user_loader
def load_user(id):
    return User.query.get(int(id))
