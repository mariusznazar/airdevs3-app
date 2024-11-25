from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from django.conf import settings
from .prompts.manager import PromptManager
from pathlib import Path

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_manager = PromptManager()

    async def chat_completion(
        self,
        messages: list,
        model: str = "gpt-4o",
        temperature: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get completion from ChatGPT
        """
        try:
            print("\n=== OpenAI Request ===")
            print(f"Model: {model}")
            print(f"Temperature: {temperature}")
            print("Messages:")
            for msg in messages:
                print(f"[{msg['role']}]: {msg['content'][:200]}...")  # Pokazujemy pierwsze 200 znaków

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )

            print("\n=== OpenAI Response ===")
            print(f"Raw response object: {response}")
            print(f"First choice content: {response.choices[0].message.content}")

            return {
                "status": "success",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            print(f"\n=== OpenAI Error ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
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
            print(f"Attempting to transcribe file: {audio_file}")
            response = await self.client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )
            print(f"Got response: {response}")
            return {
                "status": "success",
                "text": response.text
            }
        except Exception as e:
            print(f"Error in transcribe_audio: {e}")
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

    def transcribe_audio(self, audio_file_path: str | Path) -> str:
        """
        Transcribes audio file using OpenAI Whisper model.
        
        Args:
            audio_file_path: Path to the audio file
        
        Returns:
            str: Transcribed text from the audio file
        """
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found at: {audio_path}")
        
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.text
        