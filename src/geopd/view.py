from random import randint
import markdown

from flask import Markup
from flask import abort
from flask import flash
from flask import redirect
from flask import render_template
from flask import send_from_directory
from flask import current_app, make_response

from flask_login import login_required
from inflection import singularize
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import noload
from sqlalchemy import desc
from sqlalchemy import event
from geopd.core import app, csrf
from geopd.core import send_email
from geopd.core.form import ChangeAddressForm
from geopd.core.auth import RegistrationForm
from geopd.form import PostForm
from geopd.form import UpdateSurveyForm
from geopd.form import ProjectPostForm
from geopd.form import ModalForm
from werkzeug.utils import secure_filename
from flask import jsonify
import json
from pyPdf import PdfFileWriter, PdfFileReader



from geopd.orm.model import *


SURVEY_PROFILE = 1
SURVEY_BIOLOGY = 2
SURVEY_COMMUNICATION = 3
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'rtf'])


from geopd.core import mail
from flask_mail import Message
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email_async(to, subject, template_name, **context):
    subject = "[{0}] {1}".format(app.config['APP_NAME'], subject)
    msg = Message(subject,
                  sender='"{0}" <{1}>'.format(app.config['APP_NAME'], app.config['MAIL_USERNAME']),
                  recipients=[to])
    msg.body = render_template(template_name + '.txt', **context)
    msg.html = render_template(template_name + '.html', **context)

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()


########################################################################################################################
# main page
########################################################################################################################
@app.route('/')
def index():
    if not current_user.is_anonymous:
        # return redirect(url_for('show_user', user_id=current_user.id))
        return redirect(url_for('news'))

    return render_template('welcome.html', cores=Core.query.all(),
                           meetings=Meeting.query.filter(Meeting.carousel).order_by(Meeting.year.desc()).all())


########################################################################################################################
# news
########################################################################################################################
@app.route('/news')
def news():

    survey_not_finished = []
    for k, survey in current_user.surveys.iteritems():
        if survey.completed_on:
            pass
        else:
            survey_not_finished.append(survey)


    return render_template('news.html', posts=ComPost.query.order_by(ComPost.created_on.desc()).limit(5).all(), myProjects=current_user.mprojects, surveys=survey_not_finished)



########################################################################################################################
# about us
########################################################################################################################
@app.route('/about/')
def show_about():
    return render_template('about.html')


########################################################################################################################
# annual meetings
########################################################################################################################
@app.route('/meetings/')
def show_meetings():
    meeting = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).first()
    return redirect(url_for('show_meeting', id=meeting.id))


@app.route('/meetings/<int:id>')
def show_meeting(id):
    meeting = Meeting.query.get(id)
    if not meeting.program:
        abort(404)
    meetings = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).all()
    return render_template('meetings/index.html', meeting=meeting, meetings=meetings)




@app.route('/pictures/<int:picture_id>')
@login_required
def send_pictures(picture_id):
    p = Picture.query.filter(Picture.id==picture_id).one()
    file_name = os.path.basename(p.stored_path)
    dir_name = os.path.dirname(p.stored_path)

    return send_from_directory(os.path.join('static', dir_name), file_name)


# @app.route('/pictures/static/')
#
# @app.route('/projects/<int:project_id>/<path:dir>/<path:filename>', defaults={'subdir': ""})
# @app.route('/projects/<int:project_id>/<path:dir>/<path:subdir>/<path:filename>')
# @login_required
# def send_file(project_id, dir, subdir, filename):
#     return send_from_directory(os.path.join(app.config["PRIVATE_DIR"], "projects", str(project_id), dir, subdir), filename)

########################################################################################################################
# projects
########################################################################################################################
@app.route('/projects/')
def show_projects():
    project_members = ProjectMember.query.filter(ProjectMember.investigator).all()
    return render_template('/projects/index.html', projects=Project.query.order_by(desc(Project.id)).all(), project_members=ProjectMember)


@app.route('/projects/<int:project_id>')
def show_project(project_id):
    p = Project.query.get(project_id)
    read_contents_dict = {}
    for category in p.categories:
        for file in category.content_files:
            if file.read_and_show:
                full_path = os.path.join(app.config["PRIVATE_DIR"], file.file_url)
                if os.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        read_contents = Markup(markdown.markdown(f.read()))
                        read_contents_dict.update({category.id: read_contents})

    if current_user.is_anonymous:
        return render_template('projects/public.html', project=Project.query.get(project_id), read_contents=read_contents_dict)

    else:
        admin = current_user.is_authenticated and Permission.MANAGE_USER_ACCOUNT in current_user.permissions

        pm = ProjectMember.query\
            .filter(ProjectMember.project_id == project_id)\
            .filter(ProjectMember.member_id == current_user.id)\
            .filter(ProjectMember.investigator == True).count()

        is_member = True if current_user in p.members else False
        is_investigator = True if pm > 0 else False

        return render_template('projects/project.html', project=Project.query.get(project_id), form=ProjectPostForm(),
                               is_member=is_member, is_investigator=is_investigator, read_contents=read_contents_dict, admin=admin)


