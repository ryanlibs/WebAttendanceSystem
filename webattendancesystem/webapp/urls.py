# urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views, admin_views, teacher_views, student_views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard redirect
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    
    # Admin routes - CHANGE THIS SECTION
    path('admin-portal/', include([  # Changed from admin/ to admin-portal/
        path('dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
        path('teachers/', admin_views.teacher_list, name='teacher_list'),
        path('teachers/create/', admin_views.teacher_create, name='teacher_create'),
        path('teachers/<uuid:teacher_id>/update/', admin_views.teacher_edit, name='teacher_update'),
        path('teachers/<uuid:teacher_id>/delete/', admin_views.teacher_delete, name='teacher_delete'),
        path('students/', admin_views.student_list, name='student_list'),
        path('students/create/', admin_views.student_create, name='student_create'),
        path('students/<uuid:student_id>/update/', admin_views.student_edit, name='student_update'),
        path('students/<uuid:student_id>/delete/', admin_views.student_delete, name='student_delete'),
        path('schedules/', admin_views.schedule_list, name='schedule_list'),
        path('schedules/create/', admin_views.schedule_create, name='schedule_create'),
        path('schedules/<uuid:schedule_id>/edit/', admin_views.schedule_edit, name='schedule_edit'),
        path('schedules/<uuid:schedule_id>/delete/', admin_views.schedule_delete, name='schedule_delete'),
        path('sections/', admin_views.section_list, name='section_list'),
        path('sections/create/', admin_views.section_create, name='section_create'),
        path('sections/<uuid:section_id>/edit/', admin_views.section_edit, name='section_edit'),
        path('sections/<uuid:section_id>/delete/', admin_views.section_delete, name='section_delete'),
        path('subjects/', admin_views.subject_list, name='subject_list'),
        path('subjects/create/', admin_views.subject_create, name='subject_create'),
        path('subjects/<uuid:subject_id>/edit/', admin_views.subject_edit, name='subject_edit'),
        path('subjects/<uuid:subject_id>/delete/', admin_views.subject_delete, name='subject_delete'),
    ])),
    
    # Teacher routes
    path('teacher/', include([
        path('dashboard/', teacher_views.teacher_dashboard, name='teacher_dashboard'),
        path('schedule/', teacher_views.teacher_schedule, name='teacher_schedule'),
        path('attendance/sessions/', teacher_views.attendance_session_list, name='attendance_session_list'),
        path('attendance/reports/', teacher_views.attendance_reports, name='attendance_reports'),
        path('attendance/take/<str:session_id>/', teacher_views.take_attendance, name='take_attendance'),
        path('attendance/start/<str:schedule_id>/', teacher_views.start_attendance_session, name='start_attendance_session'),
        path('attendance/session/<str:session_id>/details/', teacher_views.session_details, name='session_details'),
        path('attendance/end/<str:session_id>/', teacher_views.end_session, name='end_session'),
        path('reports/export/', teacher_views.export_attendance_excel, name='export_attendance_excel'),
        path('profile/', teacher_views.teacher_profile, name='teacher_profile'),
    ])),
    
    # Student routes
    path('student/', include([
        path('dashboard/', student_views.student_dashboard, name='student_dashboard'),
        path('schedule/', student_views.student_schedule, name='student_schedule'),
        path('attendance/mark/<str:session_id>/', student_views.mark_attendance, name='mark_attendance'),
        path('attendance/history/', student_views.student_attendance_history, name='student_attendance_history'),
        path('profile/', student_views.student_profile, name='student_profile'),
    ])),
    
    # Add profile URL
    path('profile/', views.profile_view, name='profile'),
    
    # Teacher URLs
    path('teacher/attendance/take/<str:session_id>/', 
         teacher_views.take_attendance, 
         name='take_attendance'),
    path('teacher/attendance/sessions/',
         teacher_views.attendance_session_list,
         name='attendance_session_list'),
    path('teacher/attendance/<str:attendance_id>/remarks/',
         teacher_views.update_attendance_remarks,
         name='update_attendance_remarks'),
    path('teacher/session/<str:session_id>/end/', 
         teacher_views.end_session, 
         name='end_session'),
]