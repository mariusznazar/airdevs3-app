from typing import Dict, Any, BinaryIO
from ..base_processor import BaseProcessor
from ..openai_client import OpenAIClient

class AudioProcessor(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.supported_formats = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
        self.max_size = 25 * 1024 * 1024  # 25MB (OpenAI's limit)

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process audio data with specified operation
        """
        audio_data = data.get("audio")
        operation = data.get("operation", "transcribe")
        
        if not self.validate_input(audio_data):
            return {"error": "Invalid audio data"}

        if operation == "transcribe":
            result = await self.transcribe_audio(audio_data)
            if result["status"] == "success":
                # Analyze the transcription
                analysis = await self.analyze_transcription(result["text"])
                result["analysis"] = analysis.get("content", "")
            return result
            
        return {"error": "Invalid operation"}

    async def transcribe_audio(self, audio_file: BinaryIO) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI's Whisper
        """
        return await self.openai_client.transcribe_audio(audio_file)

    async def analyze_transcription(self, transcription: str) -> Dict[str, Any]:
        """
        Analyze transcribed text using GPT
        """
        return await self.openai_client.chat_completion(
            prompt_key="audio_analyze",
            prompt_vars={"transcription": transcription}
        )

    def validate_input(self, audio_data: BinaryIO) -> bool:
        """
        Validate audio data
        """
        if not audio_data:
            return False
            
        # Check file size
        audio_data.seek(0, 2)  # Seek to end
        size = audio_data.tell()
        audio_data.seek(0)  # Reset position
        
        if size > self.max_size:
            return False
            
        return True 