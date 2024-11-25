import os
from typing import Dict, List, Optional
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from asgiref.sync import sync_to_async
from .openai_client import OpenAIClient
from core.models import FileAnalysis, TagList
from .base_reporter import BaseReporter

class DocumentTagger:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.reporter = BaseReporter()
        self.data_dir = os.path.join(settings.BASE_DIR, 'data', 'raw', 'pliki_z_fabryki')
        self.facts_dir = os.path.join(self.data_dir, 'facts')
        self.cache_ttl = timedelta(hours=24)

    async def process(self) -> Dict[str, str]:
        """Main processing method"""
        try:
            # Step 1: Index all files
            print("Step 1: Indexing files...")
            await self._index_files()

            # Step 2: Generate or get cached tags
            print("Step 2: Getting tags...")
            tags = await self._get_or_generate_tags()

            # Step 3: Tag files and prepare report
            print("Step 3: Tagging files...")
            tagged_files = await self._tag_files(tags)

            # Step 4: Send report
            print("Step 4: Sending report...")
            await self._send_report(tagged_files)

            return tagged_files
        except Exception as e:
            print(f"Error in process: {str(e)}")
            raise

    @sync_to_async
    def _get_cached_tags(self) -> Optional[List[str]]:
        """Get cached tags if they exist and are not expired"""
        try:
            tag_list = TagList.objects.latest('created_at')
            age = timezone.now() - tag_list.updated_at
            
            if age > self.cache_ttl:
                return None
                
            return tag_list.tags.split(',')
        except TagList.DoesNotExist:
            return None

    @sync_to_async
    def _save_tags(self, tags: List[str]) -> None:
        """Save tags to database"""
        TagList.objects.create(tags=','.join(tags))

    async def _get_or_generate_tags(self) -> List[str]:
        """Get cached tags or generate new ones"""
        cached_tags = await self._get_cached_tags()
        if cached_tags:
            return cached_tags

        # Prepare files content for tag generation
        files_content = []
        for root in [self.data_dir, self.facts_dir]:
            if os.path.exists(root):
                for filename in os.listdir(root):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(root, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                folder = 'facts' if root == self.facts_dir else 'pliki_z_fabryki'
                                files_content.append(f"{filename} - {content} - folder {folder}")
                        except Exception as e:
                            print(f"Error reading file {filename}: {str(e)}")

        system_prompt = """
        You are a document tagging expert. Your task is to analyze the provided files and generate a list of relevant tags.
        The tags should:
        1. Be specific and meaningful
        2. Reflect the content, location, and relationships between files
        3. Be useful for categorizing and searching documents
        4. Be returned as a simple comma-separated list
        Tags should be words in polish language in form of mianownik.
        """

        user_prompt = f"""
        Based on the attached files, generate a list of tags that can be used to mark these files. Consider file locations, names, content, and potential relationships.
        <files>
        {chr(10).join(files_content)}
        </files>
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.openai_client.chat_completion(
            messages=messages,
            temperature=0.3
        )

        if response.get("status") == "success":
            tags = [tag.strip() for tag in response['content'].split(',')]
            await self._save_tags(tags)
            return tags
        
        raise Exception("Failed to generate tags")

    async def _index_files(self) -> None:
        """Index all files from both main and facts directories"""
        for root in [self.data_dir, self.facts_dir]:
            if not os.path.exists(root):
                print(f"Directory not found: {root}")
                continue

            for filename in os.listdir(root):
                if not filename.endswith('.txt'):
                    continue

                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        await self._save_analysis(filename, 'txt', content)
                except Exception as e:
                    print(f"Error indexing file {filename}: {str(e)}")

    @sync_to_async
    def _save_analysis(self, file_name: str, file_type: str, content: str) -> None:
        """Save file analysis to database"""
        FileAnalysis.objects.update_or_create(
            file_name=file_name,
            defaults={
                'file_type': file_type,
                'content': content
            }
        )

    async def _tag_files(self, tags: List[str]) -> Dict[str, str]:
        """Tag files and return mapping of filenames to their tags"""
        result = {}
        
        for filename in os.listdir(self.data_dir):
            if not filename.endswith('.txt'):
                continue

            # Check cache first
            cached = await self._get_cached_analysis(filename)
            if cached and cached.keywords:
                result[filename] = cached.keywords
                continue

            # Get file content
            try:
                with open(os.path.join(self.data_dir, filename), 'r', encoding='utf-8') as f:
                    content = f.read()

                system_prompt = f"""
                You are a document tagging expert. You have a predefined list of tags:
                {', '.join(tags)}
                
                Your task is to assign the most relevant tags to the given document.
                Return only a comma-separated list of assigned tags. Do not add any tags that are not in the provided list. Do not add any additional text.
                example: "tag1,tag2,tag3"
                """

                user_prompt = f"""
                Please analyze this document and assign appropriate tags from the provided list:
                <document>
                {content}
                </document>
                """

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                response = await self.openai_client.chat_completion(
                    messages=messages,
                    temperature=0.3
                )

                if response.get("status") == "success":
                    file_tags = response['content'].strip()
                    await self._save_file_tags(filename, file_tags)
                    result[filename] = file_tags

            except Exception as e:
                print(f"Error tagging file {filename}: {str(e)}")

        return result

    @sync_to_async
    def _get_cached_analysis(self, file_name: str) -> Optional[FileAnalysis]:
        """Get cached file analysis if exists and not expired"""
        try:
            cached = FileAnalysis.objects.get(file_name=file_name)
            age = timezone.now() - cached.updated_at
            
            if age > self.cache_ttl:
                return None
                
            return cached
        except FileAnalysis.DoesNotExist:
            return None

    @sync_to_async
    def _save_file_tags(self, file_name: str, tags: str) -> None:
        """Save file tags to database"""
        FileAnalysis.objects.filter(file_name=file_name).update(keywords=tags)

    async def _send_report(self, tagged_files: Dict[str, str]) -> None:
        """Send report to central server"""
        await self.reporter.send_report("dokumenty", tagged_files) 