from flask import Blueprint
from flask import render_template
from flask import abort
from flask import redirect
from flask import flash
from flask import escape
from flask import make_response
from flask import send_from_directory
from flask_login import login_required

from geopd import app
from geopd.config import config
from geopd.orm.model import *
from geopd.form import ContactForm
from geopd.form import CompleteSurveyForm
from geopd.form import ChangeAddressForm
from geopd.form import PostForm
from geopd.email import send_email

from sqlalchemy.orm import joinedload

web = Blueprint('web', __name__)
ajax = Blueprint('ajax', __name__)  # todo:: to be replaced with api blueprint


########################################################################################################################
# main page
########################################################################################################################
@web.route('/')
def index():
    if not current_user.is_anonymous:
        return redirect(url_for('web.show_user', id=current_user.id))

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
    return redirect(url_for('web.show_core', id=1))


@web.route('/cores/<int:id>', methods=['GET', 'POST'])
def show_core(id):
    form = PostForm()
    core = Core.query.get(id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            abort(403)
        post = CorePost(body=request.form.get('body', ''))
        core.posts.append(post)
        db.commit()
    return render_template('cores/index.html',
                           form=form,
                           core=core,
                           cores=Core.query.all())


########################################################################################################################
# members
########################################################################################################################
@web.route('/users/')
def show_users():
    users = User.query.options(joinedload('address'))
    tpl = 'users/public.html' if current_user.is_anonymous else 'users/index.html'
    return render_template(tpl, users=users)


@web.route('/users/<int:id>')
@login_required
def show_user(id):
    return render_template('users/profile.html',
                           user=User.query.options(joinedload('avatar'),
                                                   joinedload('bio'),
                                                   joinedload('address'),
                                                   joinedload('survey'),
                                                   joinedload('survey', 'clinical'),
                                                   joinedload('survey', 'epidemiologic'),
                                                   joinedload('survey', 'biospecimen')).filter(User.id == id).one(),
                           survey_form=CompleteSurveyForm(),
                           address_form=ChangeAddressForm(),
                           clinical=ClinicalSurvey.query.all(),
                           epidemiologic=EpidemiologicSurvey.query.all(),
                           biospecimen=BiospecimenSurvey.query.all())


@web.route('/users/<int:id>/address', methods=['POST'])
@login_required
def update_user_address(id):
    if id != current_user.id:
        abort(403)

    address_form = ChangeAddressForm()
    if address_form.validate_on_submit():
        address = UserAddress.query.get(id)
        address.load(request.form)
        try:
            db.commit()
        except:
            flash('Failed to save new address. Try again later', category='danger')
        else:
            flash('New address saved.', category='success')

        return redirect(url_for('web.show_user', id=id))


@web.route('/users/<int:id>/survey', methods=['POST'])
@login_required
def update_user_survey(id):
    if id != current_user.id:
        abort(403)

    address_form = ChangeAddressForm()
    if address_form.validate_on_submit():
        survey = UserSurvey.query.get(id)
        survey.completed_on = datetime.utcnow()

        try:
            db.commit()
        except:
            flash('Something went wrong. Try again later', category='danger')
        else:
            flash('Survey marked as complete.', category='success')

    return redirect(url_for('web.show_user', id=id))

@web.route('/users/<int:id>/avatar')
@login_required
def get_user_avatar(id):
    avatar = UserAvatar.query.get(id)
    if not avatar.data:
        return app.send_static_file('images/avatar.png')

    response = make_response(avatar.data)
    response.headers['Content-Type'] = avatar.mimetype
    return response


@ajax.route('/users/<int:id>/info/', methods=['POST'])
@login_required
def update_user_info(id):
    if id != current_user.id:
        abort(403)  # unauthorized

    name = request.form.get('name', None)

    if name == 'clinical':
        obj = ClinicalSurvey.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.survey.clinical.remove(obj)
        else:
            if obj not in current_user.survey.clinical:
                current_user.survey.clinical.append(obj)

    elif name == 'epidemiologic':
        obj = EpidemiologicSurvey.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.survey.epidemiologic.remove(obj)
        else:
            if obj not in current_user.survey.epidemiologic:
                current_user.survey.epidemiologic.append(obj)

    elif name == 'biospecimen':
        obj = BiospecimenSurvey.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.survey.biospecimen.remove(obj)
        else:
            if obj not in current_user.survey.biospecimen:
                current_user.survey.biospecimen.append(obj)

    elif name == 'ethical':
        current_user.survey.ethical = False if request.form['value'] == 'no' else True

    elif name == 'ethical-explain':
        value = escape(request.form['value'])
        current_user.survey.ethical_explain = value
        return value

    elif name == 'consent':
        current_user.survey.consent = False if request.form['value'] == 'no' else True

    elif name == 'consent-explain':
        value = escape(request.form['value'])
        current_user.survey.consent_explain = value
        return value

    elif name == 'sharing':
        current_user.survey.consent_sharing = False if request.form['value'] == 'no' else True

    elif name == 'sample':
        current_user.survey.sample = False if request.form['value'] == 'no' else True

    elif name == 'interest':
        value = escape(request.form['value'])
        current_user.bio.research_interests = value
        return value

    elif name == 'experience':
        value = escape(request.form['value'])
        current_user.bio.research_experience = value
        return value

    elif name == 'avatar':
        current_user.avatar.data = request.files[name].stream.read()
        current_user.avatar.avatar.mimetype = request.files[name].mimetype

    else:
        abort(400)

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
        send_email(config.get('mail', 'contact'), 'Contact Form', 'auth/email/contact', form=form.data)
        flash('Your message has been submitted. Someone will contact you by email soon.', 'success')
        return redirect(url_for('web.index'))
    return render_template('contact.html', form=form)


########################################################################################################################
# favicon
########################################################################################################################
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


########################################################################################################################
# register blueprints
########################################################################################################################
app.register_blueprint(web)
app.register_blueprint(ajax)
