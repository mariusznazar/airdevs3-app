from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from django.conf import settings
from .prompts.manager import PromptManager

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_manager = PromptManager()

    async def chat_completion(
        self,
        prompt_key: str = None,
        prompt_vars: Dict[str, Any] = None,
        messages: list = None,
        model: str = "gpt-4o",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Get completion from ChatGPT with either raw messages or prompt template
        """
        try:
            if messages is None and prompt_key:
                prompt = self.prompt_manager.get_prompt(prompt_key, **prompt_vars)
                messages = [{"role": "user", "content": prompt}]
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return {
                "status": "success",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def generate_image(
        self,
        prompt_vars: Dict[str, Any],
        size: str = "1024x1024",
        quality: str = "standard",
        model: str = "dall-e-3"
    ) -> Dict[str, Any]:
        """
        Generate image using DALL-E
        """
        try:
            prompt = self.prompt_manager.get_prompt("image_generate", **prompt_vars)
            response = await self.client.images.generate(
                prompt=prompt,
                size=size,
                quality=quality,
                model=model,
                n=1
            )
            return {
                "status": "success",
                "url": response.data[0].url
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def transcribe_audio(
        self,
        audio_file,
        model: str = "whisper-1"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        """
        try:
            response = await self.client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )
            return {
                "status": "success",
                "text": response.text
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def chat_completion_with_vision(
        self,
        image_data: str,
        prompt_key: str,
        prompt_vars: Dict[str, Any],
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Get completion from GPT-4 Vision"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Opisz co widzisz na tym zdjęciu."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data}
                        }
                    ]
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=500
            )
            
            return {
                "status": "success",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        