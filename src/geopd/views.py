from flask import Blueprint
from flask import render_template, abort, redirect, flash, escape
from flask.ext.login import login_required, current_user

from geopd.app import application, config
from geopd.orm.db import *
from geopd.forms import ContactForm
from geopd.mail import send_email

from sqlalchemy.orm import joinedload

web_blueprint = Blueprint('web', __name__)


########################################################################################################################
# About Us
########################################################################################################################
@web_blueprint.route('/about/')
def show_about():
    return render_template('about.html')


########################################################################################################################
# Annual Meetings
########################################################################################################################
@web_blueprint.route('/meetings/')
def show_meetings():
    meeting = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).first()
    return redirect(url_for('web.show_meeting', id=meeting.id))


@web_blueprint.route('/meetings/<int:id>')
def show_meeting(id):
    meeting = Meeting.query.get(id)
    if not meeting.program:
        abort(404)
    meetings = Meeting.query.filter(Meeting.program).order_by(Meeting.year.desc()).all()
    return render_template('meetings/index.html', meeting=meeting, meetings=meetings)


########################################################################################################################
# Projects
########################################################################################################################
@web_blueprint.route('/projects/')
def show_projects():
    return render_template('projects.html', projects=Project.query.all())


########################################################################################################################
# Publications
########################################################################################################################
@web_blueprint.route('/publications/')
def show_publications():
    publications = Publication.query.order_by(Publication.published_on.desc()).all()
    return render_template('publications.html', publications=publications)


########################################################################################################################
# Cores
########################################################################################################################
@web_blueprint.route('/cores/')
def show_cores():
    return render_template('cores/index.html', cores=Core.query.all())


########################################################################################################################
# Members
########################################################################################################################
@web_blueprint.route('/members/')
def show_members():
    members = User.query.options(joinedload('institution'))
    tpl = 'members/public.html' if current_user.is_anonymous else 'members/index.html'
    return render_template(tpl, members=members)


@web_blueprint.route('/members/<int:id>')
@login_required
def show_member(id):
    user = User.query.options(joinedload('info'),
                              joinedload('info', 'clinical'),
                              joinedload('info', 'epidemiologic'),
                              joinedload('info', 'biospecimen')).filter(User.id == id).one()
    return render_template('members/profile.html', member=user,
                           clinical=ClinicalInfo.query.all(),
                           epidemiologic=EpidemiologicInfo.query.all(),
                           biospecimen=BiospecimenInfo.query.all())


@web_blueprint.route('/members/<int:id>/info/', methods=['POST'])
@login_required
def update_member_info(id):

    if id != current_user.id:
        abort(403)  # unauthorized

    name = request.form['name']

    if name == 'clinical':
        obj = ClinicalInfo.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.info.clinical.remove(obj)
        else:
            if obj not in current_user.info.clinical:
                current_user.info.clinical.append(obj)

    elif name == 'epidemiologic':
        obj = EpidemiologicInfo.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.info.epidemiologic.remove(obj)
        else:
            if obj not in current_user.info.epidemiologic:
                current_user.info.epidemiologic.append(obj)

    elif name == 'biospecimen':
        obj = BiospecimenInfo.query.get(request.form['value'])
        if request.form['checked'] == 'no':
            current_user.info.biospecimen.remove(obj)
        else:
            if obj not in current_user.info.biospecimen:
                current_user.info.biospecimen.append(obj)

    elif name == 'ethical':
        current_user.info.ethical = False if request.form['value'] == 'no' else True

    elif name == 'ethical-explain':
        value = escape(request.form['value'])
        current_user.info.ethical_explain = value
        return value

    elif name == 'consent':
        current_user.info.consent = False if request.form['value'] == 'no' else True

    elif name == 'consent-explain':
        value = escape(request.form['value'])
        current_user.info.consent_explain = value
        return value

    elif name == 'sample':
        current_user.info.sample = False if request.form['value'] == 'no' else True

    elif name == 'interest':
        value = escape(request.form['value'])
        current_user.info.research_interests = value
        return value

    elif name == 'experience':
        value = escape(request.form['value'])
        current_user.info.research_experience = value
        return value

    else:
        abort(400)

    db.commit()

    return '', 204


########################################################################################################################
# Contact Us
########################################################################################################################
@web_blueprint.route('/contact/', methods=['GET', 'POST'])
def show_contact():
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    form = ContactForm()
    if form.validate_on_submit():
        send_email(config.get('mail', 'contact'), 'Contact Form', 'auth/email/contact', form=form.data)
        flash('Your message has been submitted. Someone will contact you by email soon.', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html', form=form)


########################################################################################################################
# register web blueprint
########################################################################################################################
application.register_blueprint(web_blueprint)
