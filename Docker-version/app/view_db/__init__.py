from flask import Blueprint

bp = Blueprint('view_db', __name__)

from app.view_db import forms, routes