from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Section, Subject, Schedule, Attendance, Teacher, Student, TeacherSubject, AttendanceSession

# Customize the CustomUser admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type')
    list_filter = ('user_type', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_type')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'first_name', 'last_name', 'phone')
    search_fields = ('teacher_id', 'first_name', 'last_name')

class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'section')
    list_filter = ('section',)
    search_fields = ('student_id', 'first_name', 'last_name')

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'teacher', 'section', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'teacher', 'section')
    search_fields = ('subject__name', 'teacher__first_name', 'section__name')

class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'date', 'status', 'started_at', 'ended_at')
    list_filter = ('status', 'date')
    search_fields = ('schedule__subject__name', 'schedule__teacher__first_name')

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'marked_at')
    list_filter = ('status', 'marked_at')
    search_fields = ('student__first_name', 'session__schedule__subject__name')

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Teacher, TeacherAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(TeacherSubject)
admin.site.register(AttendanceSession, AttendanceSessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)
