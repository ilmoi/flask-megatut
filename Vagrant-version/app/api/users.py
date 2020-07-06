from flask import jsonify, request, url_for

from app import db
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request
from app.models import User


@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    # get_or_404 very useful method that returns either the id or 404 (instead of none) if it does not
    # if it does find it, it returns a User object, which we then use self.to_dict() on to convert to appropriate format
    # jsonify is a MUST for the view function to work correctly (in browser or in terminal)
    return jsonify(User.query.get_or_404(id).to_dict())


@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100) #not more than 100
    data = User.to_collection_dict(User.query, page, per_page, 'api.get_users')
    return jsonify(data)


@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100) #not more than 100
    data = User.to_collection_dict(user.followers, page, per_page, 'api.get_followers', id=id)
    return jsonify(data)


@bp.route('/users/<int:id>/followed', methods=['GET'])
@token_auth.login_required
def get_followed(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100) #not more than 100
    data = User.to_collection_dict(user.followed, page, per_page, 'api.get_followed', id=id)
    return jsonify(data)


@bp.route('/users', methods=['POST'])
@token_auth.login_required
def create_user():
    # we're going to want to create a user
    # they send in 1)data, 2)new_user=True
    # data contains 1)username, 2)email, 3)about_me, 4)password

    # need to retrieve data from Post request
    data = request.get_json() or {}

    # do the checks
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request('must incl name email pw')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('username already exists')
    if User.query.filter_by(email=data['email']).first():
        return bad_request('email already exists')

    # create and commit the user to db
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()

    # prepare the response with user's details and status 201
    response = jsonify(user.to_dict())
    response.status_code = 201
    # status code 201 requires us to return the Location header that is set to the URL of the new resource
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):
    user = User.query.get_or_404(id)
    if user == "404":
        return bad_request('no such user found')

    data = request.get_json() or {}
    if not data:
        return bad_request('no changes requested')
    if 'username' in data and data['username'] != user.username and \
            User.query.filter_by(username=data['username']).first():
        return bad_request('please use a different username')
    if 'email' in data and data['email'] != user.email and \
            User.query.filter_by(email=data['email']).first():
        return bad_request('please use a different email address')

    # amend & update the db
    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())