@app.route('/projects/<int:project_id>/<path:dir>/<path:filename>', defaults={'subdir': ""})
@app.route('/projects/<int:project_id>/<path:dir>/<path:subdir>/<path:filename>')
@login_required
def send_file(project_id, dir, subdir, filename):
    return send_from_directory(os.path.join(app.config["PRIVATE_DIR"], "projects", str(project_id), dir, subdir), filename)


@app.route('/projects/<int:project_id>/create_project_category')
def create_project_category(project_id):

    return render_template('projects/create_projecte_category', project=Project.query.get(project_id))


@app.route('/projects/<int:project_id>/manage_members')
@login_required
def show_manage_project_members(project_id):
    return render_template('projects/manage_members.html', project=Project.query.get(project_id))


@app.route('/projects/<int:project_id>/manage_project')
@login_required
def show_manage_project(project_id):
    return render_template('projects/manage_project.html', project=Project.query.get(project_id), )


@app.route('/projects/manage_category/')
@login_required
def show_manage_categories():
    return render_template('projects/manage_category.html')


@app.route('/projects/<int:project_id>/manage_category/<int:category_id>')
@login_required
def show_manage_category(project_id, category_id):
    return render_template('projects/manage_category.html',
                           project=Project.query.get(project_id),
                           category=ProjectCategory.query.get(category_id))


@app.route('/projects/<int:project_id>/manage', methods=['POST'])
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
        db.session.merge(ProjectMember(project_id, user_id, False))
        db.session.flush()
    db.session.commit()

    return '', 204


@app.route('/projects/<int:project_id>/manage/remove', methods=['POST'])
@login_required
def remove_project_members(project_id):
    user_ids = [int(user_id) for user_id in request.form.getlist('users[]')]

    ProjectMember.query\
        .filter(ProjectMember.member_id.in_(user_ids))\
        .filter(ProjectMember.project_id == project_id)\
        .filter(ProjectMember.investigator == False).delete(synchronize_session='fetch')
    db.session.commit()

    return '', 204

import Bio.Entrez

########################################################################################################################
# publications
########################################################################################################################
@app.route('/publications/', methods=['GET', 'POST'])
@login_required
def show_publications():
    publications = Publication.query.order_by(Publication.published_on.desc()).all()

    if request.method == 'POST':
    #     p_id = request.form.get("p_id")
    #     title = request.form.get("title")
        file = request.files['publications_upload']
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.static_folder, 'upload', filename))

            with open(os.path.join(current_app.static_folder, 'upload', filename)) as f:
                pdf_reader = PdfFileReader(f)
                title = pdf_reader.getDocumentInfo().title
                if title:
                    print title
                else:
                    os.remove(os.path.join(current_app.static_folder, 'upload', filename))

    return render_template('publications.html', publications=publications, form=PostForm())


@app.route('/publications/add', methods=['GET', 'POST'])
def add_publications():
    return render_template('pubmed.html')


def find_pubmed(title):
    Bio.Entrez.email = 'ozabaneh@can.ubc.ca'
    Bio.Entrez.tool = 'geopd.orm.util'
    handle = Bio.Entrez.esearch(db="PubMed", retmax=100, term=title)
    record = Bio.Entrez.read(handle)
    ids = record.get("IdList")
    return ids


@app.route('/_search_pubmed')
def search_pubmed():
    title = request.args.get('title')
    print title

    Bio.Entrez.email = 'ozabaneh@can.ubc.ca'
    Bio.Entrez.tool = 'geopd.orm.util'
    handle = Bio.Entrez.esearch(db="PubMed", retmax=100, term=title)
    record = Bio.Entrez.read(handle)
    ids = record.get("IdList")
    print ids
    if ids:
        handle = Bio.Entrez.esummary(db='pubmed', id=",".join(str(x) for x in ids))
        records = Bio.Entrez.read(handle)
        handle.close()
        return jsonify(result=json.dumps(records))
    else:
        return jsonify(result=json.dumps({}))

