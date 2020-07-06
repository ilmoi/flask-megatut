from flask import jsonify, request, url_for

from app import db
from app.api import bp
from app.api.auth import token_auth
from app.models import Post, User


@bp.route('/posts/<int:id>', methods=['GET'])
def get_post(id):
    return jsonify(Post.query.get_or_404(id).to_dict())


@bp.route('/posts', methods=['GET'])
@token_auth.login_required
def get_posts():
    # going to fetch all posts for a given user
    # I first wanted to get the token and then use it in .filter_by() to find the right user - but then I realized there's an easier way
    user = token_auth.current_user()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100) #not more than 100
    # the next tricky bit was figuring out posts below
    posts = Post.query.filter_by(user_id=user.id)
    data = Post.to_collection_dict(posts, page, per_page, 'api.get_posts')
    return jsonify(data)


@bp.route('/posts', methods=['POST'])
@token_auth.login_required
def create_post():
    # we need the user here coz we need to know who to assign as author of the post
    # so we once again fetch them from the token
    user = token_auth.current_user()
    data = request.get_json() or {}

    post = Post()
    post.from_dict(data, user)
    db.session.add(post)
    db.session.commit()

    response = jsonify(post.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_post', id=post.id)
    return response


@bp.route('/posts/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_post(id):
    user = token_auth.current_user()
    data = request.get_json() or {}

    post = Post.query.filter_by(id=id).first()
    post.from_dict(data, user)
    db.session.commit()

    return jsonify(post.to_dict())