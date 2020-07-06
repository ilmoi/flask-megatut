# here we create teh blueprint for auth
from flask import Blueprint

bp = Blueprint('auth', __name__)

from app.auth import routes
