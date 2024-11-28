import json
import asyncio
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from modules.conversation_handler import ConversationHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_interaction(direction: str, data: Dict[str, Any]) -> None:
    """Log API interactions with formatted output"""
    logger.info(f"\n{'='*50}\n{direction} API Message:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n{'='*50}\n")

async def handle_conversation_request(request_data: Dict[str, Any], handler_method: str) -> JsonResponse:
    """Generic handler for conversation requests with delay and logging"""
    try:
        # Initialize conversation handler
        handler = ConversationHandler()
        
        # Log the incoming request
        log_api_interaction("Incoming Request", request_data)
        
        # Get the appropriate method
        method = getattr(handler, handler_method)
        
        # Execute the method with appropriate parameters
        if handler_method == 'start_conversation':
            response = await method()
        elif handler_method == 'send_command':
            response = await method(request_data.get('command'))
        elif handler_method == 'send_description':
            response = await method(request_data.get('description'))
        elif handler_method == 'clear_cache':
            response = await method()
        else:
            response = await method(request_data)
            
        # Log the API response
        log_api_interaction("API Response", response)
        
        # Process the response through LLM if it's not an error
        if response.get('status') != 'error' and 'message' in response:
            # Add 30-second delay
            await asyncio.sleep(30)
            
            # Process the message
            processed_response = await handler.process_message(response['message'])
            
            # Log the processed response
            log_api_interaction("Processed Response", processed_response)
            
            return JsonResponse(processed_response)
        
        return JsonResponse(response)
        
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e)
        }
        log_api_interaction("Error Response", error_response)
        return JsonResponse(error_response)

@csrf_exempt
@require_http_methods(["POST"])
async def start_conversation(request):
    """Start a new conversation"""
    return await handle_conversation_request({}, 'start_conversation')

@csrf_exempt
@require_http_methods(["POST"])
async def send_command(request):
    """Send a command to the API"""
    try:
        data = json.loads(request.body)
        return await handle_conversation_request(data, 'send_command')
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"})

@csrf_exempt
@require_http_methods(["POST"])
async def send_description(request):
    """Send the final description"""
    try:
        data = json.loads(request.body)
        return await handle_conversation_request(data, 'send_description')
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"})

@csrf_exempt
@require_http_methods(["POST"])
async def clear_cache(request):
    """Clear all cached analyses"""
    return await handle_conversation_request({}, 'clear_cache') 