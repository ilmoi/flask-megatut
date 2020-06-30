import os
from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from guess_language import guess_language
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

from app import app, db
from app.email import send_password_reset_email
from app.forms import LoginForm, RegistrationForm, EditProfileForm, EmptyForm, \
    PostForm, ResetPasswordRequestForm, ResetPasswordForm, ChangeAttrForm

# the decorators create associations between the route and the func
from app.models import User, Post
from app.translate import translate


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required #forces the user to login before seeing the app
def index():

    form = PostForm()

    if form.validate_on_submit():
        # ----------------------------------------------------------------------
        # ajax-based translation tool
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''  # any lang with empty string = assumed to have unknown language

        # ----------------------------------------------------------------------
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash('your post has been saved')

        # note we're aleready on index page and we don't in theory ahve to redirect back to index page
        # that said it is considered standard practice after POST to do so
        # this helps mitigate the annoyance with how the refresh command works in browsers
        # when you hit refresh in a browser it re-issues the lat command
        # if that command was POST it will try to re-submit form and ask the user to confirm that (confusion)
        # while if the last command was to go to index page, the browser will re-do that and that's fine
        # This simple trick is called the Post/Redirect/Get pattern. It avoids inserting duplicate posts when a user inadvertently refreshes the page after submitting a web form.
        return redirect(url_for('index'))

    # --------------------------------------------------------------------------
    # pagination
    page = request.args.get('page', 1, type=int)
    # we pass 3 arguments to paginate: page number, number of posts per page, and whether to throw a 404 if run out of posts
    posts = current_user.followed_posts().paginate(page, app.config['POSTS_PER_PAGE'], False)
    # the pagination object return above has a bunch of interesting methods for us, like .next_num and .has_next. we'll use those below to implement page links
    # anything passed to url_for that is not in the main url will be appended as query arguments ?like_this=arg
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    # rendering is what we do when we want to display a template
    # rendering invokes the Jinja2 template engine that comes bundled with flask
    return render_template('index.html', title='Bonanzaz', form=form, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)



# breaking: interesting, app.route has to be named THE SAME as the function below, or it breaks
@app.route('/log1n', methods=['GET', 'POST'])
def log1n():
    # The current_user variable comes from Flask-Login and can be used at any time during the handling to obtain the user object that represents the client of the request. The value of this variable can be a user object from the database (which Flask-Login reads through the user loader callback I provided above), or a special anonymous user object if the user did not log in yet.
    # we will be using current_user a lot since I can't think of any other way to identify the user who's requesting the action (client)
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    # during a GET request this evals to False, during POST to True
    # in other words when user clicks "submit" this branch is triggered
    if form.validate_on_submit():

        # flash is a quick and dirty way to test functionality, that it displays correctly to the screen
        # flash('login requested for user {}, remember_me={}'.format(
        #     form.username.data, form.remember_me.data))
        # return redirect(url_for('index'))

        user = User.query.filter_by(username=form.username.data).first() # first() returns user object if it exists, else None
        if user is None or not user.check_password(form.password.data):
            flash ('Invalid username or password')
            return redirect(url_for('log1n'))

        login_user(user, remember=form.remember_me.data)

        # if the user was forced to the login page we want to collect where they come from and send them there back after login
        next_page = request.args.get('next')
        # before sending them to next_page though we check if the address is relative (ie based on our domain). Otherwise there's a security hole - an attacker could insert their own domain there and have the server redirect there
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    # during a GET request above is skipped and browser renders the page
    return render_template('login.html', title='Sign Inz', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, fav_animal=form.fav_animal.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Congratulations you are now registered with name {form.username.data}.')
        return redirect(url_for('log1n'))

    return render_template('register.html', title='Registerz', form=form)


@app.route('/user/<username>') #<username> is a dynamic component - browser will accept any string and then set username=to_that_string
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404() #we're passing downt he username from the url
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    # here we need to include the extra username argument
    next_url = url_for('user', username=user.username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


# whenever you have some logic you want executed before every view function, you can use flask's built-in "before request" functionality
@app.before_request
def before_request():
    if current_user.is_authenticated:
        # because we're referencing current_user imported from flask_login, the flask-login extention is smart enough to update the database for us with db.add(). so we only have to commit after
        current_user.last_seen = datetime.utcnow() #always use UTC, otherwise the times will display differently depending on your location
        db.session.commit()


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')

        # saving down a file
        f = form.random_file.data
        if f: #if file left empty we don't want to try and save the directory into itself
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.instance_path, 'photos', filename))

        return redirect(url_for('edit_profile'))

    # only if request method is GET (we're loading the page) - update the fields. Otherwise, if the request method is POST but the above didn't trigger, means the user tried submitting but there was an error
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
def follow(username):

    form = EmptyForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('user doesnt exist')
            return redirect(url_for('index'))
        elif user == current_user:
            flash('you cant follow yourself')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'nice, now youre following {user}')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    form = EmptyForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first() #get the username from url, then fetch user from db using that username
        if not user:
            flash('user doesnt exist')
            return redirect(url_for('index'))
        elif user == current_user:
            flash('you cant unfollow yourself')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'nice, now youre unfollowing {user}')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    return render_template("index.html", title='Explore', posts=posts.items,
                          next_url=next_url, prev_url=prev_url)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('check your email')
        return redirect(url_for('log1n'))
    return render_template('reset_password_request.html', title='pw reset', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # I'm noticing a pattern for these things - we typically build and link 3 things: the view function (this one), the form and the html page
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # if validation below passes successfully we'll get back a user object fetched by id in User, models
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('your pw has been reset')
        return redirect(url_for('log1n'))
    return render_template('reset_password.html', form=form)


@app.route('/view_db')
@login_required
def view_db():
    # get user
    user = User.query.filter_by(username=current_user.username).first() #UNSECURE
    # get all columns from db
    attr_keys = [c.key for c in User.__table__.c]
    # get all values for the user
    attrs = [user.__getattribute__(c.key) for c in User.__table__.c]
    # tuple the two up, before they're displayed in html
    keyed_attrs = zip(attr_keys, attrs)
    return render_template('view_db.html', keyed_attrs=keyed_attrs)


# this allows the user to edit any one of the attributes (columns) stored for them in the database
@app.route('/edit/<attr_key>', methods=['GET', 'POST'])
def edit(attr_key):
    attr_keys = [c.key for c in User.__table__.c]

    if attr_key not in attr_keys:
        redirect(url_for('index'))

    user = User.query.filter_by(username=current_user.username).first()
    form = ChangeAttrForm()

    if form.validate_on_submit():
        user.__setattr__(attr_key, form.attr.data)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('view_db'))

    # this fills out the form with existing values
    elif request.method == 'GET':
        form.attr.data = user.__getattribute__(attr_key)

    return render_template('edit.html', form=form, ak=attr_key)


# an ajax request is similar to other routes/view functions, except that instead of returning a redirect or rendering a page it returns XML/JSON
# this is the serverside implementation
@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    # request.form is all the data that flask includes with the submission
    # when working with WTF forms we didn't have to manually access it, but now we do
    # jsonify converts dictionary into a json
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})