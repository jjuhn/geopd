from functools import wraps

from flask import flash
from flask import redirect
from flask import render_template
from flask import url_for
from flask_login import LoginManager
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user
from flask_wtf import FlaskForm
from sqlalchemy.exc import SQLAlchemyError
from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import ValidationError

from . import app
from . import send_email
from .form import AddressMixin
from .orm.model import *
from geopd.orm.model import Permission

########################################################################################################################
# login manager
########################################################################################################################

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@login_manager.unauthorized_handler
def unauthorized():
    if request.endpoint == 'confirm':
        flash('Please login to confirm your email address.', 'info')
        return render_template('welcome.html')
    return render_template('core/error.html', error='401 Unauthorized',
                           message='User not authenticated. Please log in.'), 401


def active_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif not current_user.is_authenticated or not current_user.is_active():
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)

    return decorated_view


@app.before_request
def before_request():
    if current_user.is_authenticated:

        current_user.ping()

        if not current_user.is_active() and request.endpoint != 'confirm':
            flash('This account is still pending approval. Please try again later.', 'warning')
            logout_user()

        elif current_user.force_password_reset \
                and request.endpoint not in ('static', 'change_password', 'logout'):

            form = ChangePasswordForm()
            return render_template('core/auth/change_password.html', form=form)


########################################################################################################################
# forms
########################################################################################################################


class LoginForm(FlaskForm):
    email = StringField('Email address', id='login-email')
    password = PasswordField('Password', id='login-password')
    remember_me = BooleanField('Remember me')
    login = SubmitField('Login')


class RegistrationForm(FlaskForm, AddressMixin):
    email = StringField('Email Address')
    name = StringField('Name')
    password = PasswordField('Password')
    confirm = PasswordField('Confirm Password')

    accept = BooleanField('Accept Terms')

    register = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter(User.email == field.data).first():
            raise ValidationError("The email address: '{0}' is already registered.".format(field.data))
    def validate_lat(self, field):
        if field.data == '':
            raise ValidationError("Please choose location from the list.")

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password')
    password = PasswordField('New password')
    confirm = PasswordField('Confirm new password')
    change = SubmitField('Change My Password')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email')
    reset = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
    email = StringField('Email')
    password = PasswordField('New password')
    confirm = PasswordField('Confirm password')
    reset = SubmitField('Reset Password')


########################################################################################################################
# routes
########################################################################################################################


@app.context_processor
def inject_login_form():
    return dict(login_form=LoginForm())


@app.route('/login/', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if user.status_id == User.STATUS.DISABLED:
                flash('This account is has been disabled.', 'warning')
            elif user.check_password(form.password.data):
                login_user(user, form.remember_me.data)
                return redirect(request.args.get('next') or request.referrer or url_for('index'))
            else:
                flash('Invalid username or password provided.', 'warning')
        else:
            flash('Invalid username or password provided.', 'warning')

    for field_name, errors in form.errors.items():
        for error in errors:
            flash("{field}: {message}".format(field=field_name, message=error), 'warning')
            return redirect(request.args.get('next') or url_for('index'))

    return redirect(request.args.get('next') or request.referrer or url_for('index'))


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():

        selected_committee = request.form.get("referrer")
        user = User(email=form.email.data, password=form.password.data, name=form.name.data)

        user.address.load(request.form)
        db.session.add(user)

        try:
            db.session.flush()
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('Error while processing request. Please try again later', 'warning')
        else:
            token = user.generate_confirmation_token()

            cc = []
            for c_user in Permission.query.get(Permission.STEERING_COMMITTEE).users:
                cc.append(c_user.email)

            send_email(cc[0], "Requesting activation of new user.",
                       "email/new_member_request", cc=cc, user=user, committee=User.query.get(selected_committee) )

            send_email(user.email, 'Confirm Your Account', 'core/auth/email/confirm', user=user, token=token)
            flash('A confirmation email has been sent to your email address', 'success')
            db.session.commit()
            return redirect(url_for('index'))

    # flash form errors if necessary
    for error in form.errors.values():
        flash(error[0], 'danger')

    users = User.query.all()
    committee = []
    for u in users:
        if u.permissions.get(2):
            committee.append(u)


    return render_template('core/auth/register.html', form=form, users=committee)


@app.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        flash('Your email address has been confirmed. Thanks!', 'success')

    else:
        if current_user.confirm(token):
            db.session.commit()
            flash('You have confirmed your account. Thanks!', 'success')
        else:
            flash('The confirmation link is invalid or has expired.', 'warning')

        if not current_user.is_active():
            logout_user()

    return redirect(url_for('index'))


@app.route('/confirm/')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account', 'core/auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('index'))


@app.route('/password/', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.old_password.data):
            current_user.password = form.password.data
            current_user.force_password_reset = False
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('index'))
        else:
            flash('The old password you provided is invalid. Please try again.', 'warning')
    return render_template("core/auth/change_password.html", form=form)


@app.route('/reset/', methods=['GET', 'POST'])
def reset_password_request():
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        # In the case that no account exists for the provided email address, pretend an email was sent.
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password', 'core/auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been sent to you.', 'success')
        return redirect(url_for('index'))
    return render_template('core/auth/reset_password_request.html', form=form)


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.reset_password(token, form.password.data):
            db.session.commit()
            flash('Your password has been updated.', 'success')

        return redirect(url_for('index'))

    return render_template('core/auth/reset_password.html', form=form)
