"""
Django admin page for course global models
"""
from django.contrib import admin
from course_global.models import CourseGlobalSetting

class CourseGlobalSettingAdmin(admin.ModelAdmin):
    pass

admin.site.register(CourseGlobalSetting, CourseGlobalSettingAdmin)
