from celery.decorators import task
from django.conf import settings
import logging

@task()
def queued_mail_send(message, To, From):
    from django.conf import settings
    from lamson.server import Relay
    if not hasattr(settings,'LAMSON_SEND_THROUGH_RECEIVER'): 
        settings.LAMSON_SEND_THROUGH_RECEIVER = False

    if settings.LAMSON_SEND_THROUGH_RECEIVER:
        relay = Relay(host=settings.LAMSON_RECEIVER_CONFIG['host'],
        port=settings.LAMSON_RECEIVER_CONFIG['port'])
    else:
        relay = Relay(host=settings.LAMSON_RELAY_CONFIG['host'],
        port=settings.LAMSON_RELAY_CONFIG['port'])

    print("".join(("queued mail deliver using ", str(relay), ", from ", From, ", to ", To, ", msg ", repr(message))))
    relay.deliver(message, To, From)
