# admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
import uuid
from .models import *
from .forms import *

User = get_user_model()

@login_required
def admin_dashboard(request):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    context = {
        'total_teachers': Teacher.objects.count(),
        'total_students': Student.objects.count(),
        'total_subjects': Subject.objects.count(),
        'total_sections': Section.objects.count(),
        'recent_attendance': Attendance.objects.select_related('student', 'session__schedule__subject').order_by('-marked_at')[:10]
    }
    return render(request, 'webapp/admin/dashboard.html', context)  # Updated template path

# Teacher Management
@login_required
def teacher_list(request):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        teachers = Teacher.objects.select_related('user').prefetch_related('sections', 'subjects').all().order_by('teacher_id')
        context = {
            'teachers': teachers,
            'sections': Section.objects.all(),
            'subjects': Subject.objects.all(),
        }
        return render(request, 'webapp/admin/teacher_list.html', context)
    except Exception as e:
        messages.error(request, f'Error loading teachers: {str(e)}')
        return redirect('admin_dashboard')

@login_required
def teacher_create(request):
    if request.user.user_type != 'admin':
        return redirect('login')

    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            teacher_id = request.POST.get('teacher_id')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone', '')

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('teacher_list')

            if Teacher.objects.filter(teacher_id=teacher_id).exists():
                messages.error(request, 'Teacher ID already exists')
                return redirect('teacher_list')

            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                user_type='teacher'
            )

            # Create teacher
            teacher = Teacher.objects.create(
                user=user,
                teacher_id=teacher_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )

            # Handle sections and subjects
            section_ids = request.POST.getlist('sections')
            subject_ids = request.POST.getlist('subjects')
            
            if section_ids:
                teacher.sections.set(section_ids)
            if subject_ids:
                teacher.subjects.set(subject_ids)

            messages.success(request, 'Teacher created successfully')
        except Exception as e:
            messages.error(request, f'Error creating teacher: {str(e)}')

    return redirect('teacher_list')

@login_required
def teacher_edit(request, teacher_id):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        teacher = get_object_or_404(Teacher, id=teacher_id)

        if request.method == 'POST':
            # Update teacher details
            teacher.teacher_id = request.POST.get('teacher_id')
            teacher.first_name = request.POST.get('first_name')
            teacher.last_name = request.POST.get('last_name')
            teacher.phone = request.POST.get('phone', '')

            # Update user email
            new_email = request.POST.get('email')
            if new_email != teacher.user.email:
                if User.objects.filter(email=new_email).exclude(id=teacher.user.id).exists():
                    messages.error(request, 'Email already exists')
                    return redirect('teacher_list')
                teacher.user.email = new_email
                teacher.user.username = new_email

            # Update password if provided
            new_password = request.POST.get('password')
            if new_password:
                teacher.user.set_password(new_password)

            # Update sections and subjects
            section_ids = request.POST.getlist('sections')
            subject_ids = request.POST.getlist('subjects')
            teacher.sections.set(section_ids)
            teacher.subjects.set(subject_ids)

            teacher.user.save()
            teacher.save()
            messages.success(request, 'Teacher updated successfully')
            
    except Exception as e:
        messages.error(request, f'Error updating teacher: {str(e)}')

    return redirect('teacher_list')

@login_required
def teacher_delete(request, teacher_id):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        teacher = get_object_or_404(Teacher, id=teacher_id)
        user = teacher.user
        teacher.delete()
        user.delete()
        messages.success(request, 'Teacher deleted successfully')
    except Exception as e:
        messages.error(request, f'Error deleting teacher: {str(e)}')

    return redirect('teacher_list')

# Student Management

@login_required
def student_list(request):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        # Add prefetch_related to load all related data
        students = Student.objects.select_related('user', 'section').all().order_by('student_id')
        context = {
            'students': students,
            'sections': Section.objects.all(),
        }
        return render(request, 'webapp/admin/student_list.html', context)
    except Exception as e:
        messages.error(request, f'Error loading students: {str(e)}')
        return redirect('admin_dashboard')
@login_required
def student_create(request):
    if request.user.user_type != 'admin':
        return redirect('login')

    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            student_id = request.POST.get('student_id')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            section_id = request.POST.get('section')
            phone = request.POST.get('phone', '')
            guardian_name = request.POST.get('guardian_name', '')
            guardian_phone = request.POST.get('guardian_phone', '')

            # Validate unique constraints
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('student_list')

            if Student.objects.filter(student_id=student_id).exists():
                messages.error(request, 'Student ID already exists')
                return redirect('student_list')

            # Create user
            user = User.objects.create_user(
                username=student_id,
                email=email,
                password=password,
                user_type='student'
            )

            # Create student
            Student.objects.create(
                user=user,
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                section_id=section_id,
                phone=phone,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone
            )

            messages.success(request, 'Student created successfully')
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')

    return redirect('student_list')

