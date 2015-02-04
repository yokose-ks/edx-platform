from factory.django import DjangoModelFactory

from course_global.models import CourseGlobalSetting

class CourseGlobalSettingFactory(DjangoModelFactory):
    FACTORY_FOR = CourseGlobalSetting
