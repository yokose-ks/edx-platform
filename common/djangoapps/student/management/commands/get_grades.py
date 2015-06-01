"""
Management command to generate a list of grades for
the perticipants of dc001 (written by sunk)
"""
from courseware import grades, courses
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand, CommandError
import os
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from student.models import CourseEnrollment, User
from certificates.models import CertificateStatuses, certificate_status_for_student
from optparse import make_option
from django.core.handlers.base import BaseHandler
import unicodecsv as csv


class RequestMock(RequestFactory):
    def request(self, **request):
        "Construct a generic request object."
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request


class Command(BaseCommand):

    help = """
    Generate a matrix of grades for dc001

    CSV will include the following:
      - username
      - email
      - computed grade

    Outputs grades to a csv file.

    Example:
      sudo -u www-data SERVICE_VARIANT=lms /opt/edx/bin/django-admin.py get_grade_dc001 \
        -o /tmp/20130813-6.00x.csv \
        --settings=lms.envs.aws --pythonpath=/opt/wwc/edx-platform
    """

    option_list = BaseCommand.option_list + (
        make_option('-c', '--course',
                    metavar='COURSE_ID',
                    dest='course',
                    default=False,
                    help='Course ID for grade distribution'),
        make_option('-o', '--output',
                    metavar='FILE',
                    dest='output',
                    default=False,
                    help='Filename for grade output'))


    def handle(self, *args, **options):
        if os.path.exists(options['output']):
            raise CommandError("File {0} already exists".format(
                options['output']))

        STATUS_INTERVAL = 50

        # ----------------generate course objects ----start----------------------------
        # courses for scoring
        target_course_list = [
            u"gacco/ga002/2014_05",
            u"gacco/ga008/2014_10",
            u"gacco/ga023/2015_02",
            ]
        # course for managing
        dcm_course_id = "gacco/ga006/2014_04"

        course_key_list = []
        # parse out the course into a coursekey
        for course_id in target_course_list:
            try:
                course_key = CourseKey.from_string(course_id)
            # if it's not a new-style course key, parse it from an old-style course key
            except InvalidKeyError:
                course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
            course_key_list.append(course_key)

        try:
            dcm_course_key = CourseKey.from_string(dcm_course_id)
        except InvalidKeyError:
            dcm_course_key = SlashSeparatedCourseKey.from_deprecated_string(dcm_course_id)
        # ----------------generate course objects ----end----------------------------


        # list of participants
        print "Fetching enrolled students for {0}".format(dcm_course_key)
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=dcm_course_key
        )

        total = enrolled_students.count()
        print "Total enrolled: {0}".format(total)
        rows = []

        # output the first row (header)
        rows.append(["email", "username"] + target_course_list + ["total"]) 


        print "Grading students"
        factory = RequestMock()
        request = factory.get('/')

        for count, student in enumerate(enrolled_students):
            count += 1
            if count % STATUS_INTERVAL == 0:
                print "{0}/{1} completed ".format(count, total)

            request.user = student
            row = [student.email, student.username]
            total_score = 0
            for course_key in course_key_list:
                course = courses.get_course_by_id(course_key)
                score = 0
                if(CourseEnrollment.is_enrolled(student, course_key)):
                    grade = grades.grade(student, request, course)
                    score = int(grade['percent']*100)
                    if(score >= 90.0):
                        score += 50
                    cert_status = certificate_status_for_student(student, course_key)['status']
                    if(cert_status == "downloadable"):
                        score += 50
                    score += 1
                    total_score += score

                row.append("{0}".format(score))
            row.append(total_score)
            rows.append(row)

        with open(options['output'], 'wb') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
