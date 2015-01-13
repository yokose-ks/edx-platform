"""
Utility functions for validating forms
"""
import datetime
from pytz import UTC

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.hashers import UNUSABLE_PASSWORD
from django.contrib.auth.tokens import default_token_generator

from django.utils.http import int_to_base36
from django.template import loader

from django.conf import settings
from microsite_configuration import microsite

from django.utils.translation import ugettext_lazy as _

from student.models import UserStanding

class PasswordResetFormNoActive(PasswordResetForm):
    def clean_email(self):
        """
        This is a literal copy from Django 1.4.5's django.contrib.auth.forms.PasswordResetForm
        Except removing the requirement of active users
        Validates that a user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        #The line below contains the only change, removing is_active=True
        self.users_cache = User.objects.filter(email__iexact=email)
        if not len(self.users_cache):
            raise forms.ValidationError(self.error_messages['unknown'])
        if any((user.password == UNUSABLE_PASSWORD)
               for user in self.users_cache):
            raise forms.ValidationError(self.error_messages['unusable'])
        return email

    def save(
            self,
            domain_override=None,
            subject_template_name='registration/password_reset_subject.txt',
            email_template_name='registration/password_reset_email.html',
            use_https=False,
            token_generator=default_token_generator,
            from_email=settings.DEFAULT_FROM_EMAIL,
            request=None
    ):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        # This import is here because we are copying and modifying the .save from Django 1.4.5's
        # django.contrib.auth.forms.PasswordResetForm directly, which has this import in this place.
        from django.core.mail import send_mail
        for user in self.users_cache:
            if not domain_override:
                site_name = microsite.get_value(
                    'SITE_NAME',
                    settings.SITE_NAME
                )
            else:
                site_name = domain_override
            context = {
                'email': user.email,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                'platform_name': microsite.get_value('platform_name', settings.PLATFORM_NAME)
            }
            subject = loader.render_to_string(subject_template_name, context)
            # Email subject *must not* contain newlines
            subject = subject.replace('\n', '')
            email = loader.render_to_string(email_template_name, context)
            send_mail(subject, email, from_email, [user.email])

class SetPasswordFormErrorMessages(SetPasswordForm):
    """
    A form to enter new password.
    The only change from django.contrib.auth.forms.SetResignReasonForm is error_messages.
    """
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput,
        error_messages={'required': _('New password is required.')},
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        widget=forms.PasswordInput,
        error_messages={'required': _('New password confirmation is required.')},
    )


class ResignForm(PasswordResetFormNoActive):
    """
    A form to send an e-mail for resignation.
    """
    def save(self, domain_override=None,
             subject_template_name='registration/resign_subject.txt',
             email_template_name='registration/resign_email.html',
             use_https=False, token_generator=None,
             from_email=None, request=None):
        """
        Generates a one-use only link for resignation and sends to the user.
        """
        super(ResignForm, self).save(
            domain_override=domain_override,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            use_https=use_https,
            from_email=from_email,
            request=request,
        )


class SetResignReasonForm(forms.Form):
    """
    A form that lets a user confirm to resign with a reason.
    """
    resign_reason = forms.CharField(
        label=_('Resign reason'),
        widget=forms.Textarea,
        required=True,
        max_length=1000,
        error_messages={'required': _('Resign reason is required.')},
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetResignReasonForm, self).__init__(*args, **kwargs)

    def save(self):
        """
        Disables the user's account and stores a resign reason into db.
        """
        # NOTE(yokose): force activate an unactivated user
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save()

        user_account, _success = UserStanding.objects.get_or_create(
            user=self.user, defaults={'changed_by': self.user},
        )
        user_account.account_status = UserStanding.ACCOUNT_DISABLED
        user_account.changed_by = self.user
        user_account.standing_last_changed_at = datetime.datetime.now(UTC)
        # NOTE(yokose): store resign_reason into db
        user_account.resign_reason = self.cleaned_data["resign_reason"]
        user_account.save()
