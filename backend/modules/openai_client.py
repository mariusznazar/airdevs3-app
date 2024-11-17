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
        messages: list,
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Get completion from ChatGPT with raw messages
        """
        try:
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
        model: str = "gpt-4-vision-preview"
    ) -> Dict[str, Any]:
        """
        Get completion from GPT-4 Vision
        """
        try:
            prompt = self.prompt_manager.get_prompt(prompt_key, **prompt_vars)
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": image_data}
                        ]
                    }
                ],
                max_tokens=500
            )
            return {
                "status": "success",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def process_universal(
        self,
        messages: list,
        files: Dict[str, Any] = None,
        model: str = "gpt-4-0125-preview",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Process request with GPT-4 Turbo model that can handle multiple input types
        """
        try:
            # Handle audio transcription first if audio file is present
            if files and 'audio' in files:
                transcription = await self.transcribe_audio(
                    files['audio'],
                    model="whisper-1"
                )
                if transcription["status"] == "error":
                    return transcription
                
                # Add transcription to messages
                messages.append({
                    "role": "user",
                    "content": f"Audio transcription: {transcription['text']}"
                })

            # Handle image if present
            if files and 'image' in files:
                # Convert messages to include image data
                for msg in messages:
                    if msg["role"] == "user" and isinstance(msg["content"], list):
                        for content in msg["content"]:
                            if content.get("type") == "image_url":
                                # Process image data here
                                pass

            # Use GPT-4 Turbo for the final processing
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