import aiohttp
from typing import Dict, List, Optional
from django.conf import settings
from neo4j import GraphDatabase
from asgiref.sync import sync_to_async
from .base_reporter import BaseReporter

class PathFinder:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_CONFIG['URI'],
            auth=(settings.NEO4J_CONFIG['USERNAME'], settings.NEO4J_CONFIG['PASSWORD'])
        )
        self.reporter = BaseReporter()

    @sync_to_async
    def find_shortest_path(self, start_name: str, end_name: str) -> Optional[List[str]]:
        """Find shortest path between two users by their names"""
        try:
            with self.neo4j_driver.session() as session:
                # Cypher query to find shortest path
                result = session.run("""
                    MATCH path = shortestPath(
                        (start:User {name: $start_name})-[:KNOWS*]-(end:User {name: $end_name})
                    )
                    RETURN [node in nodes(path) | node.name] as names
                """, start_name=start_name, end_name=end_name)
                
                record = result.single()
                if record:
                    return record["names"]
                return None
                
        except Exception as e:
            print(f"Error finding path: {str(e)}")
            return None

    async def process(self) -> Dict[str, str]:
        """Main method to find path from Rafał to Barbara and send report"""
        try:
            # Find shortest path
            path = await self.find_shortest_path("Rafał", "Barbara")
            
            if not path:
                return {
                    "status": "error",
                    "message": "No path found between Rafał and Barbara"
                }
            
            # Convert path to comma-separated string
            path_string = ", ".join(path)
            print(f"Found path: {path_string}")
            
            # Send report
            await self.reporter.send_report("connections", path_string)
            
            return {
                "status": "success",
                "path": path_string
            }
            
        except Exception as e:
            print(f"Error in process: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    def close(self):
        """Close Neo4j driver connection"""
        self.neo4j_driver.close() 