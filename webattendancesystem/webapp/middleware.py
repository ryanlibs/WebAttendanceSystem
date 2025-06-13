from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # URLs that don't require authentication
        EXEMPT_URLS = [
            reverse('login'),
            '/static/',
            '/media/',
        ]
        
        if not request.user.is_authenticated:
            path = request.path_info
            if not any(url in path for url in EXEMPT_URLS):
                messages.warning(request, 'Please login to continue')
                return redirect(f"{reverse('login')}?next={path}")
                
        response = self.get_response(request)
        return response