# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Teacher, Student  # Import your User model here

def login_view(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please enter both email and password')
            return render(request, 'webapp/login.html')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            
            # Redirect to 'next' URL if provided
            if next_url:
                return redirect(next_url)
                
            # Otherwise redirect based on user type
            if user.user_type == 'admin':
                return redirect('admin_dashboard')
            elif user.user_type == 'teacher':
                return redirect('teacher_dashboard')
            elif user.user_type == 'student':
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'webapp/login.html', {'next': next_url})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')

@login_required
def dashboard_redirect(request):
    """Redirect users to their appropriate dashboard based on user type"""
    if request.user.user_type == 'admin':
        return redirect('admin_dashboard')
    elif request.user.user_type == 'teacher':
        return redirect('teacher_dashboard')
    elif request.user.user_type == 'student':
        return redirect('student_dashboard')
    else:
        messages.error(request, 'Invalid user type')
        return redirect('login')

@login_required
def profile_view(request):
    context = {}
    if request.user.user_type == 'teacher':
        teacher = get_object_or_404(Teacher, user=request.user)
        context['profile'] = teacher
        return render(request, 'webapp/teacher/profile.html', context)
    elif request.user.user_type == 'student':
        student = get_object_or_404(Student, user=request.user)
        context['profile'] = student
        return render(request, 'webapp/student/profile.html', context)
    else:
        context['profile'] = request.user
        return render(request, 'webapp/admin/profile.html', context)