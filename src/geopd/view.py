from random import randint
import markdown

from flask import Markup
from flask import abort
from flask import flash
from flask import redirect
from flask import render_template
from flask import send_from_directory
from flask_login import login_required
from inflection import singularize
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import noload
from sqlalchemy import desc

from can.web import app
from can.web.form import ChangeAddressForm
from can.web.email import send_email

from geopd.form import PostForm
from geopd.form import UpdateSurveyForm
from geopd.form import ProjectPostForm
from geopd.form import ModalForm
from werkzeug.utils import secure_filename

from geopd.orm.model import *
from geopd.web import blueprint as web

SURVEY_PROFILE = 1
SURVEY_BIOLOGY = 2
SURVEY_COMMUNICATION = 3
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'])


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
    return render_template('/projects/index.html', projects=Project.query.order_by(desc(Project.id)).all())

def make_tree(path):
    tree = dict(name=os.path.basename(path), children=[])
    try:
        lst = os.listdir(path)
    except OSError:
        pass #ignore errors
    else:
        for name in lst:
            name = name.decode('utf8').encode('ascii', 'ignore')
            fn = os.path.join(path, name)
            if os.path.isdir(fn):
                tree['children'].append(make_tree(fn))
            else:
                tree['children'].append(dict(name=name))
    return tree


@web.route('/projects/<int:project_id>')
@login_required
def show_project(project_id):
    admin = current_user.is_authenticated and Permission.MANAGE_USER_ACCOUNT in current_user.permissions

    p = Project.query.get(project_id)
    pm = ProjectMember.query\
        .filter(ProjectMember.project_id == project_id)\
        .filter(ProjectMember.member_id == current_user.id)\
        .filter(ProjectMember.investigator == True).count()

    is_member = True if current_user in p.members else False
    is_investigator = True if pm > 0 else False

    tree = make_tree(os.path.join(app.config["PRIVATE_DIR"], "projects", str(project_id)))
    filename = os.path.join('texts', '{0}.md'.format(project_id))
    file_path = pkg_resources.resource_filename('geopd', os.path.join('static', filename))

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = Markup(markdown.markdown(f.read()))
            return render_template('projects/project.html', project=Project.query.get(project_id), form=ProjectPostForm(),
                           is_member=is_member, is_investigator=is_investigator, tree=tree, content=content, admin=admin)

    return render_template('projects/project.html', project=Project.query.get(project_id), form=ProjectPostForm(),
                           is_member=is_member, is_investigator=is_investigator, tree=tree, content="", admin=admin)


@web.route('/projects/<int:project_id>/<path:dir>/<path:filename>', defaults={'subdir': ""})
@web.route('/projects/<int:project_id>/<path:dir>/<path:subdir>/<path:filename>')
@login_required
def send_file(project_id, dir, subdir, filename):
    return send_from_directory(os.path.join(app.config["PRIVATE_DIR"], "projects", str(project_id), dir, subdir), filename)


@web.route('/projects/<int:project_id>/manage')
@login_required
def show_manage_project(project_id):
    return render_template('projects/manage_members.html', project=Project.query.get(project_id))


@web.route('/projects/<int:project_id>/manage', methods=['POST'])
@login_required
def update_project_members(project_id):
    user_ids = [int(user_id) for user_id in request.form.getlist('users[]')]
    invs = ProjectMember.query \
        .filter(ProjectMember.project_id == project_id) \
        .filter(ProjectMember.member_id.in_(user_ids)) \
        .filter(ProjectMember.investigator == True).all()
    inv_user_ids = [int(inv.member_id) for inv in invs]
    user_ids = list(set(user_ids) - set(inv_user_ids))

    for user_id in user_ids:
        db.merge(ProjectMember(project_id, user_id, False))
        db.flush()
    db.commit()

    return '', 204


@web.route('/projects/<int:project_id>/manage/remove', methods=['POST'])
@login_required
def remove_project_members(project_id):
    user_ids = [int(user_id) for user_id in request.form.getlist('users[]')]

    ProjectMember.query\
        .filter(ProjectMember.member_id.in_(user_ids))\
        .filter(ProjectMember.project_id == project_id)\
        .filter(ProjectMember.investigator == False).delete(synchronize_session='fetch')
    db.commit()

    return '', 204

