from random import randint

from flask import Markup
from flask import abort
from flask import flash
from flask import make_response
from flask import redirect
from flask import render_template
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import noload
from inflection import singularize

from can.web import app
from can.web import web_blueprint as web
from can.web.email import send_email
from geopd.form import ChangeAddressForm
from geopd.form import ContactForm
from geopd.form import PostForm
from geopd.form import UpdateSurveyForm
from geopd.orm.model import *

SURVEY_PROFILE = 1
SURVEY_BIOLOGY = 2


########################################################################################################################
# main page
########################################################################################################################
@web.route('/')
def index():
    if not current_user.is_anonymous:
        return redirect(url_for('web.show_user', user_id=current_user.id))

    return render_template('welcome.html', cores=Core.query.all(),
                           meetings=Meeting.query.filter(Meeting.carousel).order_by(Meeting.year.desc()).all())


########################################################################################################################
# about us
########################################################################################################################
@web.route('/about/')
def show_about():
    return render_template('about.html')


########################################################################################################################
# annual meetings
########################################################################################################################
@web.route('/meetings/')
def show_meetings():
    meeting = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).first()
    return redirect(url_for('web.show_meeting', id=meeting.id))


@web.route('/meetings/<int:id>')
def show_meeting(id):
    meeting = Meeting.query.get(id)
    if not meeting.program:
        abort(404)
    meetings = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).all()
    return render_template('meetings/index.html', meeting=meeting, meetings=meetings)


########################################################################################################################
# projects
########################################################################################################################
@web.route('/projects/')
def show_projects():
    return render_template('projects.html', projects=Project.query.all())


########################################################################################################################
# publications
########################################################################################################################
@web.route('/publications/')
def show_publications():
    publications = Publication.query.order_by(Publication.published_on.desc()).all()
    return render_template('publications.html', publications=publications)


########################################################################################################################
# cores
########################################################################################################################
@web.route('/cores/')
def show_cores():
    return show_core(core_id=1)


@web.route('/cores/<int:core_id>')
def show_core(core_id):
    if current_user.is_authenticated:
        return render_template('cores/index.html',
                               form=PostForm(),
                               survey_form=UpdateSurveyForm(),
                               core=Core.query.get(core_id),
                               cores=Core.query.all())
    return render_template('cores/public/index.html',
                           core=Core.query.get(core_id),
                           cores=Core.query.all())


@login_required
@web.route('/cores/<int:core_id>/posts/', methods=['POST'])
def create_core_post(core_id):
    form = PostForm()
    if form.validate_on_submit():

        core = Core.query.options(noload('posts')).get(core_id)
        title, body = (request.form.get(key) for key in ('title', 'body'))

        if not title:
            flash('Please provide a post title', 'danger')
        elif not body:
            flash('Please provide post content', 'danger')
        else:
            core.posts.append(CorePost(title, body))
            try:
                db.commit()
            except SQLAlchemyError:
                flash('Error creating the post. Please try again later.', 'danger')

    return redirect(url_for('web.show_core', core_id=core_id))


@login_required
@web.route('/cores/<int:core_id>/posts/<int:post_id>')
def show_core_post(core_id, post_id):
    post = CorePost.query.get(post_id)
    if not post or post.core_id != core_id:
        abort(404)
    return render_template('/cores/post.html', post=post)


@login_required
@web.route('/cores/<int:core_id>/posts/<int:post_id>', methods=['POST'])
def update_core_post(core_id, post_id):
    post = CorePost.query.get(post_id)
    if not post or post.core_id != core_id:
        abort(404)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.commit()
    return '', 204


########################################################################################################################
# users
########################################################################################################################
@web.route('/users/')
def show_users():
    users = User.query.options(joinedload('address'))
    tpl = 'users/public.html' if current_user.is_anonymous else 'users/index.html'
    return render_template(tpl, users=users)


@web.route('/users/<int:user_id>')
@login_required
def show_user(user_id):
    survey = Survey.query.get(SURVEY_PROFILE)
    return render_template('users/profile/index.html',
                           user=User.query.options(joinedload('avatar'),
                                                   joinedload('bio'),
                                                   joinedload('address')).filter(User.id == user_id).one(),
                           address_form=ChangeAddressForm(),
                           survey_form=UpdateSurveyForm(),
                           survey=survey)


@web.route('/users/<int:user_id>/address', methods=['POST'])
@login_required
def update_user_address(user_id):
    if user_id != current_user.id:
        abort(403)

    address_form = ChangeAddressForm()
    if address_form.validate_on_submit():
        address = UserAddress.query.get(current_user.id)
        address.load(request.form)
        try:
            db.commit()
        except SQLAlchemyError:
            flash('Failed to save new address. Try again later', category='danger')
        else:
            flash('New address saved.', category='success')

        return redirect(url_for('web.show_user', user_id=current_user.id))


