from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def available_models(request):
    models = [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "type": "text",
            "description": "Most capable model for text generation and analysis"
        },
        {
            "id": "gpt-4-vision-preview",
            "name": "GPT-4 Vision",
            "type": "image",
            "description": "Visual analysis and understanding"
        },
        {
            "id": "gpt-4-0125-preview",
            "name": "GPT-4 Turbo",
            "types": ["text", "image", "audio"],
            "description": "Latest GPT-4 model with vision and improved capabilities"
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "type": "text",
            "description": "Faster and more cost-effective text model"
        },
        {
            "id": "dall-e-3",
            "name": "DALL-E 3",
            "type": "image",
            "description": "Advanced image generation"
        },
        {
            "id": "whisper-1",
            "name": "Whisper",
            "type": "audio",
            "description": "Speech recognition and transcription"
        }
    ]
    return Response(models) 