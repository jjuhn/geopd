from flask.ext.wtf import Form, RecaptchaField
from wtforms import StringField, SubmitField, TextAreaField


class ContactForm(Form):
    name = StringField('Name')
    email = StringField('Email')
    subject = StringField('Subject')
    message = TextAreaField('Message')
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')