########################################################################################################################
# surveys
########################################################################################################################
@app.route('/surveys/')
@login_required
def show_surveys():
    return render_template('surveys/index.html', surveys=Survey.query.join(Survey.questions)
                           .options(joinedload('questions')))


@app.route('/surveys/<int:survey_id>')
@login_required
def show_survey(survey_id):
    return render_template('surveys/survey.html', survey=Survey.query.get(survey_id))


########################################################################################################################
# cores
########################################################################################################################
@app.route('/cores/')
def show_cores():
    return show_core(core_id=1)


@app.route('/cores/<int:core_id>')
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


@app.route('/projects/<int:project_id>/posts/', methods=['POST'])
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
            db.session.flush()

            try:
                db.session.commit()
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

                members_email = []

                for user in project.members:
                    if not user == current_user:
                        members_email.append(user.email)

                send_email(current_user.email, "{0} Discussion Board Update".format(project.name),
                           "email/project_board_update", cc=members_email, current_user=current_user, project=project,
                           title=title)



    return redirect(url_for('show_project', project_id=project_id))


@app.route('/projects/delete_posts', methods=['POST'])
@login_required
def delete_project_posts():
    post_id_list = [int(post_id) for post_id in request.form.getlist('posts[]')]
    for pp in ProjectPost.query.filter(ProjectPost.id.in_(post_id_list)):
        pp.deleted = True
    db.session.commit()

    return '', 204


@app.route('/projects/<int:project_id>/posts/<int:post_id>')
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


@app.route('/projects/<int:project_id>/posts/<int:post_id>', methods=['POST'])
@login_required
def update_project_post(project_id, post_id):
    post = ProjectPost.query.get(post_id)
    if not post or post.project_id != project_id:
        abort(404)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.session.commit()
    return '', 204


@app.route('/projects/<int:project_id>/<int:post_id>/<string:filename>')
@login_required
def send_post_file(project_id, post_id, filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], "project_post_uploads", str(project_id), str(post_id)), filename)


@app.route('/communications/')
def show_communications():
    if current_user.is_authenticated:
        return render_template('communications/index.html', form=PostForm(), pictures=Picture.query.all(), affiliations=Affiliation.query.order_by(Affiliation.id).all())

    return render_template('communications/public/index.html')


@app.route('/communications/posts', methods=['POST'])
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

            db.session.add(new_post)
            db.session.flush()

            try:
                db.session.commit()
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

                all_emails = []

                for user in User.query.filter(User.status_id == 1).all():
                    all_emails.append(user.email)

                # for testing
                # all_emails = ["jjuhn@can.ubc.ca", "jjuhn1119@gmail.com"]

                if "General" in aff_names:
                    send_email(current_user.email, "Communications Board Updated", "email/communications_board_general_update", cc=all_emails, current_user=current_user, title=title)

                else:
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
                                send_email_async(user.email, "Communications Board Updated", "email/communications_board_update",
                                       user=user, current_user=current_user)

    return redirect(url_for('show_communications'))


@app.route('/communications/posts/<int:post_id>')
@login_required
def show_communications_post(post_id):
    post = ComPost.query.get(post_id)

    uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'],"communication_post_uploads", str(post_id))
    uploaded_files = []

    if os.path.exists(uploaded_path):
        uploaded_files = [f for f in os.listdir(uploaded_path)]

    return render_template('/communications/post.html', post=post, uploaded_files=uploaded_files)


@app.route('/communications/posts/<int:post_id>', methods=['POST'])
@login_required
def update_communications_post(post_id):
    post = ComPost.query.get(post_id)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.session.commit()

    return '', 204


