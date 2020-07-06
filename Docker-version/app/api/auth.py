from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth

from app.api.errors import error_response
from app.models import User

# we're going to use another flask extention to authenticate users through api
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

# ------------------------------------------------------------------------------
# first we need to verify password to issues the token = authentication
# once implemented, the request will looks like this:
# http --auth <username>:<password> POST http://localhost:5000/api/token


@basic_auth.error_handler
def basic_auth_error(status):
    # returns standard error response that we wrote in errors.py
    return error_response(status)

@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
        # the authenticated user will be available through basic_auth.current_user

# ------------------------------------------------------------------------------
# next we need to verify the token that the user has, before giving them access to some route = authorization
# to login we have to pass token as bearer for HTTP flask to work. HTTPie doesn't offer a simplified entry so we just do:
# instead we can login using
# http GET http://localhost:5000/api/users "Authorization:Bearer AFJonzJI/pZEIAsrAcJvIXWvIPGZJ5nF

@token_auth.verify_token
def verify_token(token):
    # check_token is our function, other is standard plumbing around it
    return User.check_token(token) if token else None

@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)