import aiohttp
import json
from typing import Dict, List, Any
from django.conf import settings
from neo4j import GraphDatabase
import asyncio
from asgiref.sync import sync_to_async

class GraphIndexer:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_CONFIG['URI'],
            auth=(settings.NEO4J_CONFIG['USERNAME'], settings.NEO4J_CONFIG['PASSWORD'])
        )
        self.api_url = "https://centrala.ag3nts.org/apidb"
        self.api_key = settings.DEFAULT_API_KEY

    async def fetch_data(self, query: str) -> List[Dict[str, Any]]:
        """Fetch data from the API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "task": "database",
                    "apikey": self.api_key,
                    "query": query
                }
                
                print(f"Sending request to {self.api_url} with payload:", payload)
                
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"API error: {await response.text()}")
                    
                    data = await response.json()
                    print(f"API Response: {json.dumps(data, indent=2)}")
                    
                    # Wyciągnij dane z klucza 'reply'
                    result = data.get('reply', [])
                    print(f"Extracted data: {json.dumps(result, indent=2)}")
                    
                    if isinstance(result, list):
                        # Mapuj dane dla users
                        if 'username' in result[0]:
                            return [{'id': item['id'], 'name': item['username']} for item in result]
                        # Mapuj dane dla connections
                        elif 'user1_id' in result[0]:
                            return [{'source_id': item['user1_id'], 'target_id': item['user2_id']} for item in result]
                        
                    return result
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            raise

    @sync_to_async
    def _verify_database(self):
        """Verify database state"""
        with self.neo4j_driver.session() as session:
            # Sprawdź węzły
            result = session.run("MATCH (n:User) RETURN count(n) as count")
            node_count = result.single()["count"]
            print(f"Verified nodes in database: {node_count}")
            
            # Sprawdź relacje
            result = session.run("MATCH ()-[r:KNOWS]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"Verified relationships in database: {rel_count}")

    @sync_to_async
    def _clear_database(self):
        """Clear all nodes and relationships from Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared")

    @sync_to_async
    def _create_users(self, users: List[Dict[str, Any]]):
        """Create user nodes in Neo4j"""
        with self.neo4j_driver.session() as session:
            for user in users:
                print(f"Processing user data: {user}")
                try:
                    # Obsługa różnych formatów danych
                    if isinstance(user, (list, tuple)):
                        user_id, name = user
                    elif isinstance(user, dict):
                        user_id = user.get('id')
                        name = user.get('name')
                    else:
                        print(f"Unexpected user data format: {type(user)}")
                        continue

                    if user_id is not None and name is not None:
                        print(f"Creating user node: id={user_id}, name={name}")
                        session.run(
                            "CREATE (u:User {id: $id, name: $name})",
                            id=str(user_id), name=str(name)
                        )
                except Exception as e:
                    print(f"Error creating user node: {str(e)}")
                    raise

            # Create unique constraint on name
            try:
                session.run("CREATE CONSTRAINT user_name IF NOT EXISTS FOR (u:User) REQUIRE u.name IS UNIQUE")
            except Exception as e:
                print(f"Warning: Constraint creation failed (might already exist): {str(e)}")

    @sync_to_async
    def _create_connections(self, connections: List[Dict[str, Any]]):
        """Create relationships between users in Neo4j"""
        with self.neo4j_driver.session() as session:
            for conn in connections:
                print(f"Processing connection data: {conn}")
                try:
                    # Obsługa różnych formatów danych
                    if isinstance(conn, (list, tuple)):
                        source_id, target_id = conn
                    elif isinstance(conn, dict):
                        source_id = conn.get('source_id')
                        target_id = conn.get('target_id')
                    else:
                        print(f"Unexpected connection data format: {type(conn)}")
                        continue

                    if source_id is not None and target_id is not None:
                        print(f"Creating relationship: {source_id} -> {target_id}")
                        session.run("""
                            MATCH (u1:User {id: $source_id})
                            MATCH (u2:User {id: $target_id})
                            CREATE (u1)-[:KNOWS]->(u2)
                        """, source_id=str(source_id), target_id=str(target_id))
                except Exception as e:
                    print(f"Error creating relationship: {str(e)}")
                    raise

    async def index_data(self) -> Dict[str, Any]:
        """Main method to index data from MySQL to Neo4j"""
        try:
            print("\n=== Fetching users data ===")
            users_data = await self.fetch_data("SELECT * FROM users")
            print(f"\nProcessed users data: {json.dumps(users_data, indent=2)}")
            
            print("\n=== Fetching connections data ===")
            connections_data = await self.fetch_data("SELECT * FROM connections")
            print(f"\nProcessed connections data: {json.dumps(connections_data, indent=2)}")
            
            print(f"\nFound {len(users_data)} users and {len(connections_data)} connections")
            
            print("\n=== Clearing database ===")
            await self._clear_database()
            
            print("\n=== Creating user nodes ===")
            await self._create_users(users_data)
            
            print("\n=== Creating connections ===")
            await self._create_connections(connections_data)
            
            print("\n=== Verifying database state ===")
            await self._verify_database()
            
            return {
                "status": "success",
                "users_count": len(users_data),
                "connections_count": len(connections_data)
            }
            
        except Exception as e:
            print(f"Error indexing data: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    def close(self):
        """Close Neo4j driver connection"""
        self.neo4j_driver.close() 