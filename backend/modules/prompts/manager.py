from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class PromptTemplate:
    template: str
    required_vars: list[str]
    
class PromptManager:
    def __init__(self):
        self.prompts = {
            # Text Analysis Prompts
            "text_analyze": PromptTemplate(
                template="Analyze the following text and provide: key topics, sentiment, main ideas, and writing style:\n\n{text}",
                required_vars=["text"]
            ),
            "text_summarize": PromptTemplate(
                template="Provide a concise summary of the following text:\n\n{text}",
                required_vars=["text"]
            ),
            "text_translate": PromptTemplate(
                template="Translate the following text to {target_language}:\n\n{text}",
                required_vars=["text", "target_language"]
            ),
            "text_paraphrase": PromptTemplate(
                template="Paraphrase the following text in a {style} style:\n\n{text}",
                required_vars=["text", "style"]
            ),
            "text_generate": PromptTemplate(
                template="Generate text based on the following prompt. Be creative and engaging:\n\n{prompt}",
                required_vars=["prompt"]
            ),
            
            # Image Analysis Prompts
            "image_analyze": PromptTemplate(
                template="Analyze this image and provide detailed description including: main subjects, colors, composition, mood, and any notable elements. If there's text in the image, include it.\n\n{image_description}",
                required_vars=["image_description"]
            ),
            "image_generate": PromptTemplate(
                template="Create an image based on the following description: {description}. Style: {style}",
                required_vars=["description", "style"]
            ),
            "image_vision_analyze": PromptTemplate(
                template="Analyze this image in detail. Describe: 1) Main subjects 2) Colors and composition 3) Mood and atmosphere 4) Any text visible 5) Notable details",
                required_vars=[]
            ),
            
            # Audio Analysis Prompts
            "audio_transcribe": PromptTemplate(
                template="Transcribe the following audio and maintain proper formatting, punctuation, and speaker identification if multiple speakers are present.",
                required_vars=[]
            ),
            "audio_analyze": PromptTemplate(
                template="Analyze the following audio transcription and provide: main topics, speaker emotions, key points, and overall context:\n\n{transcription}",
                required_vars=["transcription"]
            ),
        }
    
    def get_prompt(self, prompt_key: str, **kwargs) -> str:
        """
        Get formatted prompt by key
        """
        if prompt_key not in self.prompts:
            raise KeyError(f"Prompt key '{prompt_key}' not found")
            
        prompt_template = self.prompts[prompt_key]
        missing_vars = [var for var in prompt_template.required_vars if var not in kwargs]
        
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
            
        return prompt_template.template.format(**kwargs) 