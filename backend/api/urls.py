from django.urls import path
from core.views import AnalyzeFilesView, AnalysisListView, TagDocumentsView
from api.views.graph_views import index_and_find_path

urlpatterns = [
    path('analyze-files/', AnalyzeFilesView.as_view(), name='analyze-files'),
    path('analyses/', AnalysisListView.as_view(), name='analysis-list'),
    path('tag-documents/', TagDocumentsView.as_view(), name='tag-documents'),
    path('graph/process/', index_and_find_path, name='graph-process'),
] 