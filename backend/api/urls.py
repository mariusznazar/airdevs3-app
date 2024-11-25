from django.urls import path
from core.views import AnalyzeFilesView, AnalysisListView, TagDocumentsView

urlpatterns = [
    path('analyze-files/', AnalyzeFilesView.as_view(), name='analyze-files'),
    path('analyses/', AnalysisListView.as_view(), name='analysis-list'),
    path('tag-documents/', TagDocumentsView.as_view(), name='tag-documents'),
] 