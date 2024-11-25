from django.urls import path
from . import views
from .views import TextLLMView, AudioLLMView, ImageLLMView, process_webpage, analyze_arxiv

app_name = 'core'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('llm/text/', TextLLMView.as_view(), name='llm-text'),
    path('llm/audio/', AudioLLMView.as_view(), name='llm-audio'),
    path('llm/image/', ImageLLMView.as_view(), name='llm-image'),
    path('web-crawler/process/', process_webpage, name='process-webpage'),
    path('analyze-arxiv/', analyze_arxiv, name='analyze-arxiv'),
] 