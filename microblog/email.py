from threading import Thread
from flask import current_app
from flask_mail import Message
from microblog import mail



def send_async_email(app, msg):
                    # Using 'current_app' directly in this function that
                    # runs as a background thread would not have worked
                    # because 'current_app' is a context-aware variable
                    # that is 'tied to the thread' that is handling
                    # the client 'request'. In a 'different thread',
                    # 'current_app' would not have a value assigned.(*)

    with app.app_context():
    # the application context that is created here makes the application instance
    # accessible via 'current_app' variable from Flask.
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=mail.send, args=(current_app._get_current_object(), msg)).start()
                                    # (*) Passing 'current_app' directly as an argument
                                    # to the 'thread object' would not have worked either,
                                    # because 'current_app' is really a 'proxy object' that
                                    # is dynamically mapped to the 'application instance'.
                                    # So passing the 'proxy object' would be the same
                                    # as using 'current_app' directly in the 'thread'.

                                    # To access the 'real application instance' that
                                    # is stored inside the 'proxy object',
                                    # and pass that as the 'app' argument I need to
                                    # use: 'current_app._get_current_object' expression
                                    # which extracts the actual 'application instance'
                                    # from inside the proxy object.
