from flask_wtf import Form, RecaptchaField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField

from can.web.form import AddressMixin


class ContactForm(Form):
    name = StringField('Name')
    email = StringField('Email')
    subject = StringField('Subject')
    message = TextAreaField('Message')
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')


class UpdateSurveyForm(Form):
    complete = SubmitField('Complete Survey')
    update = SubmitField('Update Survey')


class ChangeAddressForm(Form, AddressMixin):
    submit = SubmitField('Save')


class PostForm(Form):
    title = StringField('Title')
    body = TextAreaField('Content ...')
    submit = SubmitField('Publish')
