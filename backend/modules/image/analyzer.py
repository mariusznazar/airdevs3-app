from typing import Dict, Any, BinaryIO
import base64
from ..base_processor import BaseProcessor
from ..openai_client import OpenAIClient

class ImageAnalyzer(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.supported_formats = ['jpg', 'jpeg', 'png', 'webp']
        self.max_size = 20 * 1024 * 1024  # 20MB

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze image content using GPT-4 Vision
        """
        image_data = data.get("image")
        operation = data.get("operation", "analyze")
        
        if not self.validate_input(image_data):
            return {"error": "Invalid image data"}

        if operation == "analyze":
            return await self.analyze_image(image_data)
        elif operation == "generate":
            description = data.get("description")
            style = data.get("style", "natural")
            return await self.generate_image(description, style)
            
        return {"error": "Invalid operation"}

    async def analyze_image(self, image_data: BinaryIO) -> Dict[str, Any]:
        """
        Analyze image using GPT-4 Vision
        """
        # Convert image to base64
        image_base64 = base64.b64encode(image_data.read()).decode('utf-8')
        
        return await self.openai_client.chat_completion(
            prompt_key="image_analyze",
            prompt_vars={"image_description": f"data:image/jpeg;base64,{image_base64}"},
            model="gpt-4-vision-preview"
        )

    async def generate_image(self, description: str, style: str) -> Dict[str, Any]:
        """
        Generate image using DALL-E
        """
        return await self.openai_client.generate_image(
            prompt_vars={
                "description": description,
                "style": style
            }
        )

    def validate_input(self, image_data: BinaryIO) -> bool:
        if not image_data:
            return False
            
        # Check file size
        image_data.seek(0, 2)
        size = image_data.tell()
        image_data.seek(0)
        
        return size <= self.max_size 