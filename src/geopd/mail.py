import os
from flask import render_template
from flask.ext.mail import Message
from geopd.app import mail, config


def send_email(to, subject, template_name, **context):
    sender = '"{0}" <{1}>'.format(config.get('www', 'app_name'), os.environ['MAIL_USERNAME'])
    subject = "[{0}] {1}".format(config.get('www', 'app_name'), subject)
    msg = Message(subject, sender=sender, recipients=[to])
    msg.body = render_template(template_name + '.txt', **context)
    msg.html = render_template(template_name + '.html', **context)
    mail.send(msg)