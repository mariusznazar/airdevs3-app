import aiohttp
import json
from django.conf import settings
from core.models import Document
from asgiref.sync import sync_to_async
from .base_reporter import BaseReporter
from .openai_client import OpenAIClient

class DocumentAnalyzer:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.reporter = BaseReporter()

    async def _get_questions(self) -> str:
        """Fetch questions from central server"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.CENTRAL_URL}/data/{settings.DEFAULT_API_KEY}/arxiv.txt"
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Error fetching questions: {await response.text()}")
                    return await response.text()
        except Exception as e:
            print(f"Error fetching questions: {str(e)}")
            raise

    @sync_to_async
    def _get_document_content(self) -> str:
        """Get document content from database"""
        try:
            # Pobierz najnowszy dokument z tym URL-em
            doc = Document.objects.filter(
                url="https://centrala.ag3nts.org/dane/arxiv-draft.html"
            ).order_by('-created_at').first()
            
            if not doc:
                raise Exception("Document not found in database. Please crawl it first.")
                
            if not doc.processed_content:
                raise Exception("Document has no processed content")
                
            return doc.processed_content
            
        except Document.DoesNotExist:
            raise Exception("Document not found in database. Please crawl it first.")
        except Exception as e:
            print(f"Error getting document: {str(e)}")
            raise

    async def analyze_arxiv_document(self) -> None:
        """Main method to analyze arxiv document and send report"""
        try:
            # 1. Get document content first
            document = await self._get_document_content()
            if not document:
                raise Exception("No document content available")

            # 2. Get questions from central
            questions = await self._get_questions()
            
            # 3. Prepare messages for LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes documents and answers questions about them."
                },
                {
                    "role": "user",
                    "content": f"""
                    Odpowiedz na pytania w oparciu o informacje z załączonego dokumentu.
                    
                    <lista_pytań>
                    {questions}
                    </lista_pytań>
                    
                    <dokument>
                    {document}
                    </dokument>
                    
                    Odpowiedzi prześlij w formacie:
                    {{
                        "ID-pytania-01": "krótka odpowiedź w 1 zdaniu",
                        "ID-pytania-02": "krótka odpowiedź w 1 zdaniu",
                        "ID-pytania-03": "krótka odpowiedź w 1 zdaniu",
                        "ID-pytania-NN": "krótka odpowiedź w 1 zdaniu"
                    }}
                    """
                }
            ]

            # 4. Get response from LLM
            response = await self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o-mini"
            )

            if response.get("status") != "success":
                raise Exception(f"Error from LLM: {response.get('error')}")

            # 5. Parse response to get answers
            try:
                answers = json.loads(response["content"])
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response: {response['content']}")
                raise Exception(f"Invalid JSON in LLM response: {str(e)}")

            # 6. Send report
            await self.reporter.send_report("arxiv", answers)

        except Exception as e:
            print(f"Error in analyze_arxiv_document: {str(e)}")
            raise 