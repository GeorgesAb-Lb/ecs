# ecs core views

"""
Views for ecs.
"""

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response

import settings

from core.models import Document, Notification, NotificationForm


## helpers

def prepare(request, pagename):
    t = loader.get_template(pagename)
    d = dict(MEDIA_URL=settings.MEDIA_URL)
    c = RequestContext(request, d)
    return (t, d, c)

def file_uuid(doc_file):
    """returns md5 digest of a given file as uuid"""
    import hashlib
    s = doc_file.read()  # TODO optimize for large files! check if correct for binary files (e.g. random bytes)
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()


## views

def demo(request):
    return render_to_response('demo-django.html')

def index(request):
    (t, d, c) = prepare(request, 'index.html')
    return HttpResponse(t.render(c))

def submission(request, id=''):
    (t, d, c) = prepare(request, 'submission.html')
    return HttpResponse(t.render(c))

# notification form

def notification_new1(request):
    # added to request:
    #   submission -> set of submission.id
    #   notificationtype -> [0..4]  
    if request.method == 'POST' and request.POST.has_key('notificationtype'):
        # process
        # TODO validate input
        if request.POST.has_key('submission'):
            submission = request.POST['submission']
        else:
            # no submission selected
            # TODO clarify where to check and what to do
            return HttpResponseRedirect(reverse('ecs.core.views.notification_new1'))            
        notificationtype = request.POST['notificationtype']
        # TODO seems to be GET only
        return HttpResponseRedirect(reverse('ecs.core.views.notification_new2'))
    else:
        # get last active submission
        id = 1  # TODO get last active submission from DB
        code = 'EK-343/2009'
        form_last_active_submission = {'id': id, 'code': code}
        # get this user's active submissions
        form_submissions = []  # TODO Submission.objects.filter(user = this_user)
        submissions = Submission.objects.all()
        for submission in submissions:
            id = submission.id
            code = 'EK-{0}/2010'.format(id)  # TODO get code from DB
            form_submissions.append({'id': id, 'code': code})
        # render template
        pagename = 'notification_new01.html'
        t = loader.get_template(pagename)
        d = dict(MEDIA_URL = settings.MEDIA_URL, 
                 last_active_submission = form_last_active_submission, 
                 submissions = form_submissions)
        c = RequestContext(request, d)
        return HttpResponse(t.render(c))

def notification_new2(request):
    # added to request:
    #   protocolnumber -> string
    #   statement -> string (html)
    if request.method == 'POST' and request.POST.has_key('protocolnumber'):
        # process
        # TODO validate input (or not)
        return HttpResponseRedirect(reverse('ecs.core.views.notification_new3'))
    else:
        # get protocol number
        protocolnumber = 'P12345'  # TODO get this from submission
        # get statement
        statement = ''  # TODO clarify 
        # render template
        pagename = 'notification_new02.html'
        t = loader.get_template(pagename)
        d = dict(MEDIA_URL = settings.MEDIA_URL,  # TODO put back prior request vars into request
                 protocolnumber = protocolnumber,
                 statement = statement)
        c = RequestContext(request, d)
        return HttpResponse(t.render(c))

def notification_new3(request):
    # added to request:
    #   doctype -> [0..8]
    #   description -> string
    #   versiondate -> date
    #   fileupload -> file
    if request.method == 'POST' and request.POST.has_key('doctype'):
        # process the form submission

        # TODO validate input (or not)

        #
        #  handle file upload
        #

        # store uploaded file (if supplied)
        if request.FILES['fileupload']:
            fileupload = request.FILES['fileupload']
            if fileupload.size == 0:
                return HttpResponse('Die Datei ' + fileupload.name + ' ist leer!')
            # gather DB document
            uuid = file_uuid(fileupload)
            uuid_revision = uuid   # TODO explain this field
            description = request.POST['description']  # TODO harmonize IDs Form, DB
            versiondate = request.POST['versiondate']
            document = Document(uuid_document = uuid, 
                                uuid_document_revision = uuid_revision,
                                version = description,
                                date = versiondate,
                                absent = False)
            # store the received file upload into the file storage
            fileupload.seek(0)  # rewind file because of prior uuid hashing
            dest = document.open('w')  # get file object from file storage
            s = fileupload.read()
            dest.write(s)
            dest.close()  # file storage done
            # store DB record
            document.save()

        # 
        #  handle notification
        #

        # gather

        notification = Notification(
            submission = None,
            #documents =
            answer = None,
            workflow = None)
        notification.save()

        # TODO determine from notificationtype
        yearly_report = False
        final_report = False
        amendment_report = True
        SAE_report = False
        SUSAR_report = False

        notification_form = NotificationForm(
            notification = notification,
            submission_form = None,
            investigator = None,
            #
            yearly_report = yearly_report,
            final_report = final_report,
            amendment_report = amendment_report,
            SAE_report = SAE_report,
            SUSAR_report = SUSAR_report,
            #
            date_of_vote = None,
            ek_number = 'EK1',
            #
            reason_for_not_started = None,
            recruited_subjects = None,
            finished_subjects = None,
            aborted_subjects = None,
            SAE_count = None,
            SUSAR_count = None,
            runs_till = None,
            finished_on = None,
            aborted_on = None,
            comments = 'kein Kommentar',
            extension_of_vote = False,
            signed_on = None)
        notification_form.save()
                             
        return HttpResponseRedirect(reverse('ecs.core.views.index'))
    else:
        # get existing docs
        form_docs = []
        for document in Document.objects.all():
            doctype = '(missing)'  # TODO this field seems missing
            form_docs.append({'uuid': document.uuid_document,
                              'description': document.version,
                              'versiondate': document.date,
                              'doctype': doctype})
        # render template
        pagename = 'notification_new03.html'
        t = loader.get_template(pagename)
        d = dict(MEDIA_URL = settings.MEDIA_URL,
                 docs = form_docs)
        c = RequestContext(request, d)
        return HttpResponse(t.render(c))


def create_new_notification(request):
    return HttpResponse("Hello World!")

