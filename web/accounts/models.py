"""
Custom User model for email-based authentication.

This module defines a custom User model that uses email as the primary
identifier instead of username, along with a custom UserManager.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model with email-based authentication.
    
    This manager provides methods to create regular users and superusers
    using email as the primary identifier.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        
        Args:
            email (str): User's email address (required)
            password (str): User's password (optional)
            **extra_fields: Additional fields for the user model
            
        Returns:
            User: The created user instance
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('Email address is required')
        
        # Normalize email (lowercase domain part)
        email = self.normalize_email(email)
        
        # Create user instance
        user = self.model(email=email, **extra_fields)
        
        # Set password (hashes it automatically)
        user.set_password(password)
        
        # Save to database
        user.save(using=self._db)
        
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        
        Args:
            email (str): User's email address (required)
            password (str): User's password (required)
            **extra_fields: Additional fields for the user model
            
        Returns:
            User: The created superuser instance
        """
        # Set superuser flags
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        # Validate superuser flags
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the username field.
    
    This model extends Django's AbstractBaseUser and PermissionsMixin to provide
    email-based authentication with all standard Django permissions functionality.
    
    Fields:
        email: Primary identifier and login field (unique)
        first_name: User's first name (optional)
        last_name: User's last name (optional)
        is_active: Whether the user account is active
        is_staff: Whether the user can access admin site
        date_joined: Timestamp when the user was created
    """
    
    email = models.EmailField(
        'email address',
        unique=True,
        help_text='Required. Must be a valid email address.'
    )
    first_name = models.CharField(
        'first name',
        max_length=150,
        blank=True
    )
    last_name = models.CharField(
        'last name',
        max_length=150,
        blank=True
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Designates whether this user should be treated as active. '
                  'Unselect this instead of deleting accounts.'
    )
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Designates whether the user can log into the admin site.'
    )
    date_joined = models.DateTimeField(
        'date joined',
        default=timezone.now
    )
    
    # Use custom manager
    objects = UserManager()
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required as USERNAME_FIELD
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        db_table = 'auth_user'
    
    def __str__(self):
        """String representation of the user."""
        return self.email
    
    def get_full_name(self):
        """
        Return the user's full name.
        
        Returns:
            str: Full name (first + last) or email if names not provided
        """
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.email
    
    def get_short_name(self):
        """
        Return the user's short name.
        
        Returns:
            str: First name or email if first name not provided
        """
        return self.first_name or self.email

