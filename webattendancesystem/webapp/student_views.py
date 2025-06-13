# student_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import Student, Schedule, AttendanceSession, Attendance
from django.db.models import Q, Count
from django.contrib.auth.hashers import make_password

def is_schedule_available(schedule):
    """Helper function to check if schedule is within time range"""
    now = timezone.localtime()
    current_time = now.time()
    
    # Convert schedule times to minutes for comparison
    current_minutes = current_time.hour * 60 + current_time.minute
    start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
    end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
    
    # Allow attendance 15 minutes before start time until end time
    return (start_minutes - 15) <= current_minutes <= end_minutes

def is_session_available(schedule):
    """Helper function to check if schedule is within time range and has active session"""
    now = timezone.localtime()
    current_time = now.time()
    
    # Convert schedule times to minutes for comparison
    current_minutes = current_time.hour * 60 + current_time.minute
    start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
    end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
    
    # Check if within time range
    is_time_available = (start_minutes - 15) <= current_minutes <= end_minutes
    
    # Check for active session
    active_session = AttendanceSession.objects.filter(
        schedule=schedule,
        date=now.date(),
        status='ongoing'
    ).first()
    
    return is_time_available, active_session

def get_active_sessions(student, schedule):
    """Helper function to get active sessions for a student's schedule"""
    today = timezone.localtime()
    
    # Get ongoing session for this schedule today
    active_session = AttendanceSession.objects.filter(
        schedule=schedule,
        date=today.date(),
        status='ongoing'  # Only get active sessions
    ).first()

    if active_session:
        # Check if student already marked attendance
        has_attendance = Attendance.objects.filter(
            session=active_session,
            student=student
        ).exists()
        
        return active_session, has_attendance
        
    return None, False

@login_required
def student_dashboard(request):
    if request.user.user_type != 'student':
        return redirect('login')
        
    student = get_object_or_404(Student, user=request.user)
    today = timezone.localtime()
    current_day = today.strftime('%A').lower()
    
    # Get today's schedules
    schedules = Schedule.objects.filter(
        section=student.section,
        day_of_week=current_day
    ).select_related(
        'subject', 
        'teacher'
    ).order_by('start_time')

    for schedule in schedules:
        schedule.is_time_available = is_schedule_available(schedule)
        
        existing_session = AttendanceSession.objects.filter(
            schedule=schedule,
            date=today.date()
        ).first()
        
        if existing_session and existing_session.status == 'ongoing':
            schedule.active_session = existing_session
            attendance = Attendance.objects.filter(
                session=existing_session,
                student=student
            ).first()
            
            if attendance:
                schedule.has_marked_attendance = True
                schedule.attendance_status = attendance.get_status_display()
                schedule.status_color = {
                    'present': 'success',
                    'late': 'warning',
                    'absent': 'danger',
                    'excused': 'info'
                }.get(attendance.status, 'secondary')
            else:
                schedule.has_marked_attendance = False
                schedule.status_color = 'warning'
                schedule.attendance_status = 'Session Active'
        else:
            schedule.active_session = None
            schedule.has_marked_attendance = False
            if schedule.is_time_available:
                schedule.status_color = 'info'
                schedule.attendance_status = 'Scheduled Started'
            else:
                schedule.status_color = 'secondary'
                schedule.attendance_status = 'Not Scheduled Started'

    # Monthly stats (keep existing code)
    start_date = today.replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    monthly_attendance = Attendance.objects.filter(
        student=student,
        session__date__range=[start_date, end_date]
    )
    
    attendance_stats = {
        'present_count': monthly_attendance.filter(status='present').count(),
        'late_count': monthly_attendance.filter(status='late').count(),
        'absent_count': monthly_attendance.filter(status='absent').count(),
    }
    
    total_sessions = monthly_attendance.count()
    if total_sessions > 0:
        attendance_stats['attendance_percentage'] = round(
            ((attendance_stats['present_count'] + attendance_stats['late_count']) / total_sessions) * 100
        )
    else:
        attendance_stats['attendance_percentage'] = 0

    # Recent attendance (keep existing code)
    recent_attendance = Attendance.objects.filter(
        student=student
    ).select_related(
        'session__schedule__subject'
    ).order_by('-session__date', '-marked_at')[:5]
    
    for attendance in recent_attendance:
        attendance.status_color = {
            'present': 'success',
            'late': 'warning',
            'absent': 'danger',
            'excused': 'info'
        }.get(attendance.status, 'secondary')

    context = {
        'student': student,
        'schedules': schedules,
        'attendance_stats': attendance_stats,
        'recent_attendance': recent_attendance
    }
    return render(request, 'webapp/student/dashboard.html', context)

