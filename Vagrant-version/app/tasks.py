import json
import logging
import sys
import time

from flask import render_template, send_file, jsonify, url_for
from rq import get_current_job
from werkzeug.utils import redirect

from app import create_app, db

# because this is going to run in a separate process, we need to instantiate flask-sql-alchemy (to write to db) and flask-mail (to send an email to the user)
# and for that we need an instance of our app
from app.email import send_email
from app.models import Task, User, Post

app = create_app()
app.app_context().push()

logging.basicConfig(filename='rq.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        # write & save the % completion to meta dictionary in redis
        job.meta['progress'] = progress
        job.save_meta()

        task = Task.query.get(job.get_id())  # get task from db
        # SKIPPING NOTIFICATIONS BECAUSE I DIDN'T IMPLEMENT THEM
        # task.user.add_notifications('task_progress', {'task_id': job.get_id(), 'progress': progress})
        if progress >= 100:
            task.complete = True #set it as true if done
        db.session.commit() #finally commit to db


def export_posts(user_id):
    # because this process is run by RQ not by flask, we need to manually handle exceptions.
    # otherwise, unless we're watching the RQ logs all the time, we won't know that this has completed
    try:
        # read user posts from db
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            data.append({'body': post.body,
                         'timestamp': post.timestamp.isoformat() + 'Z'}) #z means UTC
            time.sleep(5) #fake adding time
            i += 1
            logging.debug(f"i is {i}, progress is {i//total_posts}")
            _set_task_progress(100 * i // total_posts)

        # send email with data to user
        # send_email('[Microblog] Your blog posts',
        #         sender=app.config['ADMINS'][0], recipients=[user.email],
        #         text_body=render_template('email/export_posts.txt', user=user),
        #         html_body=render_template('email/export_posts.html', user=user),
        #         attachments=[('posts.json', 'application/json',
        #                       json.dumps({'posts': data}, indent=4))],
        #         sync=True)
        # redirect(url_for('main.display_posts', data=data))

        # doesn't work coz we're doing from worker
        # print('sending file...')
        # return send_file('cli.py', as_attachment=True,
        #                  attachment_filename='cli.py')
        # _set_task_progress(100)
        # return data
    except:
        # log the error by collecting traceback info
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        # mark progress to 100 and task as completed
        _set_task_progress(100)


# def example(seconds):
#     # redis stuff - fetch current job
#     job = get_current_job()
#
#     print('starting task')
#     for i in range(seconds):
#
#         # redis stuff - log progress on every second
#         job.meta['progress'] = 100.0 * i / seconds
#         job.save_meta()
#
#         print(i)
#         time.sleep(1)
#
#     # redis stuff - final progress log
#     job.meta['progress'] = 100
#     job.save_meta()
#
#     print('task completed')