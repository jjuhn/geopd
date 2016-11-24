from flask import abort
from flask import flash
from flask import make_response
from flask import redirect
from flask import render_template
from flask import url_for
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from . import app
from . import send_email
from .form import ChangeAddressForm
from .form import ContactForm
from .form import FeedbackForm
from .orm.model import *


@app.route('/users/status', methods=['POST'])
@login_required
def update_users_status():
    if Permission.MANAGE_USER_ACCOUNT not in current_user.permissions:
        abort(403)

    status_id = int(request.form.get('status'))
    if status_id not in (User.STATUS.ACTIVE, User.STATUS.DISABLED):
        abort(400)

    user_id_list = [int(user_id) for user_id in request.form.getlist('users[]')]
    if current_user.id in user_id_list:
        abort(400)

    for user in User.query.filter(User.id.in_(user_id_list)):
        user.status_id = status_id

    db.session.commit()

    return '', 204


@app.route('/users/<int:user_id>/address', methods=['POST'])
@login_required
def update_user_address(user_id):
    if user_id != current_user.id:
        abort(403)

    address_form = ChangeAddressForm()
    if address_form.validate_on_submit():
        address = UserAddress.query.get(current_user.id)
        address.load(request.form)
        try:
            db.session.commit()
        except SQLAlchemyError:
            flash('Failed to save new address. Try again later', category='danger')
        else:
            flash('New address saved.', category='success')

        return redirect(url_for('show_user', user_id=current_user.id))


@app.route('/users/<int:user_id>/avatar')
@login_required
def get_user_avatar(user_id):
    avatar = UserAvatar.query.get(user_id)
    if not avatar.data:
        return app.send_static_file('core/images/avatar.png')

    response = make_response(avatar.data)
    response.headers['Content-Type'] = avatar.mimetype
    return response


@app.route('/users/<int:user_id>/avatar', methods=['POST'])
@login_required
def update_user_avatar(user_id):
    if user_id != current_user.id:
        abort(403)

    current_user.avatar.data = request.files['avatar'].stream.read()
    current_user.avatar.mimetype = request.files['avatar'].mimetype
    db.session.commit()

    return '', 204


@app.route('/contact/', methods=['GET', 'POST'])
def contact():
    form = FeedbackForm() if current_user.is_authenticated else ContactForm()

    if form.validate_on_submit():
        send_email(app.config['APP_CONTACT'], 'Contact Form', 'core/auth/email/contact', form=form.data)
        flash('Your message has been submitted. Someone will contact you by email soon.', 'success')
        return redirect(url_for('index'))

    if form.errors:
        flash('Failed to submit form. Please try again later.', 'danger')

    return render_template('core/contact.html', form=form)
