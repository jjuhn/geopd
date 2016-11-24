from flask_wtf import RecaptchaField
from flask_wtf import FlaskForm
from wtforms import widgets
from wtforms import HiddenField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField
from wtforms import SelectMultipleField


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AddressMixin(object):
    location = StringField('Institution name or address')
    department = StringField('Department')
    website = StringField('Website')
    street = StringField('Street')
    city = StringField('City')
    region = StringField('Province/State')
    postal = StringField('Postal Code')
    country = StringField('Country')
    institution = StringField('Institution')
    lat = HiddenField()
    lng = HiddenField()


class ChangeAddressForm(FlaskForm, AddressMixin):
    submit = SubmitField('Save')


class ContactForm(FlaskForm):
    name = StringField('Name')
    email = StringField('Email')
    subject = StringField('Subject')
    message = TextAreaField('Message')
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')


class FeedbackForm(FlaskForm):
    subject = StringField('Subject')
    message = TextAreaField('Message')
    submit = SubmitField('Submit')

