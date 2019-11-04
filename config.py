import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

"""Use class to store configuration variables is very good idea.
As the application needs more configuration items, they can be added to this
class, and later if I find that I need to have more than one configuration set,
I can create subclasses of it."""

"""It is in general a good practice to set configuration from environment variables,
and provide a fallback value when the environment does not define the variable.
os.environ.get('variable_name')"""

class Config(object):
    """Below variables can be reached by: 'app.config['variable']'."""

    # SECRET_KEY is also used as a cryptographic key to generate signatures or tokens.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'blablabla'
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'microblog.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail - error notification:
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['blabla@op.pl']

    # Pagination:
    POSTS_PER_PAGE = 5

    # Text Translation:
    LANGUAGES = ['en', 'es', 'pl']

    YANDEX_TRANSLATION_KEY = os.environ.get('YANDEX_TRANSLATION_KEY')

    # Full-Text Search Engine:
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
