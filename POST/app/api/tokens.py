from flask import jsonify

from app import db
from app.api import bp
from app.api.auth import basic_auth, token_auth


@bp.route('/tokens', methods=['POST'])
@basic_auth.login_required #ensures function only get run when credentials are valid
def get_token():
    # this is the get_token function we implemented in User model
    token = basic_auth.current_user().get_token()
    db.session.commit() # we add the token in that function and only commit it here
    return jsonify({'token': token})

@bp.route('/tokens', methods=['DELETE'])
@token_auth.login_required
def revoke_token():
    # token sent in the authentication header is the one actually being revoked
    # thus the revocation logic was written by us in the User class, but the logic to identify the token comes from the library itself
    token_auth.current_user().revoke_token()
    db.session.commit()
    return '', 204