@app.route('/communications/<int:post_id>/<string:filename>')
@login_required
def send_communications_post_file(post_id, filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"],"communication_post_uploads", str(post_id)), filename)


@app.route('/cores/<int:core_id>/posts/', methods=['POST'])
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
                db.session.commit()
            except SQLAlchemyError:
                flash('Error creating the post. Please try again later.', 'danger')

    return redirect(url_for('show_core', core_id=core_id))


@app.route('/cores/<int:core_id>/posts/<int:post_id>')
@login_required
def show_core_post(core_id, post_id):
    post = CorePost.query.get(post_id)
    if not post or post.core_id != core_id:
        abort(404)
    return render_template('/cores/post.html', post=post)


@app.route('/cores/<int:core_id>/posts/<int:post_id>', methods=['POST'])
@login_required
def update_core_post(core_id, post_id):
    post = CorePost.query.get(post_id)
    if not post or post.core_id != core_id:
        abort(404)

    post.body = request.form.get('body')
    post.updated_on = datetime.utcnow()
    db.session.commit()
    return '', 204


@app.route('/projects/<int:project_id>/join')
@login_required
def email_investigators(project_id):
    project = Project.query.get(project_id)
    # lazy = dynamic on project with members so I could filter the result by association table ProjectMember
    # require change later on since it won't work with jsonapi

    investigators = project.members.filter(ProjectMember.investigator).all()

    for investigator in investigators:
        send_email(investigator.email,
                   "New member Request for {0} project".format(project.name),
                   "email/new_project_member_request",
                   user=investigator, current_user=current_user, project=project)

    flash('Email request sent to investigators', category='success')

    return redirect(url_for('show_project', project_id=project_id))


########################################################################################################################
# users
########################################################################################################################
@app.route('/users/')
def show_users():
    users = User.query.options(joinedload('address'))
    tpl = 'users/public.html' if current_user.is_anonymous else 'users/index.html'
    admin = current_user.is_authenticated and Permission.MANAGE_USER_ACCOUNT in current_user.permissions
    return render_template(tpl, users=users, admin=admin)


@app.route('/users/<int:user_id>')
@login_required
def show_user(user_id):
    user = User.query.options(joinedload('avatar'),
                              joinedload('bio'),
                              joinedload('address')).filter(User.id == user_id).one()

    # if user.status_id != User.STATUS.ACTIVE:
    #     abort(404)

    survey = Survey.query.get(SURVEY_PROFILE)
    communication_survey = Survey.query.get(SURVEY_COMMUNICATION)

    # affiliations = Affiliation.query.filter(Affiliation.hidden==False).order_by(Affiliation.id).all()

    return render_template('users/profile.html',
                           user=user,
                           address_form=ChangeAddressForm(),
                           survey_form=UpdateSurveyForm(),
                           survey=survey,
                           communication_survey=communication_survey)

@app.route('/users/<int:user_id>/surveys/<int:survey_id>', methods=['POST'])
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
            db.session.add(response)
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
            db.session.commit()
        except SQLAlchemyError:
            raise
        else:
            flash('Survey information updated.', category='success')

    return redirect(request.referrer or url_for('index'))


@app.route('/users/<int:user_id>/biography', methods=['POST'])
@login_required
def update_user_biography(user_id):
    if user_id != current_user.id:
        abort(403)

    name = request.form.get('name')
    if name == 'interest':
        current_user.bio.research_interests = request.form['value'].strip()
    elif name == 'experience':
        current_user.bio.research_experience = request.form['value'].strip()

    db.session.commit()

    return '', 204

@app.route('/test', methods=['GET','POST'])
@login_required
def test():
    form = PostForm
    if request.method == 'POST':
        print request.files

    return render_template('/test.html', form=form)


def gen_rnd_filename():
    import random
    filename_prefix = datetime.now().strftime('%Y%m%d%H%M%S')
    return '%s%s' % (filename_prefix, str(random.randrange(1000, 10000)))



@app.route('/ckupload', methods=['POST', 'OPTIONS'])
@login_required
@csrf.exempt
def ckupload():
    """CKEditor file upload"""
    error = ''
    url = ''
    print request
    callback = request.args.get("CKEditorFuncNum")
    if request.method == 'POST' and 'upload' in request.files:
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        rnd_name = '%s%s' % (gen_rnd_filename(), fext)
        filepath = os.path.join(current_app.static_folder, 'upload', rnd_name)
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                error = 'ERROR_CREATE_DIR'
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'
        if not error:
            fileobj.save(filepath)
            url = url_for('static', filename='%s/%s' % ('upload', rnd_name))
    else:
        error = 'post error'

    response = {
        "uploaded":1,
        "fileName": rnd_name,
        "url": url,
        "error": error
    }

    return jsonify(response)




# @app.route("/registration", methods=['GET', 'POST'])
# def registration():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#
#     form = RegistrationForm()
#     if form.validate_on_submit():
#         selected_committee = request.form.get("referrer")
#         committee = User.query.get(selected_committee) if selected_committee else None
#
#         user = User(email=form.email.data, password=form.password.data, name=form.name.data)
#         user.address.load(request.form)
#         db.session.add(user)
#
#         try:
#             db.session.flush()
#
#         except SQLAlchemyError as e:
#             db.session.rollback()
#             flash('Error while processing request. Please try again later', 'warning')
#
#         else:
#             token = user.generate_confirmation_token()
#             # send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
#             print "hihi"
#             print committee
#
#             # if committee:
#             #     send_email(committee.email, "Requesting activation of new user.",
#             #                'email/new_member_request', user=user, committee=committee)
#
#             flash('A confirmation email has been sent to your email address', 'success')
#             db.session.commit()
#             return redirect(url_for('index'))
#
#     # flash form errors if necessary
#     for error in form.errors.values():
#         flash(error[0], 'danger')
#
#     return render_template('auth_geopd/register.html', form=form,
#                            steering_committee=Permission.query.get(2).users,
#                            admin=Permission.query.get(Permission.MANAGE_USER_ACCOUNT).users)


########################################################################################################################
# global functionality
########################################################################################################################


@app.before_request
def before_request():
    if current_user.is_authenticated:
        if request.endpoint == 'web.show_core':
            if 1 == randint(1, 2):
                if not current_user.bio.research_interests or not current_user.bio.research_experience:
                    flash(Markup(
                        'Your biography is not up to date. '
                        '<a href="{0}" class="alert-link">Update my biography</a>.'.format(
                            url_for('show_user', user_id=current_user.id))), category='warning')
                else:
                    for user_survey in current_user.surveys.values():
                        if not user_survey.completed_on:
                            parent_type, parent_id = user_survey.survey.parent_type, user_survey.survey.parent_id
                            if parent_type and parent_id:
                                endpoint = 'web.show_{0}'.format(singularize(parent_type))
                                view_args = {'{0}_id'.format(singularize(parent_type)): parent_id}
                                url = url_for(endpoint, **view_args)
                            else:
                                url = url_for('show_user', user_id=current_user.id)
                            flash(Markup(
                                'You have not completed the survey. Please complete the '
                                '<a href="{href}#survey" class="alert-link">{title}</a>.'.format(
                                    href=url,
                                    title=user_survey.title
                                )), category='warning')
                            break


@event.listens_for(User, 'after_insert')
def update_referrer_after_insert_user(mapper, connection, target):
    referrer_id = request.form.get('referrer')
    referrer = User.query.get(referrer_id)
    ur = UserReferrer(target, referrer)
    db.session.add(ur)


def get_comment_post(comment):
    if comment.parent:
        return get_comment_post(comment.parent)
    else:
        return comment.com_post

def get_project_comment_post(comment):
    if comment.parent:
        return get_project_comment_post(comment.parent)
    else:
        return comment.project_post




def get_immediate_parent_comment(comment):
    if comment.parent:
        return comment.parent


@event.listens_for(ComPostComment, 'after_insert')
def email_post_creator(mapper, connection, target):
    try:
        post_for_this_comment = get_comment_post(target)
        parent_comment = get_immediate_parent_comment(target)

        if parent_comment and not (parent_comment.author == target.author):
            commentor = target.author
            parent_commentor = parent_comment.author

            send_email_async(parent_commentor.email,
                             "{0} has commented on your comment.".format(commentor.name.full),
                             "email/new_comments_parents", post_id=post_for_this_comment.id, commentor=commentor, owner=parent_commentor)

        if post_for_this_comment and not (post_for_this_comment.author == target.author):
            owner = post_for_this_comment.author
            commentor = target.author

            send_email_async(owner.email,
                         "{0} has commented on your post.".format(commentor.name.full),
                         "email/new_comments", post_id=post_for_this_comment.id, commentor=commentor, owner=owner)

    except Exception as e:
        print str(e)


@event.listens_for(ProjectPostComment, 'after_insert')
def email_project_post_creator(mapper, connection, target):
    try:
        post_for_this_comment = get_project_comment_post(target)
        parent_comment = get_immediate_parent_comment(target)

        if parent_comment and not (parent_comment.author == target.author):
            print "here"
            commentor = target.author
            parent_commentor = parent_comment.author

            send_email_async(parent_commentor.email,
                             "{0} has commented on your comment.".format(commentor.name.full),
                             "email/new_project_comments_parents", project=post_for_this_comment.project, post_id=post_for_this_comment.id, commentor=commentor,
                             owner=parent_commentor)

        if post_for_this_comment and not (post_for_this_comment.author == target.author):
            owner = post_for_this_comment.author
            commentor = target.author

            send_email_async(owner.email,
                             "{0} has commented on your post.".format(commentor.name.full),
                             "email/new_project_comments", project=post_for_this_comment.project, post_id=post_for_this_comment.id, commentor=commentor,
                             owner=owner)

    except Exception as e:
        print str(e)




#
# @app.errorhandler(404)
# def not_found_error(error):
#     print "not found"
#
# @app.errorhandler(500)
# def internal_error(error):
#     print "internal server error"


# import scholarly
#
#
# print
