from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField


class UpdateSurveyForm(FlaskForm):
    complete = SubmitField('Complete Survey')
    update = SubmitField('Update Survey')


class PostForm(FlaskForm):
    title = StringField('Title')
    body = TextAreaField('Content ...')
    submit = SubmitField('Publish')
