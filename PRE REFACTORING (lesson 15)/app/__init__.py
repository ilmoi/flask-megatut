import logging
import os
from logging.handlers import SMTPHandler, RotatingFileHandler

from flask import Flask, request
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment

from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# create the application object as an instance of class Flask
# passing name almost always configures flask in the right way
app = Flask(__name__)

# load the config variables
app.config.from_object(Config)

# instantiate the db and the migration instance
# most extentions are initialized in a similar way
db = SQLAlchemy(app)

# flask migrate sits on top of Alembic, a migration framework that allows you to update the db without having to recreate it from scratch
# to do this it maintains a repository with migration scripts, each describing change from previous version
# flask-migrate exposes it's command through flask's cli, specifically through "flask db"
migrate = Migrate(app, db)

# extention that enables user logins
login = LoginManager(app)
login.login_view = 'log1n' # for certain pages flask can redirect users to login before showing them. for that flask needs to know at what url the login view is

# to be able to send users emails
mail = Mail(app)

# to make things pretty:)
bootstrap = Bootstrap(app)

# to display time correctly and nicely back to the user
moment = Moment(app)

# i18n and t10n - DECIDED TO SKIP FOR NOW TOO MUCH CHANGE
# babel = Babel(app)
# @babel.localeselector  # this decorator is invoked for each request to select an appropriate language translation
# def get_locale():
#     # accept_languages allows us to work with the Accept-Languages HTTP header, which advertises which languages the client is able to understand, and which locale variant is preferred.
#     # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language
#     # best_match finds the best language from babel library to match the preferred languages of the user specified above
#     return request.accept_languages.best_match(app.config['LANGUAGES'])

# routes = self expl
# models = defines structure of the database
from app import routes, models, errors

# to be able to send myself emails with errors
# flask already has the ability to send emails we just need to build the SMTP handler
if not app.debug:
    if app.config['MAIL_SERVER']:
        # security settings
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()

        # create the handler
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Microblog Failure',
            credentials=auth, secure=secure)

        # only handle errors and above
        mail_handler.setLevel(logging.ERROR)

        # attach
        app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
          os.mkdir('logs')
        # rotates the logs s.t. each file max 10kb and only 10 last files kept
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
          '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')