import os
import aiohttp
import asyncio
from io import BytesIO
from typing import Dict, Any, List, Tuple
from urllib.parse import urljoin, urlparse
from django.conf import settings
from core.models import Document, FileAnalysis
from asgiref.sync import sync_to_async
from crawl4ai import AsyncWebCrawler
from .file_analyzer import FileAnalyzer
from django.utils import timezone
from datetime import timedelta
from contextlib import contextmanager
from django.db import models

@contextmanager
def handle_crawl4ai_errors():
    try:
        yield
    except Exception as e:
        if 'filtered_html' in str(e):
            # Jeśli wystąpił błąd z filtered_html, zwracamy pusty string
            print("Warning: Error with markdown generation, falling back to empty string")
            return ""
        raise

class WebCrawlerProcessor:
    def __init__(self):
        self.file_analyzer = FileAnalyzer()
        self.supported_media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.webp'],
            'audio': ['.mp3', '.wav', '.m4a', '.mp4']
        }
        # Czas ważności cache'a (np. 24 godziny)
        self.cache_ttl = timedelta(hours=24)

    @sync_to_async
    def _save_document(self, url: str, original_content: str, processed_content: str = None) -> Document:
        """Save document to database"""
        try:
            # Sprawdź czy treść nie jest komunikatem o błędzie
            error_keywords = ['Error', 'cannot access', 'filtered_html']
            if any(keyword in str(original_content) for keyword in error_keywords):
                print(f"Detected error message in content, skipping save: {original_content}")
                return None
            
            # Upewnij się, że mamy jakąś treść
            if not original_content:
                original_content = ""
            if not processed_content:
                processed_content = original_content

            # Usuń dokumenty z tym samym URL
            Document.objects.filter(url=url).delete()
                
            # Zachowaj oryginalną treść HTML przed konwersją na markdown
            if hasattr(self, '_original_html'):
                original_content = self._original_html
                
            return Document.objects.create(
                url=url,
                original_content=original_content,
                processed_content=processed_content
            )
        except Exception as e:
            print(f"Error saving document: {str(e)}")
            return None

    @sync_to_async
    def _get_document(self, url: str) -> Document:
        """Get document from database if exists and not expired"""
        try:
            doc = Document.objects.get(url=url)
            age = timezone.now() - doc.created_at
            
            if age > self.cache_ttl:
                # Usuń przeterminowany dokument
                doc.delete()
                return None
                
            # Sprawdź czy dokument ma poprawną zawartość
            if not doc.original_content or not doc.processed_content:
                doc.delete()
                return None
                
            return doc
        except Document.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error getting document: {str(e)}")
            return None

    async def _download_media(self, url: str) -> bytes:
        """Download media file from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
        except Exception as e:
            print(f"Error downloading media from {url}: {str(e)}")
            return None

    def _is_supported_media(self, url: str) -> Tuple[bool, str]:
        """Check if URL points to supported media file"""
        lower_url = url.lower()
        
        # Rozszerzamy listę rozpoznawanych formatów audio
        self.supported_media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
            'audio': [
                '.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.oga', 
                '.opus', '.webm', '.aac', '.wma', '.flac'
            ]
        }
        
        # Sprawdzamy rozszerzenia
        for media_type, extensions in self.supported_media_types.items():
            if any(lower_url.endswith(ext) for ext in extensions):
                print(f"Detected {media_type} by extension in URL: {url}")
                return True, media_type
        
        # Sprawdzamy MIME types w URL
        mime_patterns = {
            'audio': ['audio/', 'application/ogg', 'application/x-mpegURL', 'application/octet-stream'],
            'images': ['image/']
        }
        
        for media_type, patterns in mime_patterns.items():
            if any(pattern in lower_url for pattern in patterns):
                print(f"Detected {media_type} by MIME pattern in URL: {url}")
                return True, media_type
        
        # Sprawdzamy dodatkowe wzorce w URL
        if '/audio/' in lower_url or 'sound' in lower_url or 'music' in lower_url:
            print(f"Detected audio by URL pattern: {url}")
            return True, 'audio'
        
        return False, None

    def _get_absolute_url(self, base_url: str, media_url: str) -> str:
        """Convert relative URL to absolute"""
        if media_url.startswith(('http://', 'https://')):
            return media_url
        return urljoin(base_url, media_url)

    async def _process_media_file(self, url: str, media_type: str, content: bytes) -> str:
        """Process media file and return description/transcription"""
        try:
            # Create a file-like object from bytes
            from io import BytesIO
            file_obj = BytesIO(content)
            file_obj.name = os.path.basename(urlparse(url).path)

            if media_type == 'images':
                result = await self.file_analyzer._process_image(file_obj)
                return result if isinstance(result, str) else ""
            elif media_type == 'audio':
                # Zapisz tymczasowo plik audio na dysku
                temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', file_obj.name)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                try:
                    with open(temp_path, 'wb') as f:
                        f.write(content)
                    result = await self.file_analyzer._process_audio(temp_path)
                finally:
                    # Usuń plik tymczasowy
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
                return result.get('text', '') if isinstance(result, dict) else str(result)
                
            return ""
        except Exception as e:
            print(f"Error processing {media_type} file {url}: {str(e)}")
            print(f"Full error details:", e.__class__.__name__, str(e))
            return ""

    @sync_to_async
    def _save_media_analysis(self, url: str, media_url: str, media_type: str, content: bytes, description: str) -> None:
        """Save media analysis to database"""
        try:
            file_name = f"{url}::{os.path.basename(urlparse(media_url).path)}"
            extension = os.path.splitext(urlparse(media_url).path)[1][1:]
            
            # Upewnij się, że mamy opis
            if not description:
                print(f"Warning: No description for {file_name}")
                description = ""
            
            print(f"Saving media analysis for {file_name} with description: {description[:100]}...")
            
            FileAnalysis.objects.update_or_create(
                file_name=file_name,
                defaults={
                    'file_type': extension,
                    'content': description,
                    'raw_content': content,
                    'category': media_type
                }
            )
        except Exception as e:
            print(f"Error saving media analysis: {str(e)}")

    @sync_to_async
    def _cleanup_invalid_documents(self):
        """Clean up invalid documents from database"""
        try:
            # Usuń dokumenty bez zawartości
            Document.objects.filter(
                models.Q(original_content__isnull=True) |
                models.Q(original_content='') |
                models.Q(processed_content__isnull=True) |
                models.Q(processed_content='')
            ).delete()
            
            # Usuń dokumenty zawierające komunikaty o błędach
            Document.objects.filter(
                models.Q(original_content__icontains='Error') |
                models.Q(original_content__icontains='filtered_html') |
                models.Q(processed_content__icontains='Error') |
                models.Q(processed_content__icontains='filtered_html')
            ).delete()
            
            # Usuń przeterminowane dokumenty
            expired_time = timezone.now() - self.cache_ttl
            Document.objects.filter(created_at__lt=expired_time).delete()
        except Exception as e:
            print(f"Error cleaning up documents: {str(e)}")

    @sync_to_async
    def _get_cached_media(self, url: str) -> List[Dict[str, Any]]:
        """Get cached media files for URL"""
        try:
            # Szukaj mediów z prefiksem URL
            media_files = []
            for analysis in FileAnalysis.objects.filter(file_name__startswith=f"{url}::"):
                media_url = analysis.file_name.split("::", 1)[1]
                media_files.append({
                    "url": media_url,
                    "type": analysis.category,
                    "description": analysis.content
                })
            return media_files
        except Exception as e:
            print(f"Error getting cached media: {str(e)}")
            return []

    async def process_url(self, url: str) -> Dict[str, Any]:
        try:
            await self._cleanup_invalid_documents()
            
            # Sprawdź cache dokumentu
            cached_doc = await self._get_document(url)
            cached_media = await self._get_cached_media(url)
            
            if cached_doc:
                if cached_doc.processed_content:
                    # Jeśli mamy już przetworzoną treść, zwróć ją
                    return {
                        "status": "success",
                        "url": url,
                        "content": cached_doc.processed_content,
                        "original_content": cached_doc.original_content,
                        "media_files": cached_media
                    }
                elif cached_doc.original_content:
                    # Jeśli mamy tylko oryginalną treść, przetworzymy ją ponownie
                    print("Found cached original content, processing it...")
                    original_markdown = cached_doc.original_content
                else:
                    # Jeśli nie mamy żadnej treści, usuń dokument
                    await sync_to_async(cached_doc.delete)()
                    original_markdown = None
            else:
                original_markdown = None

            if not original_markdown:
                # Tylko jeśli nie mamy treści w cache, scrapuj stronę
                async with AsyncWebCrawler(
                    verbose=True,
                    browser_type="chromium",
                    headless=True
                ) as crawler:
                    result = await crawler.arun(
                        url=url,
                        process_iframes=True,
                        word_count_threshold=10,
                        exclude_external_links=False,
                        remove_overlay_elements=True,
                        bypass_cache=True,
                        wait_for="img,audio,video,source[type*='audio']",
                        delay_before_return_html=5.0,
                        screenshot=False
                    )

                    if not result.success:
                        return {
                            "status": "error",
                            "message": f"Failed to crawl {url}: {result.error_message}"
                        }

                    # Zachowaj oryginalną treść HTML
                    self._original_html = result.html

                    # Konwertuj HTML na Markdown
                    import html2text
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.body_width = 0
                    
                    original_markdown = h.handle(result.html)

            # Przetwórz markdown (dodaj opisy mediów)
            processed_markdown = original_markdown
            media_files = []

            # Użyj BeautifulSoup do analizy HTML
            from bs4 import BeautifulSoup

            # Przetwórz media tylko jeśli nie mamy ich w cache
            if not cached_media:
                # Analizuj oryginalny HTML, nie markdown
                soup = BeautifulSoup(self._original_html, 'html.parser')
                
                # Znajdź i przetwórz obrazy
                images = soup.find_all('img')
                for img in images:
                    src = img.get('src')
                    if src:
                        media_url = self._get_absolute_url(url, src)
                        print(f"Found image: {media_url}")
                        is_supported, detected_type = self._is_supported_media(media_url)
                        if is_supported:
                            media_content = await self._download_media(media_url)
                            if media_content:
                                description = await self._process_media_file(
                                    media_url, 
                                    detected_type, 
                                    media_content
                                )
                                media_files.append({
                                    "url": media_url,
                                    "type": "images",
                                    "description": description
                                })
                                # Dodaj opis do markdown - szukaj różnych wariantów linków
                                patterns = [
                                    f"![]({src})",
                                    f"![]({media_url})",
                                    f"![{src}]({src})",
                                    f"![{media_url}]({media_url})"
                                ]
                                img_with_desc = f"![{description}]({media_url})"
                                
                                for pattern in patterns:
                                    processed_markdown = processed_markdown.replace(pattern, img_with_desc)

                # Znajdź i przetwórz pliki audio
                audio_elements = soup.find_all(['audio', 'source'])
                for audio in audio_elements:
                    src = audio.get('src')
                    if src:
                        media_url = self._get_absolute_url(url, src)
                        print(f"Found audio: {media_url}")
                        is_supported, detected_type = self._is_supported_media(media_url)
                        if is_supported:
                            media_content = await self._download_media(media_url)
                            if media_content:
                                description = await self._process_media_file(
                                    media_url, 
                                    detected_type, 
                                    media_content
                                )
                                media_files.append({
                                    "url": media_url,
                                    "type": "audio",
                                    "description": description
                                })
                                
                                # Przygotuj nowy format audio z transkrypcją
                                audio_with_desc = (
                                    f"\n\n**Audio Transcription:**\n\n"
                                    f"{description}\n\n"
                                    f"[🔊 Listen to original audio]({media_url})\n\n"
                                )
                                
                                # Znajdź i zamień wszystkie możliwe warianty audio w markdown
                                patterns = [
                                    f'<audio.*?src="{src}".*?</audio>',
                                    f'<audio.*?src="{media_url}".*?</audio>',
                                    f'<source.*?src="{src}".*?>',
                                    f'<source.*?src="{media_url}".*?>',
                                    f'[{os.path.basename(src)}]({src})',
                                    f'[{os.path.basename(media_url)}]({media_url})',
                                    f'[Audio]({src})',
                                    f'[Audio]({media_url})'
                                ]
                                
                                for pattern in patterns:
                                    if pattern in processed_markdown:
                                        processed_markdown = processed_markdown.replace(pattern, audio_with_desc)
            else:
                # Użyj mediów z cache, ale sprawdź czy mają opisy
                media_files = []
                for cached_media in cached_media:
                    base_name = os.path.basename(cached_media['url'])
                    
                    try:
                        # Najpierw spróbuj znaleźć plik z pełną ścieżką
                        file_analysis = await sync_to_async(FileAnalysis.objects.get)(
                            file_name=f"{url}::{base_name}"
                        )
                    except FileAnalysis.DoesNotExist:
                        try:
                            # Jeśli nie znaleziono, spróbuj samą nazwę pliku
                            file_analysis = await sync_to_async(FileAnalysis.objects.get)(
                                file_name=base_name
                            )
                        except FileAnalysis.DoesNotExist:
                            print(f"Warning: No analysis found for {base_name}")
                            continue
                    
                    # Jeśli content jest pusty, wygeneruj nowy opis
                    if not file_analysis.content and file_analysis.raw_content:
                        print(f"Regenerating description for {base_name}")
                        
                        if cached_media['type'] == 'images':
                            # Utwórz BytesIO z raw_content dla obrazów
                            file_obj = BytesIO(file_analysis.raw_content)
                            file_obj.name = base_name
                            description = await self.file_analyzer._process_image(file_obj)
                        elif cached_media['type'] == 'audio':
                            # Zapisz tymczasowo plik audio
                            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', base_name)
                            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                            
                            try:
                                with open(temp_path, 'wb') as f:
                                    f.write(file_analysis.raw_content)
                                description = await self.file_analyzer._process_audio(temp_path)
                            finally:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                        
                        # Zaktualizuj opis w bazie danych
                        file_analysis.content = description
                        await sync_to_async(file_analysis.save)()
                        cached_media['description'] = description
                    else:
                        # Użyj istniejącego opisu
                        cached_media['description'] = file_analysis.content
                        
                    media_files.append(cached_media)
                    
                    # Dodaj opisy do processed_markdown
                    if cached_media['type'] == 'images':
                        # Wzorce dla obrazów w markdown
                        patterns = [
                            f"![](i/{base_name})",
                            f"![{base_name}](i/{base_name})",
                            f"![]({base_name})",
                            f"![{base_name}]({base_name})"
                        ]
                        img_with_desc = f"![{cached_media['description']}](i/{base_name})"
                        
                        for pattern in patterns:
                            if pattern in processed_markdown:
                                processed_markdown = processed_markdown.replace(pattern, img_with_desc)
                                break
                                
                    elif cached_media['type'] == 'audio':
                        # Wzorce dla audio w markdown
                        patterns = [
                            f"[{base_name}](i/{base_name})",
                            f"[Audio](i/{base_name})",
                            f"[🔊](i/{base_name})",
                            f"[{base_name}]({base_name})",
                            f"[Audio]({base_name})",
                            f"[🔊]({base_name})"
                        ]
                        
                        audio_with_desc = (
                            f"\n\n**Audio Transcription:**\n\n"
                            f"{cached_media['description']}\n\n"
                            f"[🔊 Listen to original audio](i/{base_name})\n\n"
                        )
                        
                        for pattern in patterns:
                            if pattern in processed_markdown:
                                processed_markdown = processed_markdown.replace(pattern, audio_with_desc)
                                break

            # Zapisz dokument
            await self._save_document(url, original_markdown, processed_markdown)

            return {
                "status": "success",
                "url": url,
                "content": processed_markdown,
                "original_content": original_markdown,
                "media_files": media_files
            }

        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
            print(f"Full error details:", e.__class__.__name__, str(e))
            return {
                "status": "error",
                "message": f"Error processing {url}: {str(e)}"
            }