@login_required
def student_schedule(request):
    if request.user.user_type != 'student':
        return redirect('login')
        
    student = get_object_or_404(Student, user=request.user)
    today = timezone.localtime()
    current_day = today.strftime('%A').lower()

    # Get active sessions (like teacher view)
    active_sessions = AttendanceSession.objects.filter(
        schedule__section=student.section,
        status='ongoing',
        date=today.date()
    ).count()

    # Get all schedules
    schedules = Schedule.objects.filter(
        section=student.section
    ).select_related(
        'subject', 
        'teacher'
    ).order_by('day_of_week', 'start_time')

    for schedule in schedules:
        # Check if it's today's schedule
        if schedule.day_of_week == current_day:
            schedule.is_time_available = is_schedule_available(schedule)
            
            # Get active session for today (like teacher view)
            existing_session = AttendanceSession.objects.filter(
                schedule=schedule,
                date=today.date()
            ).first()
            
            if existing_session and existing_session.status == 'ongoing':
                schedule.active_session = existing_session
                # Check if student has marked attendance
                attendance = Attendance.objects.filter(
                    session=existing_session,
                    student=student
                ).first()
                
                if attendance:
                    schedule.has_marked_attendance = True
                    schedule.attendance_status = attendance.get_status_display()
                    schedule.status_color = {
                        'present': 'success',
                        'late': 'warning',
                        'absent': 'danger',
                        'excused': 'info'
                    }.get(attendance.status, 'secondary')
                else:
                    schedule.has_marked_attendance = False
                    schedule.status_color = 'warning'
                    schedule.attendance_status = 'Session Active'
            else:
                schedule.active_session = None
                schedule.has_marked_attendance = False
                if schedule.is_time_available:
                    schedule.status_color = 'info'
                    schedule.attendance_status = 'Waiting to Start'
                else:
                    schedule.status_color = 'secondary'
                    schedule.attendance_status = 'Not Started'
        else:
            schedule.is_time_available = False
            schedule.active_session = None
            schedule.has_marked_attendance = False
            schedule.attendance_status = schedule.day_of_week.title()
            schedule.status_color = 'secondary'

    context = {
        'student': student,
        'schedules': schedules,
        'current_day': current_day
    }
    return render(request, 'webapp/student/schedule.html', context)

@login_required
def student_attendance_history(request):
    if request.user.user_type != 'student':
        return redirect('login')
        
    student = get_object_or_404(Student, user=request.user)
    
    # Get month filter
    today = timezone.localdate()
    month = request.GET.get('month', f"{today.year}-{today.month:02d}")
    try:
        year, month = map(int, month.split('-'))
        start_date = date(year, month, 1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    except ValueError:
        messages.error(request, 'Invalid date format')
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Get attendance records
    attendance_records = Attendance.objects.filter(
        student=student,
        session__date__range=[start_date, end_date]
    ).select_related(
        'session__schedule__subject',
        'session__schedule__teacher'
    ).order_by('-session__date', '-marked_at')

    # Calculate stats
    total_records = attendance_records.count()
    stats = {
        'present_count': attendance_records.filter(status='present').count(),
        'late_count': attendance_records.filter(status='late').count(),
        'absent_count': attendance_records.filter(status='absent').count(),
        'attendance_percentage': round(
            (attendance_records.filter(status__in=['present', 'late']).count() / total_records * 100)
            if total_records > 0 else 0
        )
    }

    # Generate month choices
    months = Attendance.objects.filter(
        student=student
    ).dates('session__date', 'month', order='DESC')

    context = {
        'student': student,
        'attendance_records': attendance_records,
        'stats': stats,
        'available_months': [{
            'value': d.strftime('%Y-%m'),
            'label': d.strftime('%B %Y')
        } for d in months],
        'current_month': month
    }
    return render(request, 'webapp/student/attendance_history.html', context)

@login_required
def mark_attendance(request, session_id):
    if request.user.user_type != 'student':
        return redirect('login')
        
    student = get_object_or_404(Student, user=request.user)
    session = get_object_or_404(AttendanceSession, id=session_id)

    # Verify student belongs to section and session is active
    if student.section != session.schedule.section:
        messages.error(request, 'You are not enrolled in this class.')
        return redirect('student_dashboard')

    if session.status != 'ongoing':
        messages.error(request, 'This attendance session is not active.')
        return redirect('student_dashboard')

    # Create or update attendance record as present
    attendance, created = Attendance.objects.get_or_create(
        session=session,
        student=student,
        defaults={
            'status': 'present',
            'marked_at': timezone.now(),
            'marked_by': request.user
        }
    )

    if not created:
        # Update existing record to present
        attendance.status = 'present'
        attendance.marked_at = timezone.now()
        attendance.save()

    messages.success(request, 'You have been marked present!')
    return redirect('student_dashboard')

@login_required
def student_profile(request):
    if request.user.user_type != 'student':
        return redirect('login')
        
    student = get_object_or_404(Student, user=request.user)
    
    if request.method == 'POST':
        # Update user information
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        
        # Handle password change
        password = request.POST.get('password')
        if password:
            if password == request.POST.get('password_confirm'):
                user.password = make_password(password)
            else:
                messages.error(request, 'Passwords do not match')
                return redirect('student_profile')
        
        # Update student information
        student.first_name = user.first_name
        student.last_name = user.last_name
        student.phone = request.POST.get('phone', '')
        student.guardian_name = request.POST.get('guardian_name', '')
        student.guardian_phone = request.POST.get('guardian_phone', '')
        
        # Save changes
        user.save()
        student.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect('student_profile')
    
    context = {
        'student': student,
        'user': request.user
    }
    return render(request, 'webapp/student/profile.html', context)