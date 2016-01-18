from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from ecs.users.models import UserProfile
from ecs.core.models import MedicalCategory, ExpeditedReviewCategory
from ecs.core.forms.fields import MultiAutocompleteWidget, AutocompleteWidget, DateTimeField
from ecs.utils.formutils import TranslatedModelForm, require_fields
from ecs.users.utils import get_user, create_user
from ecs.users.models import LOGIN_HISTORY_TYPES
from ecs.meetings.models import AssignedMedicalCategory


class EmailLoginForm(forms.Form):
    # Note: This has to be called "username", so we can use the django login view
    username = forms.EmailField(label=_('Email'), max_length=User._meta.get_field('email').max_length)
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        return super(EmailLoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_('Please enter a correct email and password. Note that the password is case-sensitive.'))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_('This account is inactive.'))
        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class RegistrationForm(forms.Form):
    gender = forms.ChoiceField(label=_('gender'), choices=(('f', _('Ms')), ('m', _('Mr'))))
    first_name = forms.CharField(label=_('First name'))
    last_name = forms.CharField(label=_('Last name'))
    email = forms.EmailField(label=_('email'))


class ActivationForm(forms.Form):
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput, min_length=8)
    password_again = forms.CharField(label=_('Password (again)'), widget=forms.PasswordInput, min_length=8)
    
    def clean_password_again(self):
        password = self.cleaned_data.get("password", "")
        if password != self.cleaned_data["password_again"]:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password

class RequestPasswordResetForm(forms.Form):
    email = forms.EmailField()

