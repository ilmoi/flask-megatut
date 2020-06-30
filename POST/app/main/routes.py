from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app, send_file, render_template_string
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from guess_language import guess_language
from rq.job import Job, cancel_job

from app import db
from app.models import User, Post
from app.translate import translate

from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
    UserSearchForm


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        # we instantiate the form and associate it with the g container provided by flask, so that the form persists on the page
        # This g variable provided by Flask is a place where the application can store data that needs to persist through the life of a request.
        # it's important to note that g variable is specific to each request and each client - so even if the server is handling many requests for many clients, the info is containerised privately
        # templates also all automatically see this g variable, so there is no need to pass it to each render_template() function
        g.search_form = SearchForm()
        g.user_search_form = UserSearchForm()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/user_search')
@login_required
def user_search():
    User.reindex() #funny but without this it wouldn't know about existence of other users!
    if not g.user_search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    users, total = User.search(g.user_search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])
    print(users)
    next_url = url_for('main.user_search', q=g.user_search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.user_search', q=g.user_search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('user_search.html', title=_('User Search'), users=users,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/export_posts')
@login_required
def export_posts():
    # if current_user.get_task_in_progress('export_posts'):
    #     flash('an export in progress')
    # else:
    # for i in range(50):
    current_user.launch_task('export_posts', 'exporting posts...')
    db.session.commit()
    return redirect(url_for('main.index'))
    # return redirect(url_for('main.display_posts', id=job.id))


# this displays the results back to the user!
@bp.route('/display_posts/<id>')
def display_posts(id):
    job = Job.fetch(id, connection=current_app.redis)
    status = job.get_status()
    if status in ['queued', 'started', 'deferred', 'failed']:
        # need refresh to be true, since we're refreshing the page until ready
        return get_template(status, refresh=True)
    elif status == 'finished':
        # result in template either takes on "status" or takes on return value from job
        return get_template(job.result)


# helper function
def get_template(data, refresh=False):
    return render_template('display_job.html', result=data, refresh=refresh)


# cancelling jobs - need to go url manually
# NOTE if you only have 1 job running, then that job will still finisha nd you won't notice the effect of cancel, so instead make sure you have multiple jobs
@bp.route('/cancel_export')
def cancel_export():
    if current_user.get_task_in_progress('export_posts'):
        for task in current_user.get_tasks_in_progress():
            if not task.complete:
                job = Job.fetch(task.id, connection=current_app.redis)
                job.cancel()
    print('all jobs cancelled')
    return redirect(url_for('main.index'))