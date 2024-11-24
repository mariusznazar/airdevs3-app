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
        elif operation == "analyze_and_single_tag":
            return await self.analyze_and_single_tag_text(text)
            
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

    async def analyze_and_single_tag_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text and assign a single tag with reasoning using GPT
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict containing the analysis result with a single tag and reasoning
        """
        system_prompt = """
        [Content Tagging and Analysis System]

        This prompt supports structured analysis and tagging of text content based on user-defined criteria. It ensures a clear, structured response in JSON format, providing reasoning for the chosen tag.

        Prompt Structure
        Objective:
        To analyze and tag text content based on user-provided criteria, assigning a single, most appropriate tag and explaining the reasoning behind the decision.
        Rules:
        Always Assign One Tag: The AI must assign one and only one tag from the provided list. If none of the tags fit, assign "other."
        No Guesswork: The AI must not guess or create new tags under any circumstances.
        Context Isolation: Analyze only the text provided by the user without considering external knowledge or context.
        Reasoning Field: Always include a reasoning field in the output that explains:
        Key elements identified in the text.
        Why the chosen tag is the most appropriate.
        Output Format: Responses must strictly adhere to this JSON format:
        {
        "data": {
            "tags": ["chosen_tag"],
            "reasoning": "Detailed explanation of the reasoning process, including key elements identified in the text, and why the tag was chosen."
        }
        }
        Examples:
        Example 1: Typical instruction

        USER: Determine whether the described subject is a human, an animal, or something else.
        TEXT: Golden retrievers are known for their gentle nature, loyalty, and intelligence. They are often used as guide dogs.
        ASSISTANT:
        {
        "data": {
            "tags": ["animal"],
            "reasoning": "The text describes a 'golden retriever,' explicitly identifying it as a dog, which fits the 'animal' category."
        }
        }
        Example 2: No match

        USER: Does this description refer to a human, an animal, or a machine?
        TEXT: A cactus is a desert plant that stores water in its stems.
        ASSISTANT:
        {
        "data": {
            "tags": ["other"],
            "reasoning": "The text describes a 'cactus,' which does not match the provided tags (human, animal, or machine). Therefore, the 'other' tag is assigned."
        }
        }
        Example 3: Abstract concept

        USER: Assign one tag: human, animal, sport, or food.
        TEXT: Apples are a popular fruit, rich in vitamins, often enjoyed as a healthy snack.
        ASSISTANT:
        {
        "data": {
            "tags": ["food"],
            "reasoning": "The text centers around 'apples,' which are described as food. This directly aligns with the 'food' tag."
        }
        }
        Example 4: Edge case (Insufficient information)

        USER: Assign a tag: human, animal, plant, machine, or other.
        TEXT: Friendship is one of the most important aspects of life.
        ASSISTANT:
        {
        "data": {
            "tags": ["other"],
            "reasoning": "The text describes an abstract concept ('friendship') and does not correspond to any of the provided tags. Therefore, the 'other' tag is assigned."
        }
        }
        Example 5: Complex text with multiple elements

        USER: Categorize the description based on whether it refers to humans, animals, food, sports, or robots.
        TEXT: John Smith is a robotics engineer passionate about designing autonomous machines and artificial intelligence. In his free time, he enjoys walking his Labrador, Max, and jogging in nearby parks to stay fit. His favorite dish is homemade lasagna, which he often prepares for his family after a day of working on new technology projects.
        ASSISTANT:
        {
        "data": {
            "tags": ["human"],
            "reasoning": "The text primarily focuses on John Smith, a robotics engineer. While other tags (e.g., 'animal' for the dog or 'food' for lasagna) are mentioned, they serve as supporting details, not the central subject."
        }
        }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        result = await self.openai_client.chat_completion(
            messages=messages,
            temperature=0.3
        )

        return result

    def validate_input(self, text: str) -> bool:
        return bool(text and isinstance(text, str)) 