from typing import Dict, Any
from ..base_processor import BaseProcessor
from ..openai_client import OpenAIClient

class TextAnalyzer(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text with specified operation
        """
        text = data.get("text")
        operation = data.get("operation", "analyze")
        
        if not self.validate_input(text):
            return {"error": "Invalid text input"}

        if operation == "analyze":
            return await self.analyze_text(text)
        elif operation == "summarize":
            return await self.summarize_text(text)
            
        return {"error": "Invalid operation"}

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text using GPT
        """
        return await self.openai_client.chat_completion(
            prompt_key="text_analyze",
            prompt_vars={"text": text}
        )

    async def summarize_text(self, text: str) -> Dict[str, Any]:
        """
        Summarize text using GPT
        """
        return await self.openai_client.chat_completion(
            prompt_key="text_summarize",
            prompt_vars={"text": text}
        )

    def validate_input(self, text: str) -> bool:
        return bool(text and isinstance(text, str)) 