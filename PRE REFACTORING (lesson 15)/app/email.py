from threading import Thread

from flask_mail import Message

from flask import render_template

from app import mail, app


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


# allows us to send users arbitrary emails
def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # the mail server that we've instantiated in __init__ - we import it here
    # mail.send(msg)
    # multithreading this so that the app can keep working and not wait for the email send delay
    # notice that we're passing both the msg and the app to the async function
    # the app is needed because flask relies on contexts (applications context, request context) in order to function successfully
    # whenever we create a new thread, we need to pass an instance of the application s.t. create those contexts
    Thread(target=send_async_email, args=(app, msg)).start()

# specifically send password reset emails
def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(subject='hola pw reset',
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               # note how we can use render_template to generate email templates the same way we'd generate page tempaltes
               text_body=render_template('email/reset_password.txt', user=user, token=token),
               html_body=render_template('email/reset_password.html', user=user, token=token))
