from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def available_models(request):
    """Return list of available models"""
    models = [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "description": "Most capable model, best for complex tasks",
            "type": "text"
        },
        {
            "id": "gpt-4-vision-preview",
            "name": "GPT-4 Vision",
            "description": "Capable of understanding images",
            "type": "image"
        },
        {
            "id": "whisper-1",
            "name": "Whisper",
            "description": "Speech to text model",
            "type": "audio"
        }
    ]
    return Response(models) 