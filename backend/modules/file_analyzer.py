import os
import json
import base64
import aiohttp
from typing import Dict, List, Tuple
from .base_processor import BaseProcessor
from django.conf import settings
from core.models import FileAnalysis
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from .openai_client import OpenAIClient
from modules.text.analyzer import TextAnalyzer

class FileAnalyzer(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.data_dir = os.path.join(settings.BASE_DIR, 'data', 'raw', 'pliki_z_fabryki')
        print(f"Looking for files in: {self.data_dir}")
        
        if not os.path.exists(self.data_dir):
            print(f"Creating directory: {self.data_dir}")
            os.makedirs(self.data_dir, exist_ok=True)
            
        self.supported_extensions = {
            'txt': self._process_text,
            'png': self._process_image,
            'mp3': self._process_audio
        }
        
        # Czas ważności cache'a (np. 24 godziny)
        self.cache_ttl = timedelta(hours=24)

    @sync_to_async
    def _get_cached_analysis(self, file_name: str, check_type: str = 'both') -> FileAnalysis:
        """
        Get cached analysis if exists and not expired
        check_type: 'content', 'category' or 'both'
        """
        try:
            cached = FileAnalysis.objects.get(file_name=file_name)
            age = timezone.now() - cached.updated_at
            
            # Zawsze sprawdź czy cache nie wygasł
            if age > self.cache_ttl:
                return None
            
            # Sprawdź content tylko jeśli o to prosiliśmy
            if check_type in ['content', 'both'] and not cached.content:
                return None
            
            # Sprawdź kategorię tylko jeśli o to prosiliśmy
            if check_type in ['category', 'both'] and not cached.category:
                return None
            
            return cached
        except FileAnalysis.DoesNotExist:
            return None

    @sync_to_async
    def _save_analysis(self, file_name: str, file_type: str, content: str, category: str = None) -> None:
        """Save or update analysis in cache"""
        FileAnalysis.objects.update_or_create(
            file_name=file_name,
            defaults={
                'file_type': file_type,
                'content': content,
                'category': category
            }
        )

    async def process(self) -> Dict[str, List[str]]:
        """Main processing method"""
        try:
            # Krok 1: Analiza plików
            print("Step 1: Analyzing files...")
            files_content = await self._analyze_files()
            print(f"Found {len(files_content)} files to analyze")

            # Krok 2: Kategoryzacja
            print("Step 2: Categorizing files...")
            categorized_files = await self._categorize_files(files_content)
            print("Categorized files:", categorized_files)

            # Krok 3: Walidacja przed wysłaniem
            if not categorized_files.get('people') and not categorized_files.get('hardware'):
                print("Warning: No files categorized as either 'people' or 'hardware'")
                return categorized_files

            # Krok 4: Wysyłanie raportu
            print("Step 3: Sending report...")
            await self._send_report(categorized_files)
            print("Report sent successfully")

            return categorized_files
        except Exception as e:
            print(f"Error in process: {str(e)}")
            raise

    async def _analyze_files(self) -> List[Tuple[str, str]]:
        """Analyze all files in the data directory"""
        results = []
        
        if not os.path.exists(self.data_dir):
            print(f"Directory not found: {self.data_dir}")
            return results
            
        files = os.listdir(self.data_dir)
        print(f"Found {len(files)} files in directory")
        
        for filename in sorted(files):
            if 'fakty' in filename.lower() or filename.startswith('.'):
                print(f"Skipping file: {filename}")
                continue
                
            file_path = os.path.join(self.data_dir, filename)
            if not os.path.isfile(file_path):
                print(f"Skipping non-file: {file_path}")
                continue
                
            extension = filename.split('.')[-1].lower()
            
            if extension in self.supported_extensions:
                try:
                    # Sprawdź cache
                    cached = await self._get_cached_analysis(filename, check_type='content')
                    if cached:
                        results.append((filename, cached.content))
                        continue

                    print(f"Processing file: {filename} ({extension})")
                    content = await self.supported_extensions[extension](file_path)
                    if content:
                        # Zapisz do cache'a
                        await self._save_analysis(filename, extension, content)
                        results.append((filename, content))
                        print(f"Successfully processed: {filename}")
                    else:
                        print(f"No content extracted from: {filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
            else:
                print(f"Unsupported file extension: {extension} for file {filename}")
                    
        return results

    async def _process_text(self, file_path: str) -> str:
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading text file {file_path}: {str(e)}")
            return ""

    async def _process_image(self, file_path: str) -> str:
        """Process image files"""
        try:
            print(f"\n=== Processing image: {file_path} ===")
            with open(file_path, 'rb') as file:
                image_data = base64.b64encode(file.read()).decode('utf-8')
                
                response = await self.openai_client.chat_completion_with_vision(
                    image_data=f"data:image/png;base64,{image_data}",
                    prompt_key="analyze_image",
                    prompt_vars={},
                    model="gpt-4o-mini"  # Użyj właściwego modelu dla vision
                )
                
                print("Received image response from OpenAI:", response)
                if response.get("status") == "success":
                    content = response.get('content', '')
                    if content:
                        print(f"Extracted content from image response: {content}")
                        return content
                return ""
        except Exception as e:
            print(f"Error processing image {file_path}: {str(e)}")
            print(f"Full error details:", e.__class__.__name__, str(e))
            return ""

    async def _process_audio(self, file_path: str) -> str:
        """Process audio files"""
        try:
            print(f"\n=== Processing audio: {file_path} ===")
            with open(file_path, 'rb') as audio_file:
                print("Sending audio request to OpenAI")
                response = await self.openai_client.transcribe_audio(audio_file)
                print("Received audio response from OpenAI:", response)
                
                if isinstance(response, dict):
                    content = response.get('text', '')
                    print(f"Extracted content from audio response: {content}")
                    return content
                return str(response)
        except Exception as e:
            print(f"Error processing audio {file_path}: {str(e)}")
            print(f"Full error details:", e.__class__.__name__, str(e))
            return ""

    async def _categorize_files(self, files_content: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """Categorize files based on their content"""
        categories = {
            "people": [],
            "hardware": []
        }
        
        for filename, original_content in files_content:
            try:
                # Sprawdź cache dla kategorii
                cached = await self._get_cached_analysis(file_name=filename, check_type='category')
                if cached and cached.category:
                    if cached.category in ['people', 'hardware']:
                        categories[cached.category].append(filename)
                    continue

                print(f"\n=== Categorizing file: {filename} ===")
                
                user_prompt = f"""
                                Analyze the text and determine whether it contains information about:

                                People who were explicitly captured, or recent and concrete traces of their presence—assign these files the tag "people". Do not consider indirect mentions or hypothetical situations (e.g., digressions or humor) as evidence for the 'people' tag. Only assign 'people' if the text explicitly ties captured individuals or recent and concrete traces of their presence to the context of the described event.
                                Hardware malfunctions that have been repaired (do not include issues related to software)—assign these files the tag "hardware". Assign the 'hardware' tag only if the text explicitly mentions malfunctions of physical hardware components and confirms their repair. Do not include mentions of software issues, hypothetical problems, or unresolved malfunctions.
                                If neither of these conditions is met, assign the tag "other".
                                
                                <text for analysis>
                                {original_content}
                                </text for analysis>"""

                analyzer = TextAnalyzer()
                result = await analyzer.analyze_and_single_tag_text(user_prompt)
                
                if result.get("status") == "success":
                    try:
                        # Czyścimy odpowiedź z markdown
                        analysis_content = result['content']
                        if analysis_content.startswith('```'):
                            analysis_content = '\n'.join(analysis_content.split('\n')[1:-1])
                        
                        response_data = json.loads(analysis_content)
                        category = response_data["data"]["tags"][0].lower()
                        
                        # Zapisz kategorię do cache'a, ale zachowaj oryginalny content!
                        await self._save_analysis(
                            file_name=filename,
                            file_type=filename.split('.')[-1],
                            content=original_content,  # Używamy oryginalnego contentu
                            category=category
                        )
                        
                        if category in ['people', 'hardware']:
                            categories[category].append(filename)
                            print(f"File {filename} categorized as: {category}")
                            print(f"Reasoning: {response_data['data']['reasoning']}")
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON response for {filename}")
                        print(f"JSON Error details: {str(e)}")
                        print(f"Attempted to parse: {result['content']}")
                else:
                    print(f"Error getting category for {filename}: {result.get('error')}")
                    
            except Exception as e:
                print(f"Error categorizing {filename}: {str(e)}")
                
        return categories

    async def _send_report(self, categorized_files: Dict[str, List[str]]) -> None:
        """Send report to central server"""
        # Upewnijmy się, że mamy poprawny format
        report = {
            "task": "kategorie",
            "apikey": settings.DEFAULT_API_KEY,
            "answer": {
                "people": categorized_files.get('people', []),
                "hardware": categorized_files.get('hardware', [])
            }
        }
        
        print("Sending report with payload:", json.dumps(report, indent=2))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{settings.CENTRAL_URL}/report", json=report) as response:
                    response_text = await response.text()
                    print(f"Server response status: {response.status}")
                    print(f"Server response body: {response_text}")
                    
                    if response.status != 200:
                        raise Exception(f"Error sending report: {response_text}")
                    else:
                        print("Report sent successfully")
        except Exception as e:
            print(f"Error sending report: {str(e)}")
            raise