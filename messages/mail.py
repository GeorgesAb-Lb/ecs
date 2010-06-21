import os
from django.utils.encoding import force_unicode
from django.core.mail import EmailMessage, EmailMultiAlternatives
from time import gmtime, strftime

def lamson_send_mail(subject, message, from_email, recipient_list, fail_silently=False, message_html=None, **kwargs):
    from ecs.ecsmail.config.settings import relay
    from lamson.mail import MailResponse
    print 'LAMSON SEND MAIL'
    for recipient in recipient_list:
        mess = MailResponse(To=recipient, From=from_email, Subject=subject, Body=message, Html=message_html)
        mess['Date'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        relay.deliver(mess, To=recipient, From=from_email)

def django_send_html_mail(subject, message, from_email, recipient_list,
                   priority="medium", fail_silently=False, auth_user=None,
                   auth_password=None, message_html=None):
    
    print 'DJANGO SEND MAIL'
    subject = force_unicode(subject)
    message = force_unicode(message)
   
    bcc = None
    attachments = None
    headers = None

    email = EmailMultiAlternatives(subject=subject, body=message, from_email=from_email,
                to=recipient_list, bcc=bcc, attachments=attachments, headers=headers)
    
    if message_html:
        email.attach_alternative(message_html, "text/html")
    email.send()

if os.environ.get('LAMSON_LOADED'):
    send_mail = lamson_send_mail
else:
    send_mail = django_send_html_mail

