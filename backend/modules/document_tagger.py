import os
from typing import Dict, List, Optional, Any
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from asgiref.sync import sync_to_async
from .openai_client import OpenAIClient
from core.models import FileAnalysis, TagList
from .base_reporter import BaseReporter
import json

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
    def _get_cached_tags(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached tags if they exist and are not expired"""
        try:
            tag_list = TagList.objects.latest('created_at')
            age = timezone.now() - tag_list.updated_at
            
            # Sprawdzamy czy cache nie wygasł i czy tagi nie są puste
            if age > self.cache_ttl or not tag_list.tags:
                return None
                
            return tag_list.tags  # Teraz tags to już jest JSON
        except TagList.DoesNotExist:
            return None

    @sync_to_async
    def _save_tags(self, tags: List[Dict[str, Any]]) -> None:
        """Save tags to database"""
        TagList.objects.create(tags=tags)  # Zapisujemy bezpośrednio jako JSON

    async def _get_or_generate_tags(self) -> List[Dict[str, Any]]:
        """Get cached tags or generate new ones"""
        cached_tags = await self._get_cached_tags()
        if cached_tags:
            return cached_tags

        all_tags = set()  # Używamy set() do przechowywania unikalnych tagów
        
        # Iterujemy po każdym pliku osobno
        for root in [self.data_dir, self.facts_dir]:
            if not os.path.exists(root):
                continue

            for filename in os.listdir(root):
                if not filename.endswith('.txt'):
                    continue

                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        folder = 'facts' if root == self.facts_dir else 'pliki_z_fabryki'
                        
                        print(f"\n=== Analyzing file for tags: {filename} ===")
                        
                        system_prompt = """
                        <prompt_objective>
                        Generate a comprehensive JSON list of tags based on the provided document content. Tags must be meaningful, specific, and useful for categorization, searchability, and understanding document content.
                        </prompt_objective>

                        <prompt_rules>
                        - All tags must:
                        - Be in Polish, in the nominative case (base form, singular or plural as appropriate).
                        - Include one- or two-word phrases, such as "nauczyciel angielskiego," "krytyk reżimu," or "programista."
                        - Be specific, meaningful, and useful for categorization, searching, or understanding document content.
                        - **Generate at least 15 unique tags per document.** If this number is not reached, analyze the document again to find additional relevant tags.

                        <prompt_tags>
                        Generate tags for:
                        - **Individuals**: Include names and all roles, professions, or notable traits mentioned in the document (e.g., "nauczyciel angielskiego," "programista").
                        - **Animals**: Include species, types, or references to animals (e.g., "gepard," "zwierzyna leśna").
                        - **Technicals**: Include names and topics related to technology, science, or engineering (e.g., "dron," "alarm", "analiza wizualna", "sensory").
                        - **Places**: Identify locations described in the document.
                        - **Events and activities**: Mention any significant actions, processes, or occurrences (e.g., "ucieczka," "aresztowanie").
                        - **Concepts**: Extract abstract ideas, themes, or trends described in the document (e.g., "rząd robotów," "sztuczna inteligencja").
                        - **Relationships**: Recognize relationships or affiliations (e.g., "krytyk reżimu," "członek opozycji").
                        </prompt_tags>

                        <prompt_logic>
                        - Ensure all notable elements in the document are tagged.
                        - For each document:
                        - Generate as many unique tags as possible, prioritizing relevance and specificity.
                        - Ensure at least 10 unique tags are generated, even for shorter or simpler documents.
                        - If a tag has synonyms or alternative names in the document, create separate tags for each (e.g., "dron" and "bezzałogowiec").
                        - Tags must have distinct contexts explaining their relevance in the document.
                        - Avoid over-selecting or limiting tags to only the most obvious elements.
                        </prompt_logic>

                        <prompt_examples>
                        <example>
                        <document>
                        Aleksander Ragowski pracował jako nauczyciel języka angielskiego, przez wiele lat prowadząc zajęcia w Szkole Podstawowej nr 9 w Grudziądzu. Był cenionym nauczycielem, znanym z kreatywnych metod nauczania i zaangażowania w życie społeczności szkolnej. Jednak w obliczu postępującej automatyzacji i wzrostu wpływu tzw. "rządu robotów", Ragorski stał się jednym z najaktywniejszych krytyków nowego reżimu.
                        </document>
                        <output>
                        [
                            {
                                "name": "Aleksander Ragowski",
                                "context": "Mentioned as the main subject of the document, described as a teacher and critic of the regime (category: person)."
                            },
                            {
                                "name": "nauczyciel angielskiego",
                                "context": "Described as his primary profession, teaching English for many years (category: role)."
                            },
                            {
                                "name": "krytyk reżimu",
                                "context": "Referenced as his role in opposing the robotic regime (category: role)."
                            },
                            {
                                "name": "Szkoła Podstawowa nr 9",
                                "context": "Identified as his workplace located in Grudziądz (category: place)."
                            },
                            {
                                "name": "Grudziądz",
                                "context": "Mentioned as the city where he worked as a teacher (category: place)."
                            },
                            {
                                "name": "rząd robotów",
                                "context": "Described as the regime opposed by Aleksander Ragowski (category: concept)."
                            },
                            {
                                "name": "automatyzacja",
                                "context": "Referenced as a key societal issue in the document (category: concept)."
                            },
                            {
                                "name": "metody nauczania",
                                "context": "Highlighted as creative teaching methods used by Aleksander Ragowski (category: concept)."
                            },
                            {
                                "name": "społeczność szkolna",
                                "context": "Mentioned as the community where Aleksander Ragowski was actively engaged (category: concept)."
                            },
                            {
                                "name": "zaangażowanie",
                                "context": "Described as a key characteristic of Aleksander Ragowski in his teaching career (category: trait)."
                            }
                        ]
                        </output>
                        </example>
                        </prompt_examples>

                        """

                        user_prompt = f"""
                        Please analyze this document and generate relevant tags:
                        <document>
                        {filename} - {content} - folder {folder}
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
                            try:
                                # Czyścimy odpowiedź z formatowania Markdown
                                content = response['content']
                                if content.startswith('```'):
                                    content = '\n'.join(content.split('\n')[1:-1])
                                    if content.startswith('json'):
                                        content = '\n'.join(content.split('\n')[1:])
                                
                                file_tags = json.loads(content)
                                
                                # Dodajemy tagi do zbioru wszystkich tagów
                                # Używamy tuple() do konwersji słownika na niemutowalny typ
                                for tag in file_tags:
                                    all_tags.add(json.dumps(tag, sort_keys=True))
                                
                                print(f"Generated {len(file_tags)} tags from {filename}")
                                
                            except json.JSONDecodeError as e:
                                print(f"Error parsing tags JSON for {filename}: {e}")
                                print(f"Raw response: {response['content']}")
                        else:
                            print(f"Error generating tags for {filename}: {response.get('error')}")
                            
                except Exception as e:
                    print(f"Error processing file {filename}: {str(e)}")

        # Konwertujemy z powrotem do listy słowników
        final_tags = [json.loads(tag) for tag in all_tags]
        print(f"\nTotal unique tags generated: {len(final_tags)}")
        
        # Zapisujemy kompletną listę tagów
        await self._save_tags(final_tags)
        return final_tags

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

    async def _tag_files(self, tags: List[Dict[str, Any]]) -> Dict[str, str]:
        """Tag files and return mapping of filenames to their comma-separated tags"""
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

                print(f"\n=== Processing file: {filename} ===")

                system_prompt = """
                You are a document tagging expert. Your task is to analyze a provided document and assign the most relevant tags from the predefined list.

                <prompt_objective>
                Your sole purpose is to assign tags from the provided list to a given document. Use only the tags explicitly provided in the list, ensuring the following:
                1. If a tag from the list accurately describes the content of the document, include it in the output.
                2. If no tags from the list apply to the document, return an empty string (`""`).
                3. The output must be a single, comma-separated list of tags without any additional text or formatting.
                4. Do not add, create, or infer tags outside the predefined list.
                </prompt_objective>

                <prompt_rules>
                - Only use tags from the provided list.
                - Format the output as a comma-separated string, e.g., `tag1,tag2,tag3`.
                - Return an empty string (`""`) if no tags match the document.
                - Avoid repetition of tags in the output.
                - Do not include any additional text or formatting outside the required output format.
                </prompt_rules>

                <examples>
                1. **USER**: Please analyze this document and assign appropriate tags from the provided list: `marketing, social media, content creation, SEO`  
                `<document>This document is about effective SEO techniques and best practices.</document>`  
                **AI**: `SEO`

                2. **USER**: Please analyze this document and assign appropriate tags from the provided list: `marketing, social media, content creation, SEO`  
                `<document>This document is about gardening tips and techniques.</document>`  
                **AI**: `""`

                3. **USER**: Please analyze this document and assign appropriate tags from the provided list: `marketing, social media, content creation, SEO`  
                `<document>This document covers marketing, social media strategies, content creation, and SEO all at once.</document>`  
                **AI**: `marketing,social media,content creation,SEO`
                </examples>

                """

                user_prompt = f"""
                Please analyze this document and list appropriate tag names from these tags: {json.dumps(tags, ensure_ascii=False)}

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
                    file_tags = response['content'].strip().strip('"').strip("'")
                    if file_tags == '""' or file_tags == "''":
                        file_tags = ""
                    
                    print(f"Generated tags: {file_tags}")
                    
                    await self._save_file_tags(filename, file_tags)
                    result[filename] = file_tags

            except Exception as e:
                print(f"Error tagging file {filename}: {str(e)}")
                result[filename] = ""

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
        # Upewniamy się, że zapisujemy czysty string bez escapowanych cudzysłowów
        tags = tags.strip().strip('"').strip("'")
        FileAnalysis.objects.filter(file_name=file_name).update(keywords=tags)

    async def _send_report(self, tagged_files: Dict[str, str]) -> None:
        """Send report to central server"""
        await self.reporter.send_report("dokumenty", tagged_files) 

    @sync_to_async
    def _clear_tags(self) -> None:
        """Clear all tags from database"""
        TagList.objects.all().delete()
        FileAnalysis.objects.all().update(keywords='') 