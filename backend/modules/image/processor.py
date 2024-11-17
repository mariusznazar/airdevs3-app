from typing import Dict, Any, BinaryIO
import base64
from ..base_processor import BaseProcessor
from ..openai_client import OpenAIClient

class ImageProcessor(BaseProcessor):
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.supported_formats = ['jpg', 'jpeg', 'png', 'webp']
        self.max_size = 20 * 1024 * 1024  # 20MB

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image with specified operation
        """
        image_data = data.get("image")
        operation = data.get("operation", "process")
        
        if not self.validate_input(image_data):
            return {"error": "Invalid image data"}

        operations = {
            "process": self.process_image,
            "ocr": self.extract_text,
            "generate": self.generate_image
        }

        if operation not in operations:
            return {"error": "Invalid operation"}

        return await operations[operation](data)

    async def process_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image using GPT-4 Vision
        """
        image_data = data.get("image")
        image_base64 = base64.b64encode(image_data.read()).decode('utf-8')
        
        return await self.openai_client.chat_completion_with_vision(
            image_data=f"data:image/jpeg;base64,{image_base64}",
            prompt_key="image_vision_analyze",
            prompt_vars={}
        )

    async def extract_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from image using GPT-4 Vision
        """
        image_data = data.get("image")
        image_base64 = base64.b64encode(image_data.read()).decode('utf-8')
        
        return await self.openai_client.chat_completion_with_vision(
            image_data=f"data:image/jpeg;base64,{image_base64}",
            prompt_key="image_analyze",
            prompt_vars={"image_description": "Focus on extracting and listing any text visible in this image."}
        )

    async def generate_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate new image using DALL-E
        """
        description = data.get("description")
        style = data.get("style", "natural")
        
        if not description:
            return {"error": "Description is required for image generation"}
            
        return await self.openai_client.generate_image(
            prompt_vars={
                "description": description,
                "style": style
            }
        )

    def validate_input(self, image_data: BinaryIO) -> bool:
        """
        Validate image data
        """
        if not image_data:
            return False
            
        # Check file size
        image_data.seek(0, 2)
        size = image_data.tell()
        image_data.seek(0)
        
        if size > self.max_size:
            return False
            
        return True 