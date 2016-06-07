from functools import wraps
from random import randint

from flask import Markup
from flask import flash
from flask import redirect
from flask import render_template
from flask_login import LoginManager
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user
from flask_wtf import Form
from sqlalchemy.exc import SQLAlchemyError
from wtforms import StringField
from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import SubmitField
from wtforms import ValidationError

from geopd import app
from geopd.form import AddressMixin
from geopd.email import send_email
from geopd.orm.model import *

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
    # if request.blueprint == 'api':
    #     return make_error_response(401, 'user not authenticated')
    return render_template('error.html', error='401 Unauthorized',
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
            return render_template('auth/change_password.html', form=form)

        elif request.blueprint == 'web' and not current_user.survey.completed_on:
            if request.endpoint != 'web.show_user' or request.view_args['id'] != current_user.id:
                if 1 == randint(1, 5):
                    if not current_user.bio.research_interests or not current_user.bio.research_experience:
                        flash(Markup(
                            'Your biography is not up to date. '
                            '<a href="{0}" class="alert-link">Update my biography</a>.'.format(
                                url_for('web.show_user', id=current_user.id))), category='warning')
                    elif not current_user.survey.clinical or not current_user.survey.epidemiologic \
                            or not current_user.survey.biospecimen or current_user.survey.ethical == None \
                            or current_user.survey.consent == None:
                        flash(Markup(
                            'You have not completed the survey. Please complete the survey '
                            '<a href="{0}#survey" class="alert-link">here</a>.'.format(
                                url_for('web.show_user', id=current_user.id))), category='warning')


########################################################################################################################
# forms
########################################################################################################################


class LoginForm(Form):
    email = StringField('Email address', id='login-email')
    password = PasswordField('Password', id='login-password')
    remember_me = BooleanField('Remember me')
    login = SubmitField('Login')


class RegistrationForm(Form, AddressMixin):
    email = StringField('Email Address')
    last_name = StringField('Last Name')
    given_names = StringField('Given Name(s)')
    password = PasswordField('Password')
    confirm = PasswordField('Confirm Password')

    accept = BooleanField('Accept Terms')

    register = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("The email address: '{0}' is already registered.".format(field.data))


class ChangePasswordForm(Form):
    old_password = PasswordField('Old password')
    password = PasswordField('New password')
    confirm = PasswordField('Confirm new password')
    change = SubmitField('Change My Password')


class PasswordResetRequestForm(Form):
    email = StringField('Email')
    reset = SubmitField('Reset Password')


class PasswordResetForm(Form):
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
            if user.status_id == USER_STATUS_DISABLED:
                flash('This account is has been disabled.', 'warning')
            elif user.check_password(form.password.data):
                login_user(user, form.remember_me.data)
                return redirect(request.args.get('next') or request.referrer or url_for('web.index'))
            else:
                flash('Invalid username or password provided.', 'warning')
        else:
            flash('Invalid username or password provided.', 'warning')

    for field_name, errors in form.errors.items():
        for error in errors:
            flash("{field}: {message}".format(field=field_name, message=error), 'warning')
            return redirect(request.args.get('next') or url_for('web.index'))

    return redirect(request.args.get('next') or request.referrer or url_for('web.index'))


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('web.index'))


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('web.index'))

    form = RegistrationForm()

    if form.validate_on_submit():

        user = User(email=form.email.data, password=form.password.data,
                    last_name=form.last_name.data,
                    given_names=form.given_names.data)
        user.address.load(request.form)
        db.add(user)

        try:
            db.flush()

        except SQLAlchemyError:
            db.rollback()
            flash('Error while processing request. Please try again later', 'warning')

        else:
            token = user.generate_confirmation_token()
            send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
            flash('A confirmation email has been sent to your email address', 'success')
            db.commit()
            return redirect(url_for('web.index'))

    # flash form errors if necessary
    if form.errors and 'email' in form.errors:
        flash(form.errors['email'][0], 'warning')

    return render_template('auth/register.html', form=form)


@app.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        flash('Your email address has been confirmed. Thanks!', 'success')

    else:
        if current_user.confirm(token):
            db.commit()
            flash('You have confirmed your account. Thanks!', 'success')
        else:
            flash('The confirmation link is invalid or has expired.', 'warning')

        if not current_user.is_active():
            logout_user()

    return redirect(url_for('web.index'))


@app.route('/confirm/')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('web.index'))


@app.route('/password/', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.old_password.data):
            current_user.password = form.password.data
            current_user.force_password_reset = False
            db.add(current_user)
            db.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('web.index'))
        else:
            flash('The old password you provided is invalid. Please try again.', 'warning')
    return render_template("auth/change_password.html", form=form)


@app.route('/reset/', methods=['GET', 'POST'])
def reset_password_request():
    if not current_user.is_anonymous:
        return redirect(url_for('web.index'))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        # In the case that no account exists for the provided email address, pretend an email was sent.
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password', 'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been sent to you.', 'success')
        return redirect(url_for('web.index'))
    return render_template('auth/reset_password_request.html', form=form)


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not current_user.is_anonymous:
        return redirect(url_for('web.index'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.', 'success')
        return redirect(url_for('web.index'))

    return render_template('auth/reset_password.html', form=form)
