import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # 'Flask-Migrate' uses 'Alembic' migration framework.
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel # 404.html and 500.html translated only.
from config import Config
from elasticsearch import Elasticsearch
from microblog import cli



db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'  # 'login' value is the function (endpoint) name for the login view.
                            # (why I have to add this?) - because 'Flask-Login' needs to know
                            # what is the view function that handles logins.
                            # (I don't understand. what 'login_view' does? Is it responsible for
                            # redirecting to the login page if user NOT LOGGED IN?)
                            # Yes it 'redirects' to the 'auth.login' otherwise if user is not logged in
                            # 'error 401' would be returned.
# login.login_message = 'Please log in to access this page'
                            # This message is generated as default by 'Flask-Login' extension when
                            # user w/o login tries access page that '@login_required'.
                            # Now, I may change the message which will be displayed.
                            # I could translate it: _l('above message bla bla bla').
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
babel = Babel() # info: 404.html and 500.html translated only



def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

    from microblog.errors import bp as errors_bp
    from microblog.auth import bp as auth_bp
    from microblog.main import bp as main_bp
    from microblog.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(errors_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)     #^ [optional] attach a 'blueprint' under a URL prefix.
                                        # Any 'routes' defined in this 'blueprint' get this prefix
                                        # in their URLs. So foregoing 'localhost:5000/login' doesn't
    cli.register(app)                   # work - instead I should use 'localhost:5000/auth/login'
                                        # despite in 'bp.route(/login)' there is still just '/login'.
    app.elasticsearch = ( Elasticsearch([app.config['ELASTICSEARCH_URL']])
                        if app.config['ELASTICSEARCH_URL'] else None )
        # in Python adding new attributes ('.elasticsearch') to the object
        # can be done at any time.
        # An alternative is to create a subclass of 'Flask' with the 'elasticsearch'
        # attribute defined in its '__init__()' function. (whatever that means...)
    #-------------------------------------------------------------------------------
    if not app.debug and not app.testing:
            # Enable 'email logger' if application is running w/o 'debug' mode.

        ## Sending server error notification via email :
        if app.config['MAIL_SERVER']: # Enable 'email logger' if 'email server' exists in the configuration.

            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()

            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr=f"no-reply@{app.config['MAIL_SERVER']}",
                toaddrs=app.config['ADMINS'],
                subject='Microblog Failure',
                credentials=auth,
                secure=secure,
            )

            mail_handler.setLevel(logging.ERROR)

            app.logger.addHandler(mail_handler) # Add 'mail_handler' to the application.

        ## Sending server error notification to file:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler('logs\\microblog.log',
                                        maxBytes=10240,
                                        backupCount=10 # keeps last 10 'log' files.
                                        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
        )

        file_handler.setLevel(logging.INFO)

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')
    #---------------------------------------------------------------------------

    return app


# Text translation:
@babel.localeselector
def get_locale(): # this decorated function is invoked for each request to select a language translation.
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])
                    # 'request' attribute that provides high-level interface to work with 'Accept-Language' header:
                    # (Accept-Language: da, en-gb;q=0.8, en;q=0.7)                          # the content of this
                    # - prefered Danish w/ weight 1, en-gb w/ weight 0.7..                  # header can be configured
                    # that clients send with a request: specifies the client                # by user in the browser's
                    # language settings in the computer's OS.                               # preferences page.
                                                                                            # The default is usually
                                                                                            # imported from the
                                                                                            # language settings in the
                                                                                            # computer's OS.



from microblog import models # defines the structure of the database.


# # To use 'flask shell' w/o need of importing everytime 'User', 'Post' and 'db'
# from microblog.models import User, Post, Message, Notification
# @app.shell_context_processor
# def make_shell_context():
#     return { 'db': db, 'User': User, 'Post': Post, 'Message': Message,
#           'Notification': Notification }
