from flask import render_template, request
from app import db
from app.errors import bp
from app.api.errors import error_response as api_error_response

# checks what type of response the client prefers
def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
           request.accept_mimetypes['text/html']


@bp.app_errorhandler(404)
def not_found_error(error):
    # added functionality in case call comes from api with Accept header for json
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    # added functionality in case call comes from api with Accept header for json
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/500.html'), 500
