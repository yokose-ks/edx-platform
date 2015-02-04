"Tests for account creation"

import ddt
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.transaction import rollback
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
import mock

from user_api.models import UserPreference
from lang_pref import LANGUAGE_KEY

from xmodule.modulestore.tests.factories import CourseFactory
from course_global.tests.factories import CourseGlobalSettingFactory

from opaque_keys.edx.locations import SlashSeparatedCourseKey

import student

TEST_CS_URL = 'https://comments.service.test:123/'

@ddt.ddt
class TestCreateAccount(TestCase):
    "Tests for account creation"

    def setUp(self):
        self.username = "test_user"
        self.url = reverse("create_account")
        self.params = {
            "username": self.username,
            "email": "test@example.org",
            "password": "testpass",
            "name": "Test User",
            "honor_code": "true",
            "terms_of_service": "true",
        }
        self.course_1 = CourseFactory.create(display_name = "test course 1")
        self.course_2 = CourseFactory.create(display_name = "test course 2")

    @ddt.data("en", "eo")
    def test_default_lang_pref_saved(self, lang):
        with mock.patch("django.conf.settings.LANGUAGE_CODE", lang):
            response = self.client.post(self.url, self.params)
            self.assertEqual(response.status_code, 200)
            user = User.objects.get(username=self.username)
            self.assertEqual(UserPreference.get_preference(user, LANGUAGE_KEY), lang)

    @ddt.data("en", "eo")
    def test_header_lang_pref_saved(self, lang):
        response = self.client.post(self.url, self.params, HTTP_ACCEPT_LANGUAGE=lang)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        self.assertEqual(UserPreference.get_preference(user, LANGUAGE_KEY), lang)

    def test_no_global_course(self):
        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        self.assertEqual(0, student.models.CourseEnrollmentAllowed.objects.all().count())

    def test_exists_global_course(self):
        dummy_course_id = SlashSeparatedCourseKey('a', 'b', 'c')
        CourseGlobalSettingFactory.create(course_id = dummy_course_id)
        CourseGlobalSettingFactory.create(course_id = self.course_1.id)
        CourseGlobalSettingFactory.create(course_id = self.course_2.id)

        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        cea1 = student.models.CourseEnrollmentAllowed.objects.get(email = user.email, course_id = self.course_1.id)
        self.assertTrue(cea1.auto_enroll)
        cea2 = student.models.CourseEnrollmentAllowed.objects.get(email = user.email, course_id = self.course_2.id)
        self.assertTrue(cea2.auto_enroll)
        self.assertFalse(student.models.CourseEnrollmentAllowed.objects.filter(course_id = dummy_course_id))

@mock.patch.dict("student.models.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
@mock.patch("lms.lib.comment_client.User.base_url", TEST_CS_URL)
@mock.patch("lms.lib.comment_client.utils.requests.request", return_value=mock.Mock(status_code=200, text='{}'))
class TestCreateCommentsServiceUser(TransactionTestCase):

    def setUp(self):
        self.username = "test_user"
        self.url = reverse("create_account")
        self.params = {
            "username": self.username,
            "email": "test@example.org",
            "password": "testpass",
            "name": "Test User",
            "honor_code": "true",
            "terms_of_service": "true",
        }

    def test_cs_user_created(self, request):
        "If user account creation succeeds, we should create a comments service user"
        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(request.called)
        args, kwargs = request.call_args
        self.assertEqual(args[0], 'put')
        self.assertTrue(args[1].startswith(TEST_CS_URL))
        self.assertEqual(kwargs['data']['username'], self.params['username'])

    @mock.patch("student.models.Registration.register", side_effect=Exception)
    def test_cs_user_not_created(self, register, request):
        "If user account creation fails, we should not create a comments service user"
        try:
            response = self.client.post(self.url, self.params)
        except:
            pass
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username=self.username)
        self.assertTrue(register.called)
        self.assertFalse(request.called)
