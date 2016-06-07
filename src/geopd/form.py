from flask_wtf import Form, RecaptchaField
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import HiddenField
from wtforms import SubmitField


class AddressMixin(object):
    location = StringField('Institution')
    department = StringField('Department')
    website = StringField('Website')
    street = StringField('Street')
    city = StringField('City')
    region = StringField('Province/State')
    postal = StringField('Postal Code')
    country = StringField('Country')
    institution = HiddenField()
    lat = HiddenField()
    lng = HiddenField()


class ContactForm(Form):
    name = StringField('Name')
    email = StringField('Email')
    subject = StringField('Subject')
    message = TextAreaField('Message')
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')


class CompleteSurveyForm(Form):
    submit = SubmitField('Complete Survey')


class ChangeAddressForm(Form, AddressMixin):
    submit = SubmitField('Save')


class PostForm(Form):
    body = TextAreaField("What's on our mind?")
    submit = SubmitField('Post')
