"""
Authentication views for user login, logout, and registration.

This module provides views for user authentication operations including
login, logout, and user registration with email-based authentication.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from pathlib import Path
import sys

# Initialize paths - handling both frozen and regular execution
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

# Get project root (go up from web/accounts/ to project root)
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Add project root to sys.path if not already present
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.logging_utils.logging_config import get_logger

# Initialize logger for accounts module
logger = get_logger('accounts')

from .models import User


def login_view(request):
    """
    Handle user login with email and password.
    
    GET: Display login form
    POST: Authenticate user and create session
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: Login page or redirect to next page
    """
    logger.debug(f"Login view accessed - Method: {request.method}")
    
    # Redirect if already authenticated
    if request.user.is_authenticated:
        logger.info(f"User {request.user.email} already authenticated, redirecting")
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        logger.debug(f"Login attempt for email: {email}")
        
        # Validate inputs
        if not email or not password:
            logger.warning("Login attempt with missing email or password")
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'accounts/login.html')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Log the user in
            login(request, user)
            logger.info(f"User {email} successfully logged in")
            messages.success(request, f'Welcome back, {user.get_short_name()}!')
            
            # Redirect to next page or home
            next_url = request.GET.get('next', 'home')
            logger.debug(f"Redirecting to: {next_url}")
            return redirect(next_url)
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            messages.error(request, 'Invalid email or password.')
    
    logger.debug("Rendering login form")
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """
    Handle user logout.
    
    Logs out the current user and redirects to home page.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: Redirect to home page
    """
    user_email = request.user.email if request.user.is_authenticated else 'Unknown'
    logger.info(f"User {user_email} logging out")
    
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    
    logger.debug("User logged out successfully")
    return redirect('home')


def register_view(request):
    """
    Handle user registration.
    
    GET: Display registration form
    POST: Create new user account
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: Registration page or redirect to home after success
    """
    logger.debug(f"Register view accessed - Method: {request.method}")
    
    # Redirect if already authenticated
    if request.user.is_authenticated:
        logger.info(f"User {request.user.email} already authenticated, redirecting")
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        logger.debug(f"Registration attempt for email: {email}")
        
        # Validate inputs
        if not email:
            logger.warning("Registration attempt with missing email")
            messages.error(request, 'Email address is required.')
            return render(request, 'accounts/register.html', {
                'first_name': first_name,
                'last_name': last_name,
            })
        
        if not password:
            logger.warning("Registration attempt with missing password")
            messages.error(request, 'Password is required.')
            return render(request, 'accounts/register.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Validate password confirmation
        if password != password_confirm:
            logger.warning("Registration attempt with mismatched passwords")
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/register.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Validate password strength
        if len(password) < 8:
            logger.warning("Registration attempt with weak password")
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'accounts/register.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            logger.warning(f"Registration attempt with existing email: {email}")
            messages.info(request, f'An account with the email "{email}" already exists. Please log in instead.')
            return redirect('accounts:login')
        
        try:
            # Create new user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            logger.info(f"New user registered: {email}")
            
            # Log the user in automatically
            login(request, user)
            logger.info(f"New user {email} automatically logged in")
            
            messages.success(request, f'Welcome, {user.get_short_name()}! Your account has been created.')
            return redirect('home')
            
        except IntegrityError:
            logger.warning(f"Registration attempt with existing email: {email}")
            messages.info(request, f'An account with the email "{email}" already exists. Please log in instead.')
            return redirect('accounts:login')
        except Exception as e:
            logger.error(f"Error during registration for {email}: {str(e)}", exc_info=True)
            messages.error(request, f'An error occurred during registration: {str(e)}. Please try again or contact support.')
            return render(request, 'accounts/register.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
    
    logger.debug("Rendering registration form")
    return render(request, 'accounts/register.html')