class ProfileForm(TranslatedModelForm):
    first_name = forms.CharField(max_length=User._meta.get_field('first_name').max_length, required=False)
    last_name = forms.CharField(max_length=User._meta.get_field('last_name').max_length)
    forward_messages_after_minutes = forms.ChoiceField(choices=(
        (0, _('Never')),
        (5, _('after 5 minutes')),
        (360, _('after {0} hours').format(6)),
        (1440, _('after {0} hours').format(24)),
        (4320, _('after {0} hours').format(72)),
    ), initial=0)

    def __init__(self, *args, **kwargs):
        rval = super(ProfileForm, self).__init__(*args, **kwargs)

        if self.instance:
            self.fields['forward_messages_after_minutes'].initial = self.instance.forward_messages_after_minutes
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

        return rval

    def save(self, *args, **kwargs):
        instance = super(ProfileForm, self).save(*args, **kwargs)

        forward_messages_minutes = self.cleaned_data.get('forward_messages_after_minutes', 0)
        instance.forward_messages_after_minutes = int(forward_messages_minutes)
        instance.save()

        instance.user.first_name = self.cleaned_data['first_name']
        instance.user.last_name = self.cleaned_data['last_name']
        instance.user.save()

        return instance

    class Meta:
        model = UserProfile
        fields = ('gender', 'title', 'first_name', 'last_name', 'organisation', 'jobtitle',
            'address1', 'address2', 'zip_code', 'city', 'phone', 'fax', 'iban', 'swift_bic',
            'social_security_number', 'forward_messages_after_minutes',
        )
        labels = {
            'gender': _('Gender'),
            'title': _('Title'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'organisation': _('Organisation'),
            'jobtitle': _('Job Title'),
            'swift_bic': _('SWIFT-BIC'),
            'iban': _('IBAN'),
            'address1': _('Address/Home Address if external reviewer'),
            'address2': _('Additional Address Information'),
            'zip_code': _('ZIP-Code'),
            'city': _('City'),
            'phone': _('Phone'),
            'fax': _('Fax'),
            'social_security_number': _('Social Security Number'),
            'forward_messages_after_minutes': _('Forwarding of unread messages'),
        }


class AdministrationFilterForm(forms.Form):
    activity = forms.ChoiceField(required=False, choices=(
        ('both', _('Both')),
        ('active', _('active')),
        ('inactive', _('inactive')),
    ))
    groups = forms.ModelMultipleChoiceField(
        required=False, queryset=Group.objects.all(),
        widget=MultiAutocompleteWidget('groups')
    )
    medical_categories = forms.ModelMultipleChoiceField(
        required=False, queryset=MedicalCategory.objects.all(),
        widget=MultiAutocompleteWidget('medical-categories')
    )
    page = forms.CharField(required=False, widget=forms.HiddenInput())
    keyword = forms.CharField(required=False)

class UserDetailsForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=UserProfile._meta.get_field('gender').choices, label=_('gender'))
    title = forms.CharField(max_length=UserProfile._meta.get_field('title').max_length, required=False, label=_('title'))
    medical_categories = forms.ModelMultipleChoiceField(
        required=False, queryset=MedicalCategory.objects.all(),
        label=_('Board Member Categories'),
        widget=MultiAutocompleteWidget('medical-categories')
    )
    expedited_review_categories = forms.ModelMultipleChoiceField(
        required=False, queryset=ExpeditedReviewCategory.objects.all(),
        label=_('Expedited Categories'),
        widget=MultiAutocompleteWidget('expedited-review-categories')
    )
    is_internal = forms.BooleanField(required=False, label=_('Internal'))
    is_help_writer = forms.BooleanField(required=False, label=_('Help writer'))

    class Meta:
        model = User
        fields = (
            'gender', 'title', 'first_name', 'last_name', 'groups',
            'medical_categories', 'expedited_review_categories', 'is_internal',
            'is_help_writer',
        )
        widgets = {
            'groups': MultiAutocompleteWidget('groups'),
        }

    def __init__(self, *args, **kwargs):
        super(UserDetailsForm, self).__init__(*args, **kwargs)
        profile = self.instance.profile
        self.fields['gender'].initial = profile.gender
        self.fields['title'].initial = profile.title
        self.fields['medical_categories'].initial = [x.pk for x in self.instance.medical_categories.all()]
        self.fields['expedited_review_categories'].initial = [x.pk for x in self.instance.expedited_review_categories.all()]
        self.fields['is_internal'].initial = profile.is_internal
        self.fields['is_help_writer'].initial = profile.is_help_writer

    def clean_groups(self):
        groups = self.cleaned_data.get('groups', [])
        amcs = AssignedMedicalCategory.objects.filter(board_member=self.instance, meeting__ended__isnull=True)
        if amcs.exists() and not 'EC-Board Member' in [g.name for g in groups]:
            raise forms.ValidationError(_('{0} is a specialist in following meetings: {1}').format(self.instance, ', '.join(amc.meeting.title for amc in amcs)))
        return groups

    def save(self, *args, **kwargs):
        user = super(UserDetailsForm, self).save(*args, **kwargs)
        user.medical_categories = self.cleaned_data.get('medical_categories', ())
        user.expedited_review_categories = self.cleaned_data.get('expedited_review_categories', ())
        user.save()
        profile = user.profile
        profile.gender = self.cleaned_data['gender']
        profile.title = self.cleaned_data['title']
        profile.external_review = user.groups.filter(name='External Reviewer').exists()
        profile.is_board_member = user.groups.filter(name='EC-Board Member').exists()
        profile.is_executive_board_member = user.groups.filter(name='EC-Executive Board Group').exists()
        profile.is_thesis_reviewer = user.groups.filter(name='EC-Thesis Review Group').exists()
        profile.is_insurance_reviewer = user.groups.filter(name='EC-Insurance Reviewer').exists()
        profile.is_expedited_reviewer = user.groups.filter(name='Expedited Review Group').exists()
        profile.is_resident_member = user.groups.filter(name='Resident Board Member Group').exists()
        for k in ('is_internal', 'is_help_writer'):
            setattr(profile, k, self.cleaned_data.get(k, False))
        profile.save()
        return user

