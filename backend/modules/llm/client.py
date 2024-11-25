from typing import Dict, Any, Optional
import openai
from django.conf import settings
from ..base_processor import BaseProcessor

class LLMClient(BaseProcessor):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        openai.api_key = self.api_key
        self.default_model = "gpt-4o-mini"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process LLM requests
        """
        prompt = data.get("prompt")
        model = data.get("model", self.default_model)
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens", 150)

        return await self.generate_response(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150
    ) -> Dict[str, Any]:
        try:
            response = await openai.ChatCompletion.acreate(
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "status": "success",
                "content": response.choices[0].message.content,
                "usage": response.usage
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 