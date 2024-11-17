from typing import Dict, Any
from ..base_processor import BaseProcessor
from ..openai_client import OpenAIClient

class TextGenerator(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text generation requests
        """
        text = data.get("text")
        operation = data.get("operation", "generate")
        
        if not self.validate_input(text):
            return {"error": "Invalid text input"}

        operations = {
            "generate": self.generate_text,
            "translate": self.translate_text,
            "paraphrase": self.paraphrase_text
        }

        if operation not in operations:
            return {"error": "Invalid operation"}

        return await operations[operation](data)

    async def generate_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate text based on prompt
        """
        prompt = data.get("prompt", "")
        temperature = data.get("temperature", 0.7)
        
        return await self.openai_client.chat_completion(
            prompt_key="text_generate",
            prompt_vars={"prompt": prompt},
            temperature=temperature
        )

    async def translate_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate text to target language
        """
        text = data.get("text")
        target_language = data.get("target_language", "pl")
        
        return await self.openai_client.chat_completion(
            prompt_key="text_translate",
            prompt_vars={
                "text": text,
                "target_language": target_language
            }
        )

    async def paraphrase_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Paraphrase text in specified style
        """
        text = data.get("text")
        style = data.get("style", "formal")
        
        return await self.openai_client.chat_completion(
            prompt_key="text_paraphrase",
            prompt_vars={
                "text": text,
                "style": style
            }
        )

    def validate_input(self, text: str) -> bool:
        """
        Validate text input
        """
        return bool(text and isinstance(text, str)) 