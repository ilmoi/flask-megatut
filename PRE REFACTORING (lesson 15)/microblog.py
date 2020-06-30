# to complete the application need to have a python script at top level that defines the flask application instance
from app import app, db
from app.models import User, Post


# this configures the flask shell command to have an instance of the app and db pre-imported
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}
