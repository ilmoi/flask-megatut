import base64
import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from hashlib import md5
from time import time

import redis
import rq
from flask import current_app, url_for
from flask_login import UserMixin, current_user
from guess_language import guess_language
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import db, login

# pretty much didn't change except for references to current_app
from app.search import query_index, add_to_index, remove_from_index


logging.basicConfig(filename='rq.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class SearchableMixin(object):
    # the "glue" that links ES and SQLAlchemy databases

    # wraps the query_index function from app/search.py
    @classmethod
    def search(cls, expression, page, per_page):
        # all indexes will be named in line with the respective sql-alchemy table
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    # triggered each time before a commit is pushed
    @classmethod
    def before_commit(cls, session):
        # saving the changes coz they won't be available after the session has been committed
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    # triggered each time after a commit is pushed
    @classmethod
    def after_commit(cls, session):
        # we go through all the _changes and update the ES database
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        # then we leave _changes clean for next commit
        session._changes = None

    # simple helper method to refresh the indexes - the same as throwing the entire database into ES
    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class PaginatedAPIMixin(object):
    # implementing this as a mixin to preserve generality so that we can apply it to other models afterwards
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        # the first 3 arguments are a flask sql alchemy query
        # returns a pagination object with items for a given page
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            # we're using "endpoint" because we wanted to keep the function generic
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page, **kwargs),
                'next': url_for(endpoint, page=page+1, per_page=per_page, **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page-1, per_page=per_page, **kwargs) if resources.has_prev else None
            }
        }
        return data


class User(PaginatedAPIMixin, SearchableMixin, UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    fav_animal = db.Column(db.String(140))
    fav_animal2 = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    # authentication for the api
    # adding the token attribute. Because we'll have to search the db by it, making it unique and indexed
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    #---------------------------------------------------------------------------
    # message stuff

    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)

    # counts number of new messages
    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    #---------------------------------------------------------------------------
    # notifications

    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def add_notification(self, name, data):
        # if a notification with a similar name already exists - we delete it first
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    # ---------------------------------------------------------------------------

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    __searchable__ = ['username', 'email']

    # --------------------------------------------------------------------------
    # redis stuff
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    # helper functions to access the queue
    def launch_task(self, name, description, *args, **kwargs):
        # the "name" argument is the function name, as defined in app/tasks.py
        # the args/kwargs are positional arguments needed for the "name" function to actually run
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, *args, **kwargs)
        # this is where we're writing to the database
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task) #note how we're adding the task, but not issuing the commit. This is because it's better to use higher level functions that group together actions of many lower level child functions like this one, when writing to the db.
        return rq_job

    # returns all outstanding tasks
    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    # returns a specific outstanding task
    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False).first()

    # --------------------------------------------------------------------------
    # api stuff
    def to_dict(self, include_email=False):
        # define the representation structure we're going to be using in the api
        # then pull the required fields from the db
        # email is optional because we will only be showing it when request comes from account owner, otherwise we don't want to reveal it
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + 'Z',
            'about_me': self.about_me,
            'post_count': self.posts.count(), #example of where representation in api doesn't match that in db
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
                'avatar': self.avatar(128)
            }
        }
        if include_email:
            data['email'] = self.email
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    # authentication stuff
    def get_token(self, expires_in=3600):
        now = datetime.utcnow()

        # if token has at lease 1 min before expiration, return it
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token

        # else let's create a new one
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        # set expiration to be 1 second before right now, so it won't pass the below test
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(PaginatedAPIMixin, SearchableMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    # we're saying that this model (Post) needs to have its body indexed for searching
    __searchable__ = ['body']

    # --------------------------------------------------------------------------
    # api stuff
    def to_dict(self):
        data = {
            'id': self.id,
            'body': self.body,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'language': self.language,
            '_links': {
                'self': url_for('api.get_post', id=self.id)
            }
        }
        if self.id-1 > 0:
            data['_links']['previous'] = url_for('api.get_post', id=self.id-1)
        if self.id+1 in [p.id for p in Post.query.all()]:
            data['_links']['next'] = url_for('api.get_post', id=self.id+1)
        return data

    def from_dict(self, data, current_user):
        # the code below works equally well for new posts and for old posts
        # the difference happens at a higher level function, where for new posts we call db.session/.add(), but for existing we only commit
        setattr(self, 'body', data['body'])
        setattr(self, 'author', current_user)
        language = guess_language(data['body'])
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        setattr(self, 'language', language)
        print('complete ok')
        # not returning anything, instead add and commit will happen in parent function


class Task(db.Model):
    # redis queue itself is not a storage / history system. we need to separately store stuff in the database if we want to know how jobs went
    id = db.Column(db.String(36), primary_key=True) #note now a string, because using job identifiers generated by RQ
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection = current_app.redis)
            logging.debug(f'get_rq_job succeeded fetching the job {self.id}')
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            logging.debug(f'get_rq_job failed with exception {traceback.format_exc()}')
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        # assumption 1 - if job id not in the queue this means the job already finished and more than 500s passed and so we're returning 100
        # assumption 2 - if job exists but there is no meta info, this means it's still scheduled to run
        return job.meta.get('progress', 0) if job is not None else 100


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))