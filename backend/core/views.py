from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def health_check(request):
    """
    Basic health check endpoint
    """
    logger.info(f"Health check requested from: {request.META.get('REMOTE_ADDR')}")
    logger.info(f"Request headers: {request.headers}")
    
    response = Response(
        {"status": "healthy"},
        status=status.HTTP_200_OK
    )
    
    logger.info(f"Sending response: {response.data}")
    return response 