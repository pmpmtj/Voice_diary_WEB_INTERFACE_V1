"""
Diary application configuration.

This module provides centralized configuration for the diary app with support
for environment variables, .env files, and sensible defaults.

Configuration follows the project pattern:
1. Environment variables (highest priority)
2. .env file (if env vars not set)
3. Default values (fallback)
"""
from dataclasses import dataclass
import os


@dataclass
class DiaryConfig:
    """
    Configuration for diary application behavior.
    
    Attributes:
        deletion_mode: Deletion strategy - 'soft' (default) or 'hard'
            - 'soft': Sets is_deleted=True, preserves data for recovery/audit
            - 'hard': Physically removes records from database (future feature)
        
        require_delete_confirmation: Whether to show confirmation dialog before delete
        
        soft_delete_retention_days: Days to keep soft-deleted items before cleanup
            (for future automatic cleanup script)
    """
    
    # Deletion behavior: 'soft' or 'hard'
    deletion_mode: str = os.getenv('DIARY_DELETION_MODE', 'soft')
    
    # Require confirmation before delete (recommended for safety)
    require_delete_confirmation: bool = True
    
    # Retention period for soft-deleted items (for future cleanup script)
    soft_delete_retention_days: int = int(os.getenv('DIARY_SOFT_DELETE_RETENTION_DAYS', '90'))
    
    def validate(self):
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        if self.deletion_mode not in ['soft', 'hard']:
            raise ValueError(
                f"Invalid deletion_mode: {self.deletion_mode}. "
                f"Must be 'soft' or 'hard'"
            )
        
        if not isinstance(self.require_delete_confirmation, bool):
            raise ValueError(
                f"Invalid require_delete_confirmation: {self.require_delete_confirmation}. "
                f"Must be True or False"
            )
        
        if self.soft_delete_retention_days < 1:
            raise ValueError(
                f"Invalid soft_delete_retention_days: {self.soft_delete_retention_days}. "
                f"Must be >= 1"
            )


# Global configuration instance
config = DiaryConfig()

# Validate on module load
try:
    config.validate()
except ValueError as e:
    # Log error but don't crash - fall back to defaults
    print(f"WARNING: Invalid diary configuration: {e}")
    config = DiaryConfig()  # Reset to defaults

