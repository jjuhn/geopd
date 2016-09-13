from flask_wtf import Form
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField


class UpdateSurveyForm(Form):
    complete = SubmitField('Complete Survey')
    update = SubmitField('Update Survey')


class PostForm(Form):
    title = StringField('Title')
    body = TextAreaField('Content ...')
    submit = SubmitField('Publish')
