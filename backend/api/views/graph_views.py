from rest_framework.decorators import api_view
from rest_framework.response import Response
from modules.graph_indexer import GraphIndexer
from modules.path_finder import PathFinder
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

@csrf_exempt
@api_view(['POST'])
def index_and_find_path(request):
    """Index data and find shortest path"""
    async def process():
        try:
            # Step 1: Index data
            print("Starting data indexing...")
            indexer = GraphIndexer()
            index_result = await indexer.index_data()
            indexer.close()
            
            if index_result["status"] != "success":
                return Response({
                    "status": "error",
                    "message": "Failed to index data",
                    "details": index_result
                })
                
            print("Data indexed successfully")
            
            # Step 2: Find path
            print("Finding shortest path...")
            finder = PathFinder()
            path_result = await finder.process()
            finder.close()
            
            if path_result["status"] != "success":
                return Response({
                    "status": "error",
                    "message": "Failed to find path",
                    "details": path_result
                })
                
            return Response({
                "status": "success",
                "indexing": index_result,
                "path": path_result["path"]
            })
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            })

    # Uruchom funkcję asynchroniczną synchronicznie
    return async_to_sync(process)() 