########################################################################################################################
# publications
########################################################################################################################
@web.route('/publications/')
def show_publications():
    publications = Publication.query.order_by(Publication.published_on.desc()).all()
    return render_template('publications.html', publications=publications)


########################################################################################################################
# surveys
########################################################################################################################
@web.route('/surveys/')
@login_required
def show_surveys():
    return render_template('surveys/index.html', surveys=Survey.query.join(Survey.questions)
                           .options(joinedload('questions')))


@web.route('/surveys/<int:survey_id>')
@login_required
def show_survey(survey_id):
    return render_template('surveys/survey.html', survey=Survey.query.get(survey_id))


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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@web.route('/projects/<int:project_id>/posts/', methods=['POST'])
@login_required
def create_project_post(project_id):
    form = PostForm()

    if form.validate_on_submit():
        project = Project.query.options(noload('posts')).get(project_id)
        uploaded_files = request.files.getlist("project_upload[]")

        title, body = (request.form.get(key) for key in ('title', 'body'))

        if not title:
            flash('Please provide a post title', 'danger')
        elif not body:
            flash('Please provide post content', 'danger')
        else:
            new_post = ProjectPost(title, body)
            project.posts.append(new_post)
            db.flush()

            try:
                db.commit()
            except SQLAlchemyError:
                flash('Error creating the post. Please try again later.', 'danger')
            else:
                if uploaded_files:
                    for f in uploaded_files:
                        if allowed_file(f.filename):
                            filename = secure_filename(f.filename)
                            save_path = os.path.join(app.config['UPLOAD_FOLDER'], "project_post_uploads",
                                                     str(project_id), str(new_post.id))
                            if not os.path.exists(save_path):
                                os.makedirs(save_path)
                            f.save(os.path.join(save_path, filename))

                for user in project.members:
                    if not user == current_user:
                        send_email(user.email, "GEoPD - {0} Discussion Board Updated".format(project.name), "email/project_board_update", user=user, project=project, title=title, body=body)



    return redirect(url_for('web.show_project', project_id=project_id))


@web.route('/projects/<int:project_id>/posts/<int:post_id>')
@login_required
def show_project_post(project_id, post_id):
    post = ProjectPost.query.get(post_id)
    if not post or post.project_id != project_id:
        abort(404)

    uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'], "project_post_uploads", str(project_id), str(post_id))
    uploaded_files = []
    if os.path.exists(uploaded_path):
        uploaded_files = [f for f in os.listdir(uploaded_path)]

    return render_template('/projects/post.html', post=post, uploaded_files=uploaded_files)


@web.route('/projects/<int:project_id>/posts/<int:post_id>', methods=['POST'])
@login_required
def update_project_post(project_id, post_id):
    post = ProjectPost.query.get(post_id)
    if not post or post.project_id != project_id:
        abort(404)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.commit()
    return '', 204


@web.route('/projects/<int:project_id>/<int:post_id>/<string:filename>')
@login_required
def send_post_file(project_id, post_id, filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], "project_post_uploads", str(project_id), str(post_id)), filename)


@web.route('/communications/')
def show_communications():
    if current_user.is_authenticated:
        return render_template('communications/index.html', form=PostForm(), affiliations=Affiliation.query.order_by(Affiliation.id).all())

    return render_template('communications/public/index.html')


