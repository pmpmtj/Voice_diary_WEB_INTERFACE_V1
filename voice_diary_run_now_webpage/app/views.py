from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import subprocess
import os


def index(request):
    """Render the main page with the button."""
    return render(request, 'index.html')


@csrf_exempt
@require_http_methods(["POST"])
def execute_script(request):
    """Execute the Python script when button is clicked."""
    try:
        # Script path provided by user
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
            timeout=30
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