@web.route('/users/<int:user_id>/surveys/<int:survey_id>', methods=['POST'])
@login_required
def update_user_survey(user_id, survey_id):
    if user_id != current_user.id:
        abort(403)

    survey_form = UpdateSurveyForm()

    if survey_form.validate_on_submit():

        user_survey = current_user.surveys[survey_id]

        for name in user_survey.survey.questions.keys():

            question = user_survey.survey.questions[name]
            response = user_survey.responses[name] if name in user_survey.responses \
                else UserResponse(user_survey, question)
            db.add(response)

            if question.type_id in (QUESTION_TYPE_YESNO, QUESTION_TYPE_YESNO_EXPLAIN):
                if name in request.form.keys():
                    response.answer_yesno = request.form[name] == 'yes'
                    explain = request.form.get('{0}-explain'.format(name)) if not response.answer_yesno else None
                    user_survey.responses[name].answer_text = explain.strip() if explain else None

            elif question.type_id == QUESTION_TYPE_CHOICES:
                response.answer_choices = list()
                for choice_id in request.form.getlist(name):
                    response.answer_choices.append(SurveyQuestionChoice.query.get(choice_id))

        if 'complete' in request.form.keys():
            user_survey.completed_on = datetime.utcnow()
        elif 'update' in request.form.keys():
            user_survey.updated_on = datetime.utcnow()

        try:
            db.commit()
        except SQLAlchemyError:
            raise
        else:
            flash('Survey information updated.', category='success')

    return redirect(request.referrer or url_for('web.index'))


@web.route('/users/<int:user_id>/avatar')
@login_required
def get_user_avatar(user_id):
    avatar = UserAvatar.query.get(user_id)
    if not avatar.data:
        return app.send_static_file('images/avatar.png')

    response = make_response(avatar.data)
    response.headers['Content-Type'] = avatar.mimetype
    return response


@web.route('/users/<int:user_id>/avatar', methods=['POST'])
@login_required
def update_user_avatar(user_id):
    if user_id != current_user.id:
        abort(403)

    current_user.avatar.data = request.files['avatar'].stream.read()
    current_user.avatar.mimetype = request.files['avatar'].mimetype
    db.commit()

    return '', 204


@web.route('/users/<int:user_id>/biography', methods=['POST'])
@login_required
def update_user_biography(user_id):
    if user_id != current_user.id:
        abort(403)

    name = request.form.get('name')
    if name == 'interest':
        current_user.bio.research_interests = request.form['value'].strip()
    elif name == 'experience':
        current_user.bio.research_experience = request.form['value'].strip()

    db.commit()

    return '', 204


########################################################################################################################
# contact us
########################################################################################################################
@web.route('/contact/', methods=['GET', 'POST'])
def show_contact():
    if not current_user.is_anonymous:
        return redirect(url_for('web.index'))

    form = ContactForm()
    if form.validate_on_submit():
        send_email(app.config['APP_CONTACT'], 'Contact Form', 'auth/email/contact', form=form.data)
        flash('Your message has been submitted. Someone will contact you by email soon.', 'success')
        return redirect(url_for('web.index'))
    return render_template('contact.html', form=form)


@web.before_request
def before_request():
    if current_user.is_authenticated:
        if request.endpoint == 'web.show_core':
            if 1 == randint(1, 2):
                if not current_user.bio.research_interests or not current_user.bio.research_experience:
                    flash(Markup(
                        'Your biography is not up to date. '
                        '<a href="{0}" class="alert-link">Update my biography</a>.'.format(
                            url_for('web.show_user', user_id=current_user.id))), category='warning')
                else:
                    for user_survey in current_user.surveys.values():
                        if not user_survey.completed_on:
                            parent_type, parent_id = user_survey.survey.parent_type, user_survey.survey.parent_id
                            if parent_type and parent_id:
                                endpoint = 'web.show_{0}'.format(singularize(parent_type))
                                view_args = {'{0}_id'.format(singularize(parent_type)): parent_id}
                                url = url_for(endpoint, **view_args)
                            else:
                                url = url_for('web.show_user', user_id=current_user.id)
                            flash(Markup(
                                'You have not completed the survey. Please complete the '
                                '<a href="{href}#survey" class="alert-link">{title}</a>.'.format(
                                    href=url,
                                    title=user_survey.title
                                )), category='warning')
                            break


########################################################################################################################
# register blueprint
########################################################################################################################
app.register_blueprint(web)
