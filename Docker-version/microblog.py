# to complete the application need to have a python script at top level that defines the flask application instance
from app import create_app, db, cli
from app.models import User, Post, Task, Message, Notification

app = create_app()
cli.register(app)

# this configures the flask shell command to have an instance of the app and db pre-imported
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post, 'Task': Task,
            'Message': Message, 'Notification': Notification}
