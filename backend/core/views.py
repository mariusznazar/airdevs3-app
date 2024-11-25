from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from typing import Dict, Any
from modules.openai_client import OpenAIClient
import base64
from asgiref.sync import async_to_sync
from django.http import JsonResponse
from modules.file_analyzer import FileAnalyzer
import asyncio
from .models import FileAnalysis
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from modules.web_crawler import WebCrawlerProcessor
from asgiref.sync import sync_to_async

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

class BaseLLMView(APIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_client = OpenAIClient()

    def prepare_messages(self, data):
        messages = []
        if 'messages' in data:
            return data['messages']
        return messages

class TextLLMView(BaseLLMView):
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            data = request.data
            messages = self.prepare_messages(data)
            
            # Opakowujemy asynchroniczne wywołanie w async_to_sync
            response = async_to_sync(self.openai_client.chat_completion)(
                messages=messages,
                model=data.get('model', 'gpt-4'),
                temperature=data.get('temperature', 0.7)
            )
            
            # Upewniamy się, że zwracamy Response, a nie coroutine
            return Response({
                "status": "success",
                "data": response
            })
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=400)

class AudioLLMView(BaseLLMView):
    parser_classes = [MultiPartParser, FormParser]

    async def post(self, request):
        try:
            audio_file = request.FILES.get('audio')
            if not audio_file:
                return Response({"error": "No audio file provided"}, status=400)

            # First transcribe the audio
            transcription = await self.openai_client.transcribe_audio(
                audio_file=audio_file,
                model=request.data.get('transcription_model', 'whisper-1')
            )

            if transcription.get('status') != 'success':
                return Response(transcription, status=400)

            # Prepare messages with transcription
            data = request.data.dict()
            data['user_message'] = f"{data.get('user_message', '')}\n\nTranscription: {transcription['text']}"
            messages = self.prepare_messages(data)

            # Process with GPT
            response = await self.openai_client.chat_completion(
                messages=messages,
                model=data.get('model', 'gpt-4'),
                temperature=data.get('temperature', 0.7)
            )

            return Response({
                **response,
                'transcription': transcription['text']
            })
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class ImageLLMView(BaseLLMView):
    parser_classes = [MultiPartParser, FormParser]

    async def post(self, request):
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return Response({"error": "No image file provided"}, status=400)

            # Convert image to base64
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_data}"

            # Prepare messages with image
            data = request.data.dict()
            messages = self.prepare_messages(data)
            
            # Add image to the last user message
            if messages and messages[-1]['role'] == 'user':
                messages[-1]['content'] = [
                    {"type": "text", "text": messages[-1]['content']},
                    {"type": "image_url", "image_url": image_url}
                ]

            response = await self.openai_client.chat_completion(
                messages=messages,
                model=data.get('model', 'gpt-4-vision-preview'),
                temperature=data.get('temperature', 0.7)
            )

            return Response(response)
        except Exception as e:
            return Response({"error": str(e)}, status=400) 

class AnalyzeFilesView(APIView):
    def post(self, request):
        try:
            analyzer = FileAnalyzer()
            # Uruchamiamy asynchroniczną funkcję w synchronicznym kontekście
            result = asyncio.run(analyzer.process())
            return Response({
                "status": "success",
                "data": result
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=500) 

class CacheStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {
            'total_files': FileAnalysis.objects.count(),
            'by_type': FileAnalysis.objects.values('file_type').annotate(count=Count('id')),
            'by_category': FileAnalysis.objects.values('category').annotate(count=Count('id')),
            'recent': FileAnalysis.objects.order_by('-updated_at')[:5].values(
                'file_name', 'file_type', 'category', 'updated_at'
            )
        }
        return Response(stats) 

class AnalysisListView(APIView):
    def get(self, request):
        analyses = FileAnalysis.objects.all().values(
            'file_name', 
            'file_type', 
            'category', 
            'content', 
            'created_at'
        ).order_by('-created_at')
        
        summary = {
            'total': FileAnalysis.objects.count(),
            'by_type': dict(FileAnalysis.objects.values_list('file_type').annotate(count=Count('id'))),
            'by_category': dict(FileAnalysis.objects.values_list('category').annotate(count=Count('id'))),
            'analyses': list(analyses)
        }
        
        return Response(summary) 

@api_view(['POST'])
def process_webpage(request):
    """
    Process webpage and extract content with media
    """
    url = request.data.get('url')
    if not url:
        return Response({
            'status': 'error',
            'message': 'URL is required'
        }, status=400)
        
    try:
        crawler = WebCrawlerProcessor()
        # Używamy async_to_sync do wywołania asynchronicznej metody
        result = async_to_sync(crawler.process_url)(url)
        return Response(result)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500) 