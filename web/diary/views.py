from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import subprocess
import os
from pathlib import Path
import sys

from .models import IngestItem

# Initialize paths for logging
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.logging_utils.logging_config import get_logger
from .services import delete_item

# Initialize logger
logger = get_logger('diary')


def home(request):
    items = (
        IngestItem.objects
        .filter(is_deleted=False)
        .prefetch_related("tags")
        .order_by("-occurred_at")
    )[:7]
    return render(request, "diary/home.html", {"items": items})


@login_required
def dashboard(request):
    """Read-only dashboard for authenticated users showing recent entries."""
    items = (
        IngestItem.objects
        .filter(is_deleted=False)
        .prefetch_related("tags")
        .order_by("-occurred_at")
    )
    paginator = Paginator(items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "diary/dashboard.html", {"page_obj": page_obj})


@login_required
def manage(request):
    """Management area for authenticated users (actions live here)."""
    logger.debug(f"Manage view accessed by user {request.user.email}")
    
    # Query and paginate entries (same as dashboard)
    items = (
        IngestItem.objects
        .filter(is_deleted=False)
        .prefetch_related("tags")
        .order_by("-occurred_at")
    )
    paginator = Paginator(items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    logger.debug(f"Manage page {page_number or 1} showing {page_obj.object_list.count()} items")
    
    return render(request, "diary/manage.html", {"page_obj": page_obj})


@login_required
def execute(request):
    """Render the execute script page."""
    return render(request, "diary/execute.html")


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def execute_script(request):
    """Execute the pipeline script when button is clicked."""
    try:
        # Script path from the other project
        script_path = r"C:\Users\pmpmt\V6-Voice_diary_records\run_pipelines.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            return JsonResponse({
                'success': False, 
                'message': f'Script not found: {script_path}'
            }, status=404)
        
        # Execute the script
        result = subprocess.run(
            ['python', script_path], 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            return JsonResponse({
                'success': True, 
                'message': 'Script executed successfully',
                'output': result.stdout
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Script execution failed',
                'error': result.stderr
            }, status=500)
            
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False, 
            'message': 'Script execution timed out'
        }, status=408)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error executing script: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_item_view(request, item_id):
    """
    Delete a diary entry (soft or hard based on configuration).
    
    This endpoint handles deletion requests from the web interface.
    Only authenticated users can delete entries.
    
    Args:
        request: Django HTTP request object
        item_id: UUID of the IngestItem to delete
        
    Returns:
        JsonResponse: Success status and message
            - 200: {'success': True, 'message': 'Entry deleted'}
            - 404: {'success': False, 'error': 'Item not found'}
            - 500: {'success': False, 'error': 'Error message'}
    """
    logger.debug(f"Delete request for item {item_id} by user {request.user.email}")
    
    try:
        # Lookup item (only non-deleted items can be deleted)
        item = IngestItem.objects.get(id=item_id, is_deleted=False)
        
        logger.info(f"Deleting item {item_id}: {item.content_text[:50] if item.content_text else '(no content)'}")
        
        # Call delete service
        delete_item(item)
        
        logger.info(f"Successfully processed delete request for item {item_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Entry deleted successfully'
        })
        
    except IngestItem.DoesNotExist:
        logger.warning(f"Delete request for non-existent item {item_id}")
        return JsonResponse({
            'success': False,
            'error': 'Item not found or already deleted'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error deleting item {item_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred while deleting: {str(e)}'
        }, status=500)


