from flask import jsonify, request
from werkzeug.http import HTTP_STATUS_CODES



def bad_request(message):
    # to make it even easier to generate 400 errors, this is a helper func
    return error_response(400, message)

def error_response(status_code, message=None):
    # werkzeug provides a short description for each http code -
    # in this way we only need to worry about the numeric status of the error code and not the full desc
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload) #convert into a nice json object
    response.status_code = status_code
    return response