@web.route('/communications/posts', methods=['POST'])
@login_required
def create_communications_post():
    form = PostForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist("communications_post_upload[]")
        title, body = (request.form.get(key) for key in ('title', 'body'))
        aff = request.form.getlist('affiliations')

        if not title:
            flash('Please provide a post title', 'danger')
        elif not body:
            flash('Please provide post content', 'danger')
        else:
            new_post = ComPost(title, body)

            if not aff:
                aff = [Affiliation.query.filter(Affiliation.name=='General').first().id]

            # adding records to association table using many to many relationship.
            affs = Affiliation.query.filter(Affiliation.id.in_(aff)).all()
            aff_names = [item.name for item in affs]

            new_post.affiliations = affs

            db.add(new_post)
            db.flush()

            try:
                db.commit()
            except SQLAlchemyError:
                flash('Error creating the post. Please try again later.', 'danger')
            else:
                if uploaded_files:
                    for f in uploaded_files:
                        if allowed_file(f.filename):
                            filename = secure_filename(f.filename)
                            save_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                                     "communication_post_uploads", str(new_post.id))
                            if not os.path.exists(save_path):
                                os.makedirs(save_path)
                            f.save(os.path.join(save_path, filename))

                sq = SurveyQuestion.query.filter(SurveyQuestion.name=='communications').first()
                responses = sq.responses

                users_aff = []
                for user_response in responses:
                    for choice in user_response.answer_choices:
                        if choice.label in aff_names:
                            users_aff.append(user_response.user_survey.user)

                if users_aff:
                    users_aff = set(users_aff)
                    if current_user in users_aff:
                        users_aff.remove(current_user)

                    users_aff = list(users_aff)
                    if users_aff:
                        for user in users_aff:
                            send_email(user.email, "GEoPD Communications Board Updated", "email/communications_board_update",
                                   user=user, current_user=current_user)

    return redirect(url_for('web.show_communications'))


@web.route('/communications/posts/<int:post_id>')
@login_required
def show_communications_post(post_id):
    post = ComPost.query.get(post_id)

    uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'],"communication_post_uploads", str(post_id))
    uploaded_files = []

    if os.path.exists(uploaded_path):
        uploaded_files = [f for f in os.listdir(uploaded_path)]

    return render_template('/communications/post.html', post=post, uploaded_files=uploaded_files)


@web.route('/communications/posts/<int:post_id>', methods=['POST'])
@login_required
def update_communications_post(post_id):
    post = ComPost.query.get(post_id)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.commit()

    return '', 204


@web.route('/communications/<int:post_id>/<string:filename>')
@login_required
def send_communications_post_file(post_id, filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"],"communication_post_uploads", str(post_id)), filename)


@web.route('/cores/<int:core_id>/posts/', methods=['POST'])
@login_required
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


@web.route('/cores/<int:core_id>/posts/<int:post_id>')
@login_required
def show_core_post(core_id, post_id):
    post = CorePost.query.get(post_id)
    if not post or post.core_id != core_id:
        abort(404)
    return render_template('/cores/post.html', post=post)


@web.route('/cores/<int:core_id>/posts/<int:post_id>', methods=['POST'])
@login_required
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
    admin = current_user.is_authenticated and Permission.MANAGE_USER_ACCOUNT in current_user.permissions
    return render_template(tpl, users=users, admin=admin)


@web.route('/users/<int:user_id>')
@login_required
def show_user(user_id):
    user = User.query.options(joinedload('avatar'),
                              joinedload('bio'),
                              joinedload('address')).filter(User.id == user_id).one()

    if user.status_id != User.STATUS.ACTIVE:
        abort(404)

    survey = Survey.query.get(SURVEY_PROFILE)
    communication_survey = Survey.query.get(SURVEY_COMMUNICATION)

    affiliations = Affiliation.query.filter(Affiliation.hidden==False).order_by(Affiliation.id).all()

    return render_template('users/profile.html',
                           user=user,
                           address_form=ChangeAddressForm(),
                           survey_form=UpdateSurveyForm(),
                           survey=survey,
                           communication_survey=communication_survey)

@web.route('/users/<int:user_id>/surveys/<int:survey_id>', methods=['POST'])
@login_required
def update_user_survey(user_id, survey_id):
    if user_id != current_user.id:
        abort(403)

    survey_form = UpdateSurveyForm()

    if survey_form.validate_on_submit():

        user_survey = current_user.surveys[survey_id]

        for name in user_survey.survey.questions.keys():
            print name
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
# global functionality
########################################################################################################################


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
