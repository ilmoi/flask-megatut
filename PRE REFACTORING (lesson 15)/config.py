import os

# get directory for this file
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # you don't have to store in a class but this is considered good practice
    # later you can subclass it
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-enver-guess'

    # sql alchemy is another flask extention, except this time for managing databases
    # it's an ORM that allows us to work with native python objects instead of writing raw sql
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

    # the below disables the events feature of sql alchemy, that would otherwise signal the applivation every time there is a change to the db
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # to get emails about errors
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['emailgoeshere@gmail.com']

    # pagination
    POSTS_PER_PAGE = 2

    # language support - decided not to implement
    # LANGUAGES = ['en', 'es']

    # key for msft translator
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')