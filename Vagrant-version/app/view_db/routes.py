from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required

from app import db
from app.models import User
from app.view_db import bp
from app.view_db.forms import ChangeAttrForm


@bp.route('/view_db')
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
    return render_template('view_db/view_db.html', keyed_attrs=keyed_attrs)


# this allows the user to edit any one of the attributes (columns) stored for them in the database
@bp.route('/edit/<attr_key>', methods=['GET', 'POST'])
def edit(attr_key):
    attr_keys = [c.key for c in User.__table__.c]

    if attr_key not in attr_keys:
        redirect(url_for('main.index'))

    user = User.query.filter_by(username=current_user.username).first()
    form = ChangeAttrForm()

    if form.validate_on_submit():
        user.__setattr__(attr_key, form.attr.data)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('view_db.view_db'))

    # this fills out the form with existing values
    elif request.method == 'GET':
        form.attr.data = user.__getattribute__(attr_key)

    return render_template('view_db/edit.html', form=form, ak=attr_key)

