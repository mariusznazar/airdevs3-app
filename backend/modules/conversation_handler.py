import aiohttp
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
from .openai_client import OpenAIClient
from .file_analyzer import FileAnalyzer
from core.models import FileAnalysis
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
import re
from urllib.parse import urljoin
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from pathlib import Path
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationHandler:
    def __init__(self):
        self.api_url = "https://centrala.ag3nts.org/report"
        self.api_key = settings.DEFAULT_API_KEY  # This will get the key from .env
        self.openai_client = OpenAIClient()
        self.file_analyzer = FileAnalyzer()
        self.base_url = "https://centrala.ag3nts.org"
        
        logger.info(f"Initialized ConversationHandler with API URL: {self.api_url}")
        
        # System prompt for the LLM
        self.system_prompt = """
        Jesteś asystentem AI pomagającym przeanalizować zdjęcia i stworzyć szczegółowy rysopis osoby o imieniu Barbara.
        
        Konwersacja będzie dotyczyć analizy zdjęć, które mogą przedstawiać Barbarę. Niektóre zdjęcia mogą być uszkodzone lub niewyraźne.
        Możesz sugerować następujące polecenia, aby poprawić jakość zdjęć (używaj dokładnie takiego formatu):
        - REPAIR nazwa_pliku.png - aby naprawić szumy/glitche
        - DARKEN nazwa_pliku.png - aby przyciemnić zdjęcie
        - BRIGHTEN nazwa_pliku.png - aby rozjaśnić zdjęcie
        
        Przykład poprawnego formatu komend:
        REPAIR IMG_559.PNG
        DARKEN IMG_1410.PNG
        
        Nie używaj nawiasów kwadratowych ani innych znaków specjalnych w komendach.
        
        Twoje zadanie to:
        1. Przeanalizuj wiadomość z API
        2. Wyodrębnij adresy URL zdjęć
        3. Zasugeruj odpowiednie polecenia do poprawy jakości zdjęć, jeśli są potrzebne
        4. Pomóż stworzyć szczegółowy rysopis Barbary, gdy zbierzesz wystarczająco informacji
        
        Odpowiadaj po polsku, ponieważ końcowy rysopis musi być w języku polskim.
        
        Pamiętaj:
        - Analizuj każde zdjęcie pod kątem cech charakterystycznych osoby
        - Zwracaj uwagę na szczegóły twarzy, ubioru i postawy
        - Jeśli zdjęcie jest niewyraźne, sugeruj odpowiednie polecenia do jego poprawy
        - <very important> Jeśli zdjęcie nie przedstawia człowieka może być to artefakt, sugeruj naprawę zdjęcia
        - Jeśli nie masz danych o zdjęciu, spróbuj wykonać jedno z poleceń REPAIR/DARKEN/BRIGHTEN na chybił trafił
        - Gdy masz pewność co do wyglądu Barbary, przygotuj kompletny rysopis
        """

        self.cache_dir = Path(settings.MEDIA_ROOT) / 'cache' / 'barbara'
        self.cache_ttl = timedelta(hours=24)
        
        # Upewnij się, że katalog cache istnieje
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")

        self.timezone = ZoneInfo("UTC")

        # Dodaj śledzenie wykonanych akcji
        self.executed_actions = set()
        self.max_retries_per_action = 2  # Maksymalna liczba prób dla każdej akcji
        self.action_attempts = {}  # Słownik do śledzenia liczby prób dla każdej akcji

        # Dodaj historię konwersacji
        self.conversation_history = []
        self.analysis_history = []

    def _should_execute_action(self, action: str) -> bool:
        """Sprawdź czy akcja powinna zostać wykonana"""
        # Normalizuj akcję (usuń whitespace, zamień na wielkie litery)
        normalized_action = ' '.join(action.split()).upper()
        
        # Jeśli to analiza, zawsze wykonuj
        if normalized_action.startswith('ANALYZE'):
            return True
            
        # Sprawdź liczbę prób dla tej akcji
        attempts = self.action_attempts.get(normalized_action, 0)
        if attempts >= self.max_retries_per_action:
            logger.warning(f"Akcja {normalized_action} osiągnęła maksymalną liczbę prób ({self.max_retries_per_action})")
            return False
            
        return True

    def _update_action_tracking(self, action: str) -> None:
        """Aktualizuj śledzenie wykonanych akcji"""
        normalized_action = ' '.join(action.split()).upper()
        self.executed_actions.add(normalized_action)
        self.action_attempts[normalized_action] = self.action_attempts.get(normalized_action, 0) + 1

    async def start_conversation(self) -> Dict[str, Any]:
        """Start the conversation with the API"""
        try:
            payload = {
                "task": "photos",
                "apikey": self.api_key,
                "answer": "START"
            }
            
            logger.info("Starting new conversation...")
            return await self._send_api_request(payload)
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _send_api_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to the API"""
        try:
            logger.info(f"Sending API request to {self.api_url}")
            logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API error (status {response.status}): {error_text}")
                        raise Exception(f"API error: {error_text}")
                    
                    data = await response.json()
                    logger.info(f"API Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    return data
        except Exception as e:
            logger.error(f"Error sending API request: {str(e)}")
            raise

    def _extract_image_urls(self, message: str) -> List[str]:
        """Extract image URLs from the message"""
        # Najpierw sprawdź, czy w wiadomości jest wspomniane nowe zdjęcie
        new_image_pattern = r'\b([A-Za-z0-9_]+\.(?:jpg|jpeg|gif|png|bmp|webp|PNG|JPG|JPEG))\b'
        new_images = re.findall(new_image_pattern, message)
        
        # Jeśli znaleziono nowe zdjęcia, dodaj do nich pełną ścieżkę URL
        full_urls = []
        for img in new_images:
            if not img.startswith('http'):
                full_url = f"{self.base_url}/dane/barbara/{img}"
                full_urls.append(full_url)
        
        # Znajdź też wszystkie pełne URLe w wiadomości
        url_pattern = r'https?://[^\s<>"]+?\.(?:jpg|jpeg|gif|png|bmp|webp|PNG|JPG|JPEG)\b'
        existing_urls = re.findall(url_pattern, message)
        
        # Połącz obie listy
        all_urls = list(set(full_urls + existing_urls))  # set() usuwa duplikaty
        logger.info(f"Extracted URLs: {all_urls}")
        return all_urls

    async def _get_cached_image(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached image if exists and not expired"""
        try:
            filename = url.split('/')[-1]
            cache_path = self.cache_dir / filename
            
            # Sprawdź czy plik istnieje w cache
            if cache_path.exists():
                # Sprawdź czy cache nie wygasł
                modified_time = timezone.datetime.fromtimestamp(
                    os.path.getmtime(cache_path)
                ).replace(tzinfo=self.timezone)
                age = timezone.now() - modified_time
                
                if age <= self.cache_ttl:
                    # Sprawdź czy mamy zapisaną analizę w bazie danych
                    analysis = await sync_to_async(lambda: FileAnalysis.objects.filter(
                        file_name=filename
                    ).first())()  # Używamy lambda do opakowania całego zapytania
                    
                    if analysis and analysis.content:
                        logger.info(f"Found cached image and analysis for {filename}")
                        return {
                            "url": url,
                            "filename": filename,
                            "description": analysis.content,
                            "cached": True
                        }
                    
                    # Jeśli nie ma analizy, usuń plik z cache
                    logger.info(f"Found cached image but no analysis for {filename}")
                    os.remove(cache_path)
                else:
                    # Cache wygasł, usuń plik
                    logger.info(f"Cache expired for {filename}")
                    os.remove(cache_path)
            
            return None
        except Exception as e:
            logger.error(f"Error checking cache for {url}: {str(e)}")
            return None

    async def _save_to_cache(self, url: str, content: bytes, description: str) -> None:
        """Save image and its analysis to cache"""
        try:
            filename = url.split('/')[-1]
            cache_path = self.cache_dir / filename
            
            # Zapisz plik
            with open(cache_path, 'wb') as f:
                f.write(content)
            
            # Zapisz analizę w bazie danych
            await sync_to_async(FileAnalysis.objects.update_or_create)(
                file_name=filename,
                defaults={
                    'file_type': filename.split('.')[-1].lower(),
                    'content': description,
                    'raw_content': content,
                    'category': 'image'
                }
            )
            
            logger.info(f"Saved {filename} to cache with analysis")
        except Exception as e:
            logger.error(f"Error saving to cache for {url}: {str(e)}")

    async def _process_image(self, url: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Download and process an image"""
        try:
            # Najpierw sprawdź cache
            cached_result = await self._get_cached_image(url)
            if cached_result:
                return cached_result

            logger.info(f"Cache miss for {url}, downloading...")
            
            # Używamy przekazanej sesji
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                content = await response.read()
                
                # Create BytesIO object for processing
                from io import BytesIO
                file_obj = BytesIO(content)
                file_obj.name = url.split('/')[-1]
                
                # Process image using FileAnalyzer
                description = await self.file_analyzer._process_image(file_obj)
                
                if description:
                    # Save to cache
                    await self._save_to_cache(url, content, description)
                    
                    return {
                        "url": url,
                        "filename": file_obj.name,
                        "description": description,
                        "cached": False
                    }
                return None
        except Exception as e:
            logger.error(f"Error processing image {url}: {str(e)}")
            return None

    async def _cleanup_cache(self) -> None:
        """Clean up expired cache files"""
        try:
            current_time = timezone.now()
            for cache_file in self.cache_dir.glob('*'):
                if cache_file.is_file():
                    modified_time = timezone.datetime.fromtimestamp(
                        os.path.getmtime(cache_file)
                    ).replace(tzinfo=self.timezone)
                    age = current_time - modified_time
                    
                    if age > self.cache_ttl:
                        logger.info(f"Removing expired cache file: {cache_file}")
                        os.remove(cache_file)
                        
                        # Usuń też analizę z bazy danych
                        await sync_to_async(FileAnalysis.objects.filter)(
                            file_name=cache_file.name
                        ).delete()
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")

    def _add_to_history(self, role: str, content: str) -> None:
        """Dodaj wiadomość do historii konwersacji"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": timezone.now().isoformat()
        })

    def _add_to_analysis(self, analysis: str) -> None:
        """Dodaj analizę do historii"""
        self.analysis_history.append({
            "content": analysis,
            "timestamp": timezone.now().isoformat()
        })

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process message using LLM and handle any files"""
        try:
            # Dodaj wiadomość od API do historii
            self._add_to_history("api", message)
            
            # Cleanup expired cache files
            await self._cleanup_cache()
            
            logger.info(f"\nProcessing message: {message}")
            
            # Extract image URLs
            image_urls = self._extract_image_urls(message)
            logger.info(f"Found {len(image_urls)} images to process")
            
            # Process each image
            processed_images = []
            async with aiohttp.ClientSession() as session:  # Przenieś sesję na zewnątrz pętli
                for url in image_urls:
                    logger.info(f"Processing image: {url}")
                    try:
                        image_info = await self._process_image(url, session)  # Przekaż sesję
                        if image_info:
                            processed_images.append(image_info)
                    except Exception as e:
                        logger.error(f"Error processing image {url}: {str(e)}")
                        continue

            # Get all cached analyses
            cached_analyses = await self._get_all_cached_analyses()
            
            # Przygotuj historię konwersacji dla LLM
            conversation_summary = "\n\nHistoria konwersacji:\n" + "\n".join([
                f"[{h['timestamp']}] {h['role'].upper()}: {h['content']}"
                for h in self.conversation_history[-5:]  # Pokaż ostatnie 5 wiadomości
            ])
            
            # Przygotuj historię analiz
            analysis_summary = "\n\nHistoria analiz:\n" + "\n".join([
                f"[{h['timestamp']}] {h['content']}"
                for h in self.analysis_history[-5:]  # Pokaż ostatnie 5 analiz
            ])
            
            # Dodaj informację o wykonanych akcjach do promptu
            executed_actions_info = "\n\nWykonane akcje:\n" + "\n".join(
                f"- {action} (próby: {self.action_attempts.get(action, 0)})" 
                for action in sorted(self.executed_actions)
            )
            
            # Get LLM analysis of the message and images
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""
                Przeanalizuj tę wiadomość i zdjęcia:
                
                Wiadomość: {message}
                
                Nowo przetworzone zdjęcia:
                {json.dumps(processed_images, indent=2, ensure_ascii=False)}
                
                Historia przeanalizowanych zdjęć:
                {json.dumps(cached_analyses, indent=2, ensure_ascii=False)}
                {conversation_summary}
                {analysis_summary}
                {executed_actions_info}
                
                Zaproponuj następne kroki:
                1. Jeśli w wiadomości pojawiły się nowe zdjęcia, zaproponuj odpowiednie polecenia (REPAIR/DARKEN/BRIGHTEN)
                2. Jeśli nie ma nowych zdjęć lub akcji do wykonania, przeanalizuj wszystkie dotychczasowe zdjęcia i zaproponuj:
                   - Które zdjęcia wymagają poprawy (REPAIR/DARKEN/BRIGHTEN)
                   - Które zdjęcia są już wystarczająco dobre
                   - Czy mamy wystarczająco informacji do stworzenia rysopisu Barbary
                
                WAŻNE: 
                - Nie proponuj ponownie tych samych akcji dla zdjęć, które już były przetwarzane więcej niż {self.max_retries_per_action} razy.
                - Weź pod uwagę całą historię konwersacji i poprzednie analizy przy podejmowaniu decyzji.
                - Jeśli widzisz, że jakaś akcja była już wykonana i nie przyniosła rezultatu, zaproponuj inną strategię.
                """}
            ]

            logger.info("Sending request to LLM for analysis...")
            response = await self.openai_client.chat_completion(messages=messages)
            
            # Dodaj analizę LLM do historii
            self._add_to_analysis(response.get("content", ""))
            
            # Extract commands and add any new image processing to the queue
            suggested_actions = self._extract_commands(response.get("content", ""))
            
            # Jeśli w wiadomości pojawiło się nowe zdjęcie, dodaj je do analizy
            new_images = [url.split('/')[-1] for url in image_urls if url not in [img['url'] for img in processed_images]]
            if new_images:
                logger.info(f"Found new images to analyze: {new_images}")
                suggested_actions.extend([f"ANALYZE {img}" for img in new_images])
            
            # Jeśli nie ma sugerowanych akcji, ale mamy cached_analyses,
            # dodaj analizę wszystkich zdjęć do kolejki
            if not suggested_actions and cached_analyses:
                logger.info("No suggested actions, analyzing all cached images")
                suggested_actions.extend([f"ANALYZE {img['filename']}" for img in cached_analyses])
            
            result = {
                "status": "success",
                "message": message,
                "processed_images": processed_images,
                "cached_analyses": cached_analyses,
                "llm_analysis": response.get("content", ""),
                "suggested_actions": suggested_actions
            }
            
            logger.info(f"Final result: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _extract_commands(self, llm_response: str) -> List[str]:
        """Extract commands from LLM response"""
        commands = set()  # Użyj set() aby uniknąć duplikatów
        # Zaktualizowany pattern, który obsługuje różne formaty
        command_patterns = [
            # Format: REPAIR filename.png
            r'(REPAIR|DARKEN|BRIGHTEN|ANALYZE)\s+([^\s\[\]]+\.(?:jpg|jpeg|gif|png|bmp|PNG|JPG|JPEG))',
            # Format: REPAIR [filename.png]
            r'(REPAIR|DARKEN|BRIGHTEN|ANALYZE)\s+\[([^\[\]]+\.(?:jpg|jpeg|gif|png|bmp|PNG|JPG|JPEG))\]'
        ]
        
        for pattern in command_patterns:
            matches = re.finditer(pattern, llm_response, re.IGNORECASE)
            for match in matches:
                command = f"{match.group(1)} {match.group(2)}"
                commands.add(command.strip())  # Dodaj do set po usunięciu whitespace
        
        # Walidacja komend przed zwróceniem
        validated_commands = []
        for command in commands:
            # Sprawdź format komendy
            parts = command.split()
            if len(parts) == 2:
                action, filename = parts
                # Upewnij się, że akcja jest poprawna i filename ma rozszerzenie
                if (action.upper() in ['REPAIR', 'DARKEN', 'BRIGHTEN', 'ANALYZE'] and 
                    '.' in filename and 
                    filename.split('.')[-1].upper() in ['JPG', 'JPEG', 'PNG', 'GIF', 'BMP']):
                    
                    normalized_command = f"{action.upper()} {filename.upper()}"
                    
                    # Sprawdź czy akcja powinna być wykonana
                    if self._should_execute_action(normalized_command):
                        validated_commands.append(f"{action.upper()} {filename}")
                    else:
                        logger.warning(f"Pominięto powtórzoną akcję: {normalized_command}")
                else:
                    logger.warning(f"Odrzucono nieprawidłową komendę: {command}")
        
        logger.info(f"Extracted commands: {validated_commands}")
        return validated_commands

    async def send_command(self, command: str) -> Dict[str, Any]:
        """Send a command to the API"""
        try:
            # Dodaj komendę do historii
            self._add_to_history("user", f"Command: {command}")
            
            # Specjalna obsługa komendy ANALYZE_ALL
            if command == "ANALYZE_ALL":
                logger.info("Received ANALYZE_ALL command, performing full reanalysis")
                
                # Pobierz wszystkie analizy
                cached_analyses = await self._get_all_cached_analyses()
                
                # Jeśli to drugie wykonanie ANALYZE_ALL, wygeneruj rysopis
                if len([h for h in self.conversation_history if "ANALYZE_ALL" in h['content']]) >= 1:
                    logger.info("Second ANALYZE_ALL detected, generating final description")
                    
                    # Przygotuj specjalny prompt dla wygenerowania rysopisu
                    messages = [
                        {"role": "system", "content": """
                        Twoim zadaniem jest stworzenie szczegółowego rysopisu Barbary na podstawie wszystkich 
                        dostępnych informacji. Rysopis powinien być w języku polskim i zawierać wszystkie 
                        istotne cechy charakterystyczne, które udało się ustalić na podstawie zdjęć.
                        
                        Format rysopisu powinien być profesjonalny i zawierać:
                        1. Ogólny opis sylwetki
                        2. Szczegóły twarzy i kolor włosów
                        3. Ubiór i charakterystyczne elementy
                        4. Wszelkie inne wyróżniające cechy
                        
                        Skup się tylko na faktach, które można było zaobserwować na zdjęciach.
                        """},
                        {"role": "user", "content": f"""
                        Na podstawie poniższych informacji stwórz rysopis Barbary:
                        
                        Historia przeanalizowanych zdjęć:
                        {json.dumps(cached_analyses, indent=2, ensure_ascii=False)}
                        
                        Historia wykonanych akcji:
                        {json.dumps(list(self.executed_actions), indent=2, ensure_ascii=False)}
                        
                        Historia konwersacji:
                        {json.dumps(self.conversation_history, indent=2, ensure_ascii=False)}
                        """}
                    ]
                    
                    response = await self.openai_client.chat_completion(messages=messages)
                    
                    return {
                        "status": "success",
                        "message": "Generated description",
                        "llm_analysis": response.get("content", ""),
                        "suggested_actions": ["SUBMIT_DESCRIPTION"]
                    }
                
                # Standardowa analiza dla pierwszego ANALYZE_ALL
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"""
                    Przeanalizuj wszystkie dotychczas zebrane informacje:
                    
                    Historia przeanalizowanych zdjęć:
                    {json.dumps(cached_analyses, indent=2, ensure_ascii=False)}
                    
                    Historia wykonanych akcji:
                    {json.dumps(list(self.executed_actions), indent=2, ensure_ascii=False)}
                    
                    Liczba prób dla każdej akcji:
                    {json.dumps(self.action_attempts, indent=2, ensure_ascii=False)}
                    
                    Na podstawie powyższych informacji:
                    1. Oceń które zdjęcia są już wystarczająco dobre
                    2. Które zdjęcia mogą jeszcze wymagać poprawy (ale tylko jeśli nie przekroczono limitu prób)
                    3. Czy mamy wystarczająco informacji do stworzenia rysopisu Barbary
                    
                    Pamiętaj:
                    - Nie proponuj akcji, które już zostały wykonane maksymalną liczbę razy
                    - Jeśli jakaś akcja nie przyniosła rezultatu, zaproponuj inną
                    - Jeśli wszystkie możliwe akcje zostały już wykonane, zaproponuj ANALYZE_ALL
                    """}
                ]
                
                response = await self.openai_client.chat_completion(messages=messages)
                
                return {
                    "status": "success",
                    "message": "Reanalysis completed",
                    "llm_analysis": response.get("content", ""),
                    "suggested_actions": self._extract_commands(response.get("content", ""))
                }
            
            # Standardowa obsługa innych komend
            # Aktualizuj śledzenie akcji przed wykonaniem
            self._update_action_tracking(command)
            
            # Jeśli to komenda ANALYZE, nie wysyłaj jej do API, tylko przetworz zdjęcie
            if command.startswith("ANALYZE"):
                _, image_name = command.split(" ", 1)
                image_url = f"{self.base_url}/dane/barbara/{image_name}"
                logger.info(f"Analyzing new image: {image_url}")
                
                # Zwróć odpowiedź w formacie podobnym do API
                response = {
                    "status": "success",
                    "message": f"Analyzing new image: {image_name}",
                    "image_url": image_url
                }
            else:
                # Dla innych komend, wyślij do API
                payload = {
                    "task": "photos",
                    "apikey": self.api_key,
                    "answer": command
                }
                
                response = await self._send_api_request(payload)
            
            # Dodaj odpowiedź do historii
            if response.get("status") == "success":
                self._add_to_history("api", response.get("message", ""))
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_description(self, description: str) -> Dict[str, Any]:
        """Send the final description to the API"""
        try:
            # Dodaj opis do historii
            self._add_to_history("user", f"Description: {description}")
            
            # Wyślij do API
            payload = {
                "task": "photos",
                "apikey": self.api_key,
                "answer": description
            }
            
            response = await self._send_api_request(payload)
            
            # Dodaj odpowiedź do historii
            if response.get("status") == "success":
                self._add_to_history("api", response.get("message", ""))
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending description: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _get_all_cached_analyses(self) -> List[Dict[str, Any]]:
        """Get all cached image analyses"""
        try:
            # Używamy sync_to_async z lambda do pobrania wszystkich analiz
            analyses_query = await sync_to_async(lambda: list(
                FileAnalysis.objects.filter(category='image')
                .order_by('-updated_at')
                .values('file_name', 'content', 'updated_at')
            ))()
            
            return [{
                "filename": analysis['file_name'],
                "description": analysis['content'],
                "url": f"{self.base_url}/dane/barbara/{analysis['file_name']}",
                "updated_at": analysis['updated_at'].isoformat()
            } for analysis in analyses_query if analysis['content']]
        except Exception as e:
            logger.error(f"Error getting cached analyses: {str(e)}")
            return []

    async def clear_cache(self) -> Dict[str, Any]:
        """Clear all cached analyses and files"""
        try:
            # Usuń wszystkie pliki z cache
            for cache_file in self.cache_dir.glob('*'):
                if cache_file.is_file():
                    logger.info(f"Removing cache file: {cache_file}")
                    os.remove(cache_file)

            # Usuń wszystkie analizy z bazy danych
            await sync_to_async(lambda: FileAnalysis.objects.filter(
                category='image'
            ).delete())()

            # Wyczyść historię
            self.conversation_history = []
            self.analysis_history = []
            self.executed_actions = set()
            self.action_attempts = {}

            logger.info("Cache cleared successfully")
            return {
                "status": "success",
                "message": "Cache and analysis history cleared successfully"
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {"status": "error", "message": str(e)} 