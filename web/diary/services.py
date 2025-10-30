"""
Business logic layer for diary operations.

This module handles diary entry operations including deletion with
configurable soft/hard delete modes, comprehensive logging, and audit trails.
"""
from pathlib import Path
from django.utils import timezone
import sys

# Initialize paths - handling both frozen and regular execution
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

# Get project root (go up from web/diary/ to project root)
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Add project root to sys.path if not already present
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.logging_utils.logging_config import get_logger
from .diary_config import config
from .models import IngestItem

# Initialize logger for diary module
logger = get_logger('diary')


def delete_item(item: IngestItem, deletion_mode: str = None) -> bool:
    """
    Delete a diary entry based on configured deletion mode.
    
    This function handles both soft and hard deletion:
    - Soft delete: Sets is_deleted=True, deletion_type='soft', deleted_at=now()
      Entry is preserved in database for recovery/audit
    - Hard delete: Sets deletion_type='hard', then physically removes from database
      Used for permanent removal (future feature)
    
    Args:
        item: The IngestItem to delete
        deletion_mode: Override config deletion mode (for testing)
                      Valid values: 'soft', 'hard'
                      If None, uses config.deletion_mode
    
    Returns:
        bool: True if deletion successful
        
    Raises:
        ValueError: If deletion_mode is invalid
        Exception: If database operation fails
        
    Examples:
        # Soft delete (default)
        >>> delete_item(item)
        True
        
        # Override to hard delete
        >>> delete_item(item, deletion_mode='hard')
        True
    """
    # Get deletion mode from parameter or config
    mode = deletion_mode or config.deletion_mode
    
    # Validate deletion mode
    if mode not in ['soft', 'hard']:
        logger.error(f"Invalid deletion mode: {mode}")
        raise ValueError(f"Invalid deletion mode: {mode}. Must be 'soft' or 'hard'")
    
    item_id = str(item.id)
    item_title = item.content_text[:50] if item.content_text else '(no content)'
    
    try:
        if mode == 'soft':
            # Soft delete: Mark as deleted but preserve data
            logger.debug(f"Soft deleting item {item_id}: {item_title}")
            
            item.is_deleted = True
            item.deletion_type = 'soft'
            item.deleted_at = timezone.now()
            
            # Save with specific fields for efficiency
            item.save(update_fields=['is_deleted', 'deletion_type', 'deleted_at'])
            
            logger.info(
                f"Successfully soft deleted item {item_id} "
                f"at {item.deleted_at.isoformat()}"
            )
            
        elif mode == 'hard':
            # Hard delete: Remove from database permanently
            logger.debug(f"Hard deleting item {item_id}: {item_title}")
            
            # Set deletion type before physical removal (for any triggers/logs)
            item.deletion_type = 'hard'
            item.deleted_at = timezone.now()
            item.save(update_fields=['deletion_type', 'deleted_at'])
            
            # Physical deletion
            item.delete()
            
            logger.info(f"Successfully hard deleted item {item_id}")
        
        return True
        
    except Exception as e:
        logger.error(
            f"Error deleting item {item_id} (mode: {mode}): {str(e)}",
            exc_info=True
        )
        raise


def get_deleted_items(include_hard_deleted: bool = False):
    """
    Retrieve soft-deleted items for potential recovery.
    
    Args:
        include_hard_deleted: If True, include items marked for hard delete
        
    Returns:
        QuerySet: Deleted IngestItem objects
        
    Note:
        This is a helper function for future "Trash" page implementation.
    """
    logger.debug(f"Fetching deleted items (include_hard: {include_hard_deleted})")
    
    queryset = IngestItem.objects.filter(is_deleted=True)
    
    if not include_hard_deleted:
        queryset = queryset.filter(deletion_type='soft')
    
    logger.debug(f"Found {queryset.count()} deleted items")
    return queryset


def restore_item(item: IngestItem) -> bool:
    """
    Restore a soft-deleted item.
    
    Args:
        item: The IngestItem to restore
        
    Returns:
        bool: True if restoration successful
        
    Raises:
        ValueError: If item is hard-deleted (cannot restore)
        Exception: If database operation fails
        
    Note:
        This function is for future "Restore" feature implementation.
    """
    if item.deletion_type == 'hard':
        logger.warning(f"Cannot restore hard-deleted item {item.id}")
        raise ValueError("Cannot restore hard-deleted items")
    
    if not item.is_deleted:
        logger.warning(f"Item {item.id} is not deleted, no restoration needed")
        return True
    
    try:
        logger.debug(f"Restoring item {item.id}")
        
        item.is_deleted = False
        item.deleted_at = None
        item.save(update_fields=['is_deleted', 'deleted_at'])
        
        logger.info(f"Successfully restored item {item.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error restoring item {item.id}: {str(e)}", exc_info=True)
        raise

