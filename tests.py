from datetime import datetime, timedelta
import unittest
from microblog import create_app, db
from microblog.models import User, Post
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
                # Flask uses two context:
                # (1) application context (current_app, g)
                # (2) request context (request, session as well as Flask-Login's current_user)
                    # It is activated right before a request is handled.
        self.app_context.push() # push 'app_context' - brings 'current app' and 'g' to life.
                                # When the 'request' is complete, the 'context' is removed,
                                # along with these variables.
        db.create_all() # Creates all the database tables.
                        # It uses 'current_app.config' (that was created when I pushed an
                        # application context for the application instance)
                        # to know where is the database.

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


    def test_password_hashing(self):
        u = User(username='test')
        u.set_password('test')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('test'))

    def test_avatar(self):
        u = User(username='john', email='john@gexample.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                        '93bb94201b62f74f4cc21109a8fe29bf'
                                        '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='test1', email='test1@gmail.com')
        u2 = User(username='test2', email='test2@gmail.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'test2')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'test1')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_post(self):
        # Create four users:
        u1 = User(username='test1', email='test1@gmail.com')
        u2 = User(username='test2', email='test2@gmail.com')
        u3 = User(username='test3', email='test3@gmail.com')
        u4 = User(username='test4', email='test4@gmail.com')
        db.session.add_all([u1, u2, u3, u4])

        # Create four posts:
        now = datetime.utcnow()
        p1 = Post(body='post from test1', author=u1,
                timestamp=now+timedelta(seconds=1))
        p2 = Post(body='post from test2', author=u2,
                timestamp=now+timedelta(seconds=4))
        p3 = Post(body='post from test3', author=u3,
                timestamp=now+timedelta(seconds=3))
        p4 = Post(body='post from test4', author=u4,
                timestamp=now+timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # Setup the followers:
        u1.follow(u2) # 'test1' follows 'test2'
        u1.follow(u4) # 'test1' follows 'test4'
        u2.follow(u3) # 'test2' follows 'test3'
        u3.follow(u4) # 'test3' follows 'test4'
        db.session.commit()

        # Check the followed posts of each user:
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])


if __name__ == '__main__':
    unittest.main(verbosity=2)
