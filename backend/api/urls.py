from django.urls import path
from core.views import AnalyzeFilesView, AnalysisListView, TagDocumentsView
from api.views.graph_views import index_and_find_path
from api.views import conversation_views
from api.views.pilot_views import pilot_instruction, test_connection
from django.urls import get_resolver

urlpatterns = [
    path('analyze-files/', AnalyzeFilesView.as_view(), name='analyze-files'),
    path('analyses/', AnalysisListView.as_view(), name='analysis-list'),
    path('tag-documents/', TagDocumentsView.as_view(), name='tag-documents'),
    path('graph/process/', index_and_find_path, name='graph-process'),
    path('conversation/start', conversation_views.start_conversation, name='start_conversation'),
    path('conversation/command', conversation_views.send_command, name='send_command'),
    path('conversation/description', conversation_views.send_description, name='send_description'),
    path('conversation/clear-cache', conversation_views.clear_cache, name='clear_cache'),
    path('test/', test_connection, name='test_connection'),
    path('pilot/instruction/', pilot_instruction, name='pilot_instruction'),
]

if __name__ == '__main__':
    print("\nAvailable URLs:")
    resolver = get_resolver()
    for pattern in resolver.url_patterns:
        print(f"- {pattern.pattern}") 