@login_required
def student_edit(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        student = get_object_or_404(Student, id=student_id)

        if request.method == 'POST':
            # Update student details
            student.student_id = request.POST.get('student_id')
            student.first_name = request.POST.get('first_name')
            student.last_name = request.POST.get('last_name')
            student.section_id = request.POST.get('section')
            student.phone = request.POST.get('phone', '')
            student.guardian_name = request.POST.get('guardian_name', '')
            student.guardian_phone = request.POST.get('guardian_phone', '')

            # Update user email
            new_email = request.POST.get('email')
            if new_email != student.user.email:
                if User.objects.filter(email=new_email).exclude(id=student.user.id).exists():
                    messages.error(request, 'Email already exists')
                    return redirect('student_list')
                student.user.email = new_email

            # Update password if provided
            new_password = request.POST.get('password')
            if new_password:
                student.user.set_password(new_password)

            student.user.save()
            student.save()
            messages.success(request, 'Student updated successfully')
            
    except Exception as e:
        messages.error(request, f'Error updating student: {str(e)}')

    return redirect('student_list')

@login_required
def student_delete(request, student_id):
    if request.user.user_type != 'admin':
        return redirect('login')

    try:
        student = get_object_or_404(Student, id=student_id)
        user = student.user
        student.delete()
        user.delete()
        messages.success(request, 'Student deleted successfully')
    except Exception as e:
        messages.error(request, f'Error deleting student: {str(e)}')

    return redirect('student_list')

# Schedule Management
@login_required
def schedule_list(request):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    schedules = Schedule.objects.select_related(
        'teacher', 
        'subject', 
        'section'
    ).order_by('day_of_week', 'start_time')
    
    # Get only valid teacher-subject-section combinations
    teachers = Teacher.objects.prefetch_related('subjects', 'sections').all()
    subjects = Subject.objects.all().order_by('name')
    sections = Section.objects.all().order_by('name')
    
    context = {
        'schedules': schedules,
        'teachers': teachers,
        'subjects': subjects,
        'sections': sections,
    }
    return render(request, 'webapp/admin/schedule_list.html', context)

@login_required 
def schedule_create(request):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        try:
            teacher_id = request.POST.get('teacher')
            subject_id = request.POST.get('subject')
            section_id = request.POST.get('section')
            day_of_week = request.POST.get('day_of_week')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            room = request.POST.get('room', '')
            
            # Validate teacher has access to subject and section
            teacher = Teacher.objects.get(id=teacher_id)
            if not (teacher.subjects.filter(id=subject_id).exists() and 
                   teacher.sections.filter(id=section_id).exists()):
                messages.error(request, 'Invalid teacher-subject-section combination')
                return redirect('schedule_list')
            
            # Check for schedule conflicts
            conflicts = Schedule.objects.filter(
                day_of_week=day_of_week,
                section_id=section_id
            ).filter(
                Q(start_time__lt=end_time, end_time__gt=start_time) |
                Q(start_time__exact=start_time) |
                Q(end_time__exact=end_time)
            )
            
            if conflicts.exists():
                messages.error(request, 'Schedule conflict detected')
                return redirect('schedule_list')
            
            Schedule.objects.create(
                teacher_id=teacher_id,
                subject_id=subject_id,
                section_id=section_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                room=room,
                is_active=True
            )
            
            messages.success(request, 'Schedule created successfully')
            
        except Exception as e:
            messages.error(request, f'Error creating schedule: {str(e)}')
            
    return redirect('schedule_list')

@login_required
def schedule_edit(request, schedule_id):
    if request.user.user_type != 'admin':
        return redirect('login')
        
    try:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        if request.method == 'POST':
            teacher_id = request.POST.get('teacher')
            subject_id = request.POST.get('subject')
            section_id = request.POST.get('section')
            day_of_week = request.POST.get('day_of_week')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            room = request.POST.get('room', '')
            
            # Validate teacher has access to subject and section
            teacher = Teacher.objects.get(id=teacher_id)
            if not (teacher.subjects.filter(id=subject_id).exists() and 
                   teacher.sections.filter(id=section_id).exists()):
                messages.error(request, 'Invalid teacher-subject-section combination')
                return redirect('schedule_list')
            
            # Check for schedule conflicts excluding current schedule
            conflicts = Schedule.objects.filter(
                day_of_week=day_of_week,
                section_id=section_id
            ).exclude(id=schedule_id).filter(
                Q(start_time__lt=end_time, end_time__gt=start_time) |
                Q(start_time__exact=start_time) |
                Q(end_time__exact=end_time)
            )
            
            if conflicts.exists():
                messages.error(request, 'Schedule conflict detected')
                return redirect('schedule_list')
            
            # Update schedule
            schedule.teacher_id = teacher_id
            schedule.subject_id = subject_id
            schedule.section_id = section_id
            schedule.day_of_week = day_of_week
            schedule.start_time = start_time
            schedule.end_time = end_time
            schedule.room = room
            schedule.save()
            
            messages.success(request, 'Schedule updated successfully')
            
    except Exception as e:
        messages.error(request, f'Error updating schedule: {str(e)}')
        
    return redirect('schedule_list')

@login_required
def schedule_delete(request, schedule_id):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    try:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        # Check if schedule has any active attendance sessions
        if AttendanceSession.objects.filter(schedule=schedule, status='ongoing').exists():
            messages.error(request, 'Cannot delete schedule with active attendance sessions')
            return redirect('schedule_list')
        
        # Delete the schedule
        schedule.delete()
        messages.success(request, 'Schedule deleted successfully')
        
    except Exception as e:
        messages.error(request, f'Error deleting schedule: {str(e)}')
        
    return redirect('schedule_list')

# Section Management
@login_required
def section_list(request):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    sections = Section.objects.annotate(
        student_count=Count('student'),
        teacher_count=Count('teacher', distinct=True)
    ).order_by('year_level', 'name')
    
    context = {
        'sections': sections,
    }
    return render(request, 'webapp/admin/section_list.html', context)  # Update template path

@login_required
def section_create(request):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        year_level = request.POST.get('year_level')
        
        if Section.objects.filter(name=name, year_level=year_level).exists():
            messages.error(request, 'Section with this name and year level already exists')
            return redirect('section_list')
        
        Section.objects.create(
            name=name,
            year_level=year_level
        )
        messages.success(request, 'Section created successfully')
        return redirect('section_list')
    
    return redirect('section_list')

@login_required
def section_edit(request, section_id):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        year_level = request.POST.get('year_level')
        
        # Check if another section exists with same name and year level
        if Section.objects.exclude(id=section_id).filter(name=name, year_level=year_level).exists():
            messages.error(request, 'Section with this name and year level already exists')
            return redirect('section_list')
        
        section.name = name
        section.year_level = year_level
        section.save()
        
        messages.success(request, 'Section updated successfully')
        return redirect('section_list')
    
    return redirect('section_list')

@login_required
def section_delete(request, section_id):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    section = get_object_or_404(Section, id=section_id)
    
    # Check if section has any students
    if section.student_set.exists():
        messages.error(request, 'Cannot delete section that has students')
        return redirect('section_list')
    
    section.delete()
    messages.success(request, 'Section deleted successfully')
    return redirect('section_list')

# Subject Management
@login_required
def subject_list(request):
    if request.user.user_type != 'admin':
        return redirect('login')
        
    subjects = Subject.objects.all().order_by('name')
    context = {
        'subjects': subjects
    }
    return render(request, 'webapp/admin/subject_list.html', context)

@login_required
def subject_create(request):
    if request.user.user_type != 'admin':
        return redirect('login')
        
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if Subject.objects.filter(code=code).exists():
            messages.error(request, 'Subject code already exists')
            return redirect('subject_list')
            
        Subject.objects.create(
            code=code,
            name=name,
            description=description
        )
        messages.success(request, 'Subject created successfully')
        return redirect('subject_list')
    
    return redirect('subject_list')

@login_required
def subject_edit(request, subject_id):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        try:
            code = request.POST.get('code')
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            
            # Check if another subject has the same code
            if Subject.objects.exclude(id=subject_id).filter(code=code).exists():
                messages.error(request, 'Subject code already exists')
                return redirect('subject_list')
            
            subject.code = code
            subject.name = name
            subject.description = description
            subject.save()
            
            messages.success(request, 'Subject updated successfully')
        except Exception as e:
            messages.error(request, f'Error updating subject: {str(e)}')
        
        return redirect('subject_list')
    
    return redirect('subject_list')

@login_required
def subject_delete(request, subject_id):
    if request.user.user_type != 'admin':
        return redirect('login')
    
    subject = get_object_or_404(Subject, id=subject_id)
    
    try:
        subject.delete()
        messages.success(request, 'Subject deleted successfully')
    except Exception as e:
        messages.error(request, 'Cannot delete subject that is in use')
    
    return redirect('subject_list')