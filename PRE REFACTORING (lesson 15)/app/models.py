from datetime import datetime
from hashlib import md5
from time import time

import jwt
from flask_login import UserMixin

from app import db, login, app
from werkzeug.security import generate_password_hash, check_password_hash


# not declaring this table as a model since it has no actual data other than foreign keys
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, db.Model):
    # UserMixin is used to add the 4 methods expected by flask-login:
    # is_authenticated, is_active, is_anonymous, get_id

    # define the table columns with optional params, like whether they are indexed
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    fav_animal = db.Column(db.String(128)) #added later during migration
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # db.relationship is a special call used to rep ONE TO MANY relship
    # ONE = table it's created in
    # MANY = first arg
    # if I have a user stores as "u", u.posts will run a query to return all posts by that user
    # backref = the field that is added in table on the MANY side (ie we can now call post.author on posts)
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    # --------------------------------------------------------------------------
    # followers

    # declaring the many to many relship
    followed = db.relationship(
        'User', secondary=followers, #User is the right side entity in the relation, left side = parent class (obv self referential)
        # secondary configures the association table used for the relationship that is defined above
        primaryjoin=(followers.c.follower_id == id), #how we link LHS of followers table with Users
        secondaryjoin=(followers.c.followed_id == id), #how we link RHS of followers table with Users
        backref=db.backref('followers', lazy='dynamic'), #indicates how the rel-ship is accessed from RHS
        lazy='dynamic' #lazy population both from LHS (this line) and RHS (prev line)
    )

    # it's always better to move code away from view functions and into models / other modules - better for unit testing
    # below methods allow us to add/remove relationships
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        # filter_by can only check for equality, filter can check for any arbitrary condition
        # count() is a "query terminator" together with all() and first()
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query\
            .join(followers, (followers.c.followed_id == Post.user_id) #join Posts and followers where posts are made by followed people
            ).filter(followers.c.follower_id == self.id #filter the resulting table s.t. the follower is the current user
            )
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    # --------------------------------------------------------------------------
    # login functionality
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # flask-login keeps users logged in by storing their id in flask's user session
    # each time the user accesses a page, flask retrieves that id from the session and logs the user in
    # so we need a function to retrieve the user's id
    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # --------------------------------------------------------------------------
    # avatars
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    # --------------------------------------------------------------------------
    # password reset
    # the below functionality is needed for us to generate/validate a security token to be included in the email
    # what we do is we store the user information inside a json object and we encode it using HS256 algorithm and a secret key
    # next we send it to the user in an email
    # if they are the real user with access to their email, they will be able to retrieve it and pass it as an argument into the url
    # we can then check if the token is indeed valid (function below) and thus authorize the user to see the page
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256'
        ).decode('utf-8') #the decoding part is necessary because the token is returned as a bytes sequence, but it's more convenient to work with a string

    # we decode the token using the same algo and secret key to get the user's information and make sure the signature is the same (ie token has not been tampered with)
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Post(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # user_id = foreign key, whereas id column in users table = primary key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    # --------------------------------------------------------------------------
    # post translation

    language = db.Column(db.String(5))