class InvitationForm(forms.Form):
    email = forms.EmailField(label=_('email'))
    gender = forms.ChoiceField(choices=UserProfile._meta.get_field('gender').choices, label=_('gender'))
    title = forms.CharField(max_length=UserProfile._meta.get_field('title').max_length, required=False, label=_('title'))
    first_name = forms.CharField(max_length=User._meta.get_field('first_name').max_length, label=_('First name'))
    last_name = forms.CharField(max_length=User._meta.get_field('last_name').max_length, label=_('Last name'))
    groups = forms.ModelMultipleChoiceField(
        required=False, queryset=Group.objects.all(), label=_('Groups'),
        widget=MultiAutocompleteWidget('groups')
    )
    medical_categories = forms.ModelMultipleChoiceField(
        required=False, queryset=MedicalCategory.objects.all(),
        label=_('Board Member Categories'),
        widget=MultiAutocompleteWidget('medical-categories')
    )
    expedited_review_categories = forms.ModelMultipleChoiceField(
        required=False, queryset=ExpeditedReviewCategory.objects.all(),
        label=_('Expedited Categories'),
        widget=MultiAutocompleteWidget('expedited-review-categories')
    )
    is_internal = forms.BooleanField(required=False, label=_('Internal'))
    is_help_writer = forms.BooleanField(required=False, label=_('Help writer'))
    invitation_text = forms.CharField(widget=forms.Textarea(), label=_('Invitation Text'))

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = get_user(email)
            raise forms.ValidationError(_('There is already a user with this email address.'))
        except User.DoesNotExist:
            pass
        return email

    def save(self):
        user = create_user(self.cleaned_data['email'], first_name=self.cleaned_data['first_name'], last_name=self.cleaned_data['last_name'])
        user.groups = self.cleaned_data.get('groups', [])
        user.medical_categories = self.cleaned_data.get('medical_categories', [])
        user.expedited_review_categories = self.cleaned_data.get('expedited_review_categories', [])
        user.save()
        profile = user.profile
        profile.gender = self.cleaned_data['gender']
        profile.title = self.cleaned_data['title']
        profile.is_board_member = user.groups.filter(name='EC-Board Member').exists()
        profile.is_executive_board_member = user.groups.filter(name='EC-Executive Board Group').exists()
        profile.is_thesis_reviewer = user.groups.filter(name='EC-Thesis Review Group').exists()
        profile.is_insurance_reviewer = user.groups.filter(name='EC-Insurance Reviewer').exists()
        profile.is_expedited_reviewer = user.groups.filter(name='Expedited Review Group').exists()
        profile.is_resident_member = user.groups.filter(name='Resident Board Member Group').exists()
        profile.forward_messages_after_minutes = 5
        for k in ('is_internal', 'is_help_writer'):
            setattr(profile, k, self.cleaned_data.get(k, False))
        profile.save()
        return user

class IndispositionForm(forms.ModelForm):
    is_indisposed = forms.BooleanField(required=False, label=_('is_indisposed'))
    communication_proxy = forms.ModelChoiceField(
        queryset=User.objects.all().select_related('profile'), required=False,
        label=_('communication_proxy'),
        widget=AutocompleteWidget('users')
    )

    class Meta:
        model = UserProfile
        fields = ('is_indisposed', 'communication_proxy')

    def clean(self):
        cd = super(IndispositionForm, self).clean()

        if cd.get('is_indisposed', False):
            require_fields(self, ('communication_proxy',))

        return cd

class SetPasswordForm(DjangoSetPasswordForm):
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput, min_length=8)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput, min_length=8)

class PasswordChangeForm(DjangoPasswordChangeForm):
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput, min_length=8)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput, min_length=8)


class LoginHistoryFilterForm(forms.Form):
    type = forms.ChoiceField(choices=(('', '---'),) + LOGIN_HISTORY_TYPES, required=False)
    start = DateTimeField()
    end = DateTimeField()
    page = forms.IntegerField(initial=1, widget=forms.HiddenInput())

    def clean(self):
        super(LoginHistoryFilterForm, self).clean()
        start = self.cleaned_data.get('start')
        end = self.cleaned_data.get('end')
        if start and end and start >= end:
            raise forms.ValidationError(_('Start must be before end.'))
        return self.cleaned_data
