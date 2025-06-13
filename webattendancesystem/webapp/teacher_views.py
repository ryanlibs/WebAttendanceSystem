# teacher_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from .models import Teacher, Schedule, AttendanceSession, Attendance, Student, Section, Subject
import uuid
from io import BytesIO
import xlsxwriter
from datetime import datetime, timedelta

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

@login_required
def teacher_dashboard(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    today = timezone.localtime()
    current_day = today.strftime('%A').lower()
    
    # Get today's schedules
    schedules = Schedule.objects.filter(
        teacher=teacher,
        day_of_week=current_day,
        section__in=teacher.sections.all(),  # Add section filter
        subject__in=teacher.subjects.all()   # Add subject filter
    ).select_related(
        'subject',
        'section'
    ).order_by('start_time')

    for schedule in schedules:
        # Check if within time range first
        schedule.is_time_available = is_schedule_available(schedule)
        
        # Check for existing session today
        existing_session = AttendanceSession.objects.filter(
            schedule=schedule,
            date=today.date()
        ).first()
        
        if existing_session and existing_session.status == 'ongoing':
            schedule.has_ongoing_session = True
            schedule.ongoing_session = existing_session
            schedule.can_take_attendance = True
        else:
            schedule.has_ongoing_session = False
            schedule.ongoing_session = None
            # Can only take attendance if within time range and no session exists
            schedule.can_take_attendance = schedule.is_time_available and not existing_session

    context = {
        'teacher': teacher,
        'schedules': schedules,
        'total_students': Student.objects.filter(section__in=teacher.sections.all()).count(),
        'active_sessions': AttendanceSession.objects.filter(schedule__teacher=teacher, status='ongoing').count(),
        'sections': teacher.sections.all(),
        'recent_sessions': AttendanceSession.objects.filter(
            schedule__teacher=teacher
        ).select_related(
            'schedule__subject',
            'schedule__section'
        ).order_by('-date')[:5]
    }
    
    return render(request, 'webapp/teacher/dashboard.html', context)

@login_required
def teacher_schedule(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    today = timezone.localtime()
    current_day = today.strftime('%A').lower()
    
    schedules = Schedule.objects.filter(
        teacher=teacher,
        section__in=teacher.sections.all(),  # Add section filter 
        subject__in=teacher.subjects.all()   # Add subject filter
    ).select_related(
        'subject',
        'section'
    ).order_by('day_of_week', 'start_time')

    for schedule in schedules:
        # Only check availability if it's today
        if schedule.day_of_week == current_day:
            schedule.is_time_available = is_schedule_available(schedule)
            
            # Check for existing session today
            existing_session = AttendanceSession.objects.filter(
                schedule=schedule,
                date=today.date()
            ).first()
            
            if existing_session and existing_session.status == 'ongoing':
                schedule.has_ongoing_session = True
                schedule.ongoing_session = existing_session
                schedule.can_take_attendance = True
            else:
                schedule.has_ongoing_session = False
                schedule.ongoing_session = None
                # Can only take attendance if within time range and no session exists
                schedule.can_take_attendance = schedule.is_time_available and not existing_session
        else:
            # Not today's schedule
            schedule.is_time_available = False
            schedule.has_ongoing_session = False
            schedule.ongoing_session = None
            schedule.can_take_attendance = False

    context = {
        'schedules': schedules,
        'teacher': teacher,
        'current_day': current_day
    }
    
    return render(request, 'webapp/teacher/schedule.html', context)

# Add these helper methods
def calculate_attendance_stats(session):
    """Calculate attendance statistics for a session"""
    # Get distinct students from the section
    total_students = Student.objects.filter(section=session.schedule.section).distinct().count()
    
    # Get attendance counts for this specific session
    stats = {
        'present_count': Attendance.objects.filter(
            session=session, 
            status='present'
        ).distinct().count(),
        
        'absent_count': Attendance.objects.filter(
            session=session, 
            status='absent'
        ).distinct().count(),
        
        'late_count': Attendance.objects.filter(
            session=session, 
            status='late'
        ).distinct().count(),
        
        'excused_count': Attendance.objects.filter(
            session=session, 
            status='excused'
        ).distinct().count(),
    }
    
    # Calculate percentage using actual student count from section
    stats['attendance_percentage'] = round(
        ((stats['present_count'] + stats['late_count']) / total_students * 100) 
        if total_students > 0 else 0
    )
    
    return stats

@login_required
def attendance_session_list(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
    
    teacher = get_object_or_404(Teacher, user=request.user)
    today = timezone.now().date()
    
    # Get sessions with related data
    sessions = AttendanceSession.objects.filter(
        schedule__teacher=teacher
    ).select_related(
        'schedule__subject', 
        'schedule__section'
    ).order_by('-date', '-started_at')

    # Calculate stats for each session
    for session in sessions:
        stats = calculate_attendance_stats(session)
        session.attendance_percentage = stats['attendance_percentage']
        session.status_color = {
            'ongoing': 'success',
            'ended': 'secondary',
            'cancelled': 'danger'
        }.get(session.status, 'secondary')

    # Calculate overall stats
    total_sessions = sessions.count()
    active_sessions = sessions.filter(status='ongoing').count()
    today_sessions = sessions.filter(date=today).count()
    
    # Calculate average attendance
    all_attendance = Attendance.objects.filter(
        session__in=sessions, 
        status__in=['present', 'late']
    ).count()
    total_possible = Student.objects.filter(
        section__in=teacher.sections.all()
    ).count() * total_sessions

    average_attendance = round(
        (all_attendance / total_possible * 100) 
        if total_possible > 0 else 0
    )

    context = {
        'sessions': sessions,
        'active_sessions': active_sessions,
        'today_sessions': today_sessions,
        'total_sessions': total_sessions,
        'average_attendance': average_attendance
    }
    
    return render(request, 'webapp/teacher/attendance_session_list.html', context)

@login_required
def start_attendance_session(request, schedule_id):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher)
    today = timezone.now().date()
    
    # Check if session already exists
    existing_session = AttendanceSession.objects.filter(
        schedule=schedule,
        date=today,
        status='ongoing'
    ).first()
    
    if existing_session:
        return redirect('take_attendance', session_id=existing_session.id)
    
    # Create new session
    session = AttendanceSession.objects.create(
        id=str(uuid.uuid4()),
        schedule=schedule,
        date=today,
        status='ongoing'
    )
    
    messages.success(request, 'Attendance session started successfully')
    return redirect('take_attendance', session_id=session.id)

@login_required
def take_attendance(request, session_id):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    session = get_object_or_404(
        AttendanceSession, 
        id=session_id, 
        schedule__teacher=teacher
    )
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('status_'):
                attendance_id = key.replace('status_', '')
                try:
                    attendance = Attendance.objects.get(id=attendance_id)
                    attendance.status = value
                    attendance.marked_by = request.user
                    attendance.save()
                except Attendance.DoesNotExist:
                    continue
        
        messages.success(request, 'Attendance updated successfully')
        if 'save_and_continue' not in request.POST:
            return redirect('attendance_session_list')
    
    # Get or create attendance records for all students
    students = Student.objects.filter(section=session.schedule.section)
    attendances = []
    
    for student in students:
        attendance, created = Attendance.objects.get_or_create(
            session=session,
            student=student,
            defaults={
                'status': 'absent',
                'marked_by': request.user
            }
        )
        attendances.append(attendance)

    stats = calculate_attendance_stats(session)
    
    context = {
        'session': session,
        'attendances': attendances,
        'stats': stats
    }
    
    return render(request, 'webapp/teacher/take_attendance.html', context)

@require_POST
def update_attendance_remarks(request, attendance_id):
    if request.user.user_type != 'teacher':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    attendance = get_object_or_404(Attendance, id=attendance_id)
    remarks = request.POST.get('remarks', '')
    attendance.remarks = remarks
    attendance.save()
    
    return JsonResponse({'success': True})

@login_required
def end_session(request, session_id):  # Remove @require_POST since we're using GET
    if request.user.user_type != 'teacher':
        messages.error(request, 'Unauthorized access')
        return redirect('attendance_session_list')
    
    try:
        teacher = get_object_or_404(Teacher, user=request.user)
        session = get_object_or_404(AttendanceSession, id=session_id)
        
        # Verify this session belongs to the teacher
        if session.schedule.teacher != teacher:
            messages.error(request, 'This session does not belong to you')
            return redirect('attendance_session_list')
        
        # Only end ongoing sessions
        if session.status != 'ongoing':
            messages.error(request, 'This session is not ongoing')
            return redirect('attendance_session_list')
        
        # End the session
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save()
        
        messages.success(request, 'Session ended successfully')
        
    except Exception as e:
        messages.error(request, f'Error ending session: {str(e)}')
    
    return redirect('attendance_session_list')

@login_required 
def attendance_reports(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    
    # Get filter parameters
    section_id = request.GET.get('section')
    subject_id = request.GET.get('subject')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base query for sessions
    sessions = AttendanceSession.objects.filter(
        schedule__teacher=teacher
    ).select_related(
        'schedule__subject',
        'schedule__section'
    )

    # Apply filters
    if section_id:
        sessions = sessions.filter(schedule__section_id=section_id)
    if subject_id:
        sessions = sessions.filter(schedule__subject_id=subject_id)
    if start_date:
        sessions = sessions.filter(date__gte=start_date)
    if end_date:
        sessions = sessions.filter(date__lte=end_date)

    # Calculate totals for stats cards
    total_sessions = sessions.count()
    total_attendance_records = 0
    total_present = 0
    total_late = 0
    total_absent = 0
    
    # Calculate stats for each session
    sessions_list = []
    for session in sessions:
        # Get attendance counts for this session
        attendance_counts = Attendance.objects.filter(session=session).values('status').annotate(count=Count('status'))
        
        # Convert to dictionary for easier access
        counts = {item['status']: item['count'] for item in attendance_counts}
        
        # Get counts with defaults
        present_count = counts.get('present', 0)
        late_count = counts.get('late', 0)
        absent_count = counts.get('absent', 0)
        
        # Add counts to session object
        session.present_count = present_count
        session.late_count = late_count
        session.absent_count = absent_count
        
        # Calculate total students and attendance rate
        total_students = present_count + late_count + absent_count
        attendance_rate = ((present_count + late_count) / total_students * 100) if total_students > 0 else 0
        session.attendance_rate = round(attendance_rate)
        
        # Add to totals
        total_attendance_records += total_students
        total_present += present_count
        total_late += late_count
        total_absent += absent_count
        
        sessions_list.append(session)

    # Calculate overall statistics
    stats = {
        'total_sessions': total_sessions,
        'total_present': total_present,
        'total_late': total_late,
        'total_absent': total_absent,
        'attendance_rate': round((total_present / total_attendance_records * 100) if total_attendance_records > 0 else 0, 1),
        'late_percentage': round((total_late / total_attendance_records * 100) if total_attendance_records > 0 else 0, 1),
        'absent_percentage': round((total_absent / total_attendance_records * 100) if total_attendance_records > 0 else 0, 1)
    }

    context = {
        'sessions': sorted(sessions_list, key=lambda x: x.date, reverse=True),
        'teacher': teacher,
        'sections': teacher.sections.all(),
        'subjects': teacher.subjects.all(),
        'stats': stats,
        'selected_section': section_id,
        'selected_subject': subject_id,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return render(request, 'webapp/teacher/reports.html', context)

@login_required
def teacher_profile(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    
    if request.method == 'POST':
        try:
            # Update basic info
            teacher.first_name = request.POST.get('first_name')
            teacher.last_name = request.POST.get('last_name')
            teacher.phone = request.POST.get('phone')
            
            # Update email if changed
            new_email = request.POST.get('email')
            if new_email and new_email != teacher.user.email:
                teacher.user.email = new_email
                teacher.user.username = new_email
                teacher.user.save()
            
            # Update password if provided
            new_password = request.POST.get('password')
            if new_password:
                teacher.user.set_password(new_password)
                teacher.user.save()
            
            teacher.save()
            messages.success(request, 'Profile updated successfully')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            
    context = {
        'teacher': teacher,
        'subjects': teacher.subjects.all(),
        'sections': teacher.sections.all()
    }
    return render(request, 'webapp/teacher/profile.html', context)

@login_required
def export_attendance_excel(request):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    
    # Get filter parameters
    section_id = request.GET.get('section')
    subject_id = request.GET.get('subject')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Create Excel file with remove_timezone option
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'remove_timezone': True})
    
    # Add formatting
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#f4f4f4',
        'border': 1,
        'align': 'center'
    })
    
    date_format = workbook.add_format({
        'num_format': 'yyyy-mm-dd',
        'align': 'center'
    })
    time_format = workbook.add_format({
        'num_format': 'hh:mm AM/PM',
        'align': 'center'
    })
    percent_format = workbook.add_format({
        'num_format': '0.0%',
        'align': 'center'
    })
    center_format = workbook.add_format({
        'align': 'center'
    })
    
    # Create worksheets
    summary = workbook.add_worksheet('Summary')
    details = workbook.add_worksheet('Session Details')
    student_details = workbook.add_worksheet('Student Records')

    # Add student records headers
    student_headers = [
        'Date',
        'Subject',
        'Section',
        'Student ID',
        'Student Name',
        'Status',
        'Time In',
        'Remarks'
    ]
    
    # Write student records headers
    for col, header in enumerate(student_headers):
        student_details.write(0, col, header, header_format)

    # Base query for sessions
    sessions = AttendanceSession.objects.filter(
        schedule__teacher=teacher
    ).select_related(
        'schedule__subject',
        'schedule__section'
    )

    # Apply filters
    if section_id:
        sessions = sessions.filter(schedule__section_id=section_id)
    if subject_id:
        sessions = sessions.filter(schedule__subject_id=subject_id)
    if start_date:
        sessions = sessions.filter(date__gte=start_date)
    if end_date:
        sessions = sessions.filter(date__lte=end_date)

    # Calculate totals
    total_sessions = sessions.count()
    total_attendance_records = 0
    total_present = 0
    total_late = 0
    total_absent = 0
    
    # Write session details headers
    details_headers = [
        'Date',
        'Subject',
        'Section',
        'Total Students',
        'Present',
        'Late',
        'Absent',
        'Attendance Rate'
    ]
    for col, header in enumerate(details_headers):
        details.write(0, col, header, header_format)
    
    # Write session data
    row = 1
    for session in sessions:
        stats = calculate_attendance_stats(session)
        student_count = stats['present_count'] + stats['late_count'] + stats['absent_count']
        
        # Add to totals
        total_attendance_records += student_count
        total_present += stats['present_count']
        total_late += stats['late_count']
        total_absent += stats['absent_count']
        
        details.write(row, 0, session.date, date_format)
        details.write(row, 1, session.schedule.subject.name, center_format)
        details.write(row, 2, session.schedule.section.name, center_format)
        details.write(row, 3, student_count, center_format)
        details.write(row, 4, stats['present_count'], center_format)
        details.write(row, 5, stats['late_count'], center_format)
        details.write(row, 6, stats['absent_count'], center_format)
        details.write(row, 7, stats['attendance_percentage']/100, percent_format)
        row += 1

    # Write student attendance records
    student_row = 1
    for session in sessions:
        attendances = Attendance.objects.filter(
            session=session
        ).select_related(
            'student',
            'session__schedule__subject',
            'session__schedule__section'
        ).order_by(
            'student__last_name',
            'student__first_name'
        )

        for attendance in attendances:
            # Convert timezone-aware datetime to naive for Excel
            marked_time = timezone.localtime(attendance.marked_at).replace(tzinfo=None) if attendance.marked_at else None

            student_details.write(student_row, 0, session.date, date_format)
            student_details.write(student_row, 1, session.schedule.subject.name, center_format)
            student_details.write(student_row, 2, session.schedule.section.name, center_format)
            student_details.write(student_row, 3, attendance.student.student_id, center_format)
            student_details.write(student_row, 4, f"{attendance.student.last_name}, {attendance.student.first_name}", center_format)
            student_details.write(student_row, 5, attendance.get_status_display(), center_format)
            
            if marked_time:
                student_details.write(student_row, 6, marked_time, time_format)
            else:
                student_details.write(student_row, 6, "Not Recorded", center_format)
                
            student_details.write(student_row, 7, attendance.remarks or '', center_format)
            student_row += 1

    # Calculate overall rates
    attendance_rate = (total_present / total_attendance_records * 100) if total_attendance_records > 0 else 0
    late_rate = (total_late / total_attendance_records * 100) if total_attendance_records > 0 else 0
    absent_rate = (total_absent / total_attendance_records * 100) if total_attendance_records > 0 else 0

    # Write summary data
    summary.write_row(0, 0, ['Attendance Summary Report'], header_format)
    summary.write_row(2, 0, ['Period:', f"{start_date or 'All'} to {end_date or 'All'}"])
    summary.write_row(3, 0, ['Total Sessions:', total_sessions])
    summary.write_row(4, 0, ['Total Students:', total_attendance_records // total_sessions if total_sessions > 0 else 0])
    summary.write_row(5, 0, ['Present Count:', total_present])
    summary.write_row(6, 0, ['Late Count:', total_late])
    summary.write_row(7, 0, ['Absent Count:', total_absent])
    summary.write_row(8, 0, ['Attendance Rate:', attendance_rate/100], percent_format)
    summary.write_row(9, 0, ['Late Rate:', late_rate/100], percent_format)
    summary.write_row(10, 0, ['Absent Rate:', absent_rate/100], percent_format)
    
    # Set column widths
    details.set_column('A:A', 15)  # Date
    details.set_column('B:B', 30)  # Subject
    details.set_column('C:C', 20)  # Section
    details.set_column('D:G', 15)  # Counts
    details.set_column('H:H', 15)  # Rate
    
    summary.set_column('A:A', 20)
    summary.set_column('B:B', 30)
    
    # Set column widths for student records
    student_details.set_column('A:A', 15)  # Date
    student_details.set_column('B:B', 30)  # Subject
    student_details.set_column('C:C', 20)  # Section
    student_details.set_column('D:D', 15)  # Student ID
    student_details.set_column('E:E', 30)  # Student Name
    student_details.set_column('F:F', 15)  # Status
    student_details.set_column('G:G', 15)  # Time In
    student_details.set_column('H:H', 20)  # Remarks

    # Close workbook and create response
    workbook.close()
    output.seek(0)
    
    # Generate filename with timestamp
    filename = f"attendance_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@login_required
def session_details(request, session_id):
    if request.user.user_type != 'teacher':
        return redirect('login')
        
    teacher = get_object_or_404(Teacher, user=request.user)
    session = get_object_or_404(
        AttendanceSession, 
        id=session_id,
        schedule__teacher=teacher
    )
    
    # Get attendance records for this session
    attendances = Attendance.objects.filter(
        session=session
    ).select_related(
        'student'
    ).order_by(
        'student__last_name',
        'student__first_name'
    )

    # Calculate attendance statistics
    stats = calculate_attendance_stats(session)
    
    # Add status color for badges
    session.status_color = {
        'ongoing': 'success',
        'ended': 'secondary',
        'cancelled': 'danger'
    }.get(session.status, 'secondary')

    for attendance in attendances:
        attendance.status_color = {
            'present': 'success',
            'absent': 'danger',
            'late': 'warning',
            'excused': 'info'
        }.get(attendance.status, 'secondary')

    context = {
        'session': session,
        'attendances': attendances,
        'stats': stats
    }
    
    return render(request, 'webapp/teacher/session_details.html', context)