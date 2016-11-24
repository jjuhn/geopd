from flask import render_template
from flask_mail import Message

from ..core import app
from ..core import mail


SENDER = '"{0}" <{1}>'.format(app.config['APP_NAME'], app.config['MAIL_USERNAME'])
PREFIX = app.config['APP_NAME']


def send_email(to, subject, template_name, **context):
    subject = "[{0}] {1}".format(PREFIX, subject)
    msg = Message(subject, sender=SENDER, recipients=[to])
    msg.body = render_template(template_name + '.txt', **context)
    msg.html = render_template(template_name + '.html', **context)
    if mail:
        mail.send(msg)
