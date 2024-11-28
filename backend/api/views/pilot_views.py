import json
import logging
import asyncio
from rest_framework.decorators import api_view
from rest_framework.response import Response
from modules.openai_client import OpenAIClient
from django.utils.encoding import force_str
from datetime import datetime
from django.urls import get_resolver
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
### System Prompt – Navigating a 4x4 Map

<prompt_objective>
The assistant is to interpret user commands regarding navigation on a 4x4 map, analyze their content, determine movement directions, traveled distances, final positions, and generate a description of the final position in a structured JSON format. The starting point is always ([0,3]).
</prompt_objective>

<prompt_rules>
1. **Map Structure**: The map dimensions are 4x4, with a coordinate system starting in the bottom-left corner ([0,0]). Field descriptions:
   - (0, 0): "góry"
   - (0, 1): "trawa"
   - (0, 2): "trawa"
   - (0, 3): "marker startowy"
   - (1, 0): "góry"
   - (1, 1): "trawa"
   - (1, 2): "wiatrak"
   - (1, 3): "trawa"
   - (2, 0): "samochód"
   - (2, 1): "skały"
   - (2, 2): "trawa"
   - (2, 3): "drzewo"
   - (3, 0): "jaskinia"
   - (3, 1): "dwa drzewa"
   - (3, 2): "trawa"
   - (3, 3): "dom"

2. **Map Interpretation Rules**:
   - Base directions:
     - "Up" (top): Y-coordinate increases.
     - "Down" (bottom): Y-coordinate decreases.
     - "Right": X-coordinate increases.
     - "Left": X-coordinate decreases.
   - The starting position is always [0,3].
   - Movement must be limited to one axis per stage.

3. **Movement Validation**:
   - The movement must stay within the map boundaries (0 ≤ X ≤ 3, 0 ≤ Y ≤ 3).
   - If the command exceeds the map, return an error and suggest corrections.
   - Keep in mind that terms like 'behind the object' or 'in front of the object' refer to positions distinct from the object's own location. Check if your step count match this rule.

4. **Final Position Description**:
   - The **"description"** in the JSON response always reflects the content of the field where the movement ends.
   - If the command refers to an object (e.g., "house") and the user must stop before it, the number of steps should be one less than the distance to the object.
5. ANSWER ONLY IN POLISH
</prompt_rules>

<task_execution_steps>

1. Split the command into individual movement stages.
2. For each stage:
   - Identify object in command and its coordinates (e.g., "rocks" -> [2,1]).
   - Identify axis for movement (e.g. current position -> mountains means down)
   - Interpret the relationship keyword ("behind", "in front of", "above"):
     - "above": Final position is exactly the object's coordinates.
     - "behind": 
       - Determine the axis of the object.
       - Move one step further along the axis beyond the object's position:
         - Horizontal axis: Adjust X-coordinate.
         - Vertical axis: Adjust Y-coordinate.
     - "in front of":
       - Determine the axis of the object.
       - Move one step closer to the starting point along the axis:
         - Horizontal axis: Adjust X-coordinate.
         - Vertical axis: Adjust Y-coordinate.
     - "next to":
       - Determine position of the object.
       - Move to the position next to the object along valid axis.
   - Validate final position (ensure within map boundaries, within single axis and with correct relationship to the objects).
   - Record the movement stage with all calculated details.
3. Validate the movement within map boundaries and adherence to the one-axis-per-stage rule.
4. **Validate the final position**:
    - Ensure that the **"description"** matches the map field content for the final position coordinates.
    - If the final position is [X,Y], assign the map[X,Y] content to **"description"**.
5. Generate a response for each stage and a summary for the final position.
</task_execution_steps>

<prompt_examples>

USER: "I moved 1 step to the right."
AI: 
```json
{
  "thinking": {
    "instruction": "I moved 1 step to the right.",
    "directions": {
      "top": "[x,3]",
      "bottom": "[x,0]",
      "right": "[3,y]",
      "left": "[0,y]"
    },
    "stages": {
      "stage_1": {
        "task": "1 step to the right",
        "starting_position": "[0,3]",
        "vector": "right",
        "steps": 1,
        "end_position": "[1,3]",
        "reasoning": "Starting position is [0,3]. Moving 1 step to the right leads to [1,3]."
      }
    },
    "summary": "The final stage ended at position [1,3]. According to the map, there is grass at this position."
  },
  "description": "grass"
}
```

USER: "I moved 2 steps to the right, then 1 step down."
AI: 
```json
{
  "thinking": {
    "instruction": "I moved 2 steps to the right, then 1 step down.",
    "directions": {
      "top": "[x,3]",
      "bottom": "[x,0]",
      "right": "[3,y]",
      "left": "[0,y]"
    },
    "stages": {
      "stage_1": {
        "task": "2 steps to the right",
        "starting_position": "[0,3]",
        "vector": "right",
        "steps": 2,
        "end_position": "[2,3]",
        "reasoning": "Starting position is [0,3]. Moving 2 steps to the right leads to [2,3]."
      },
      "stage_2": {
        "task": "1 step down",
        "starting_position": "[2,3]",
        "vector": "bottom",
        "steps": 1,
        "end_position": "[2,2]",
        "reasoning": "Starting position is [2,3]. Moving 1 step down leads to [2,2]."
      }
    },
    "summary": "The final stage ended at position [2,2]. According to the map, there is grass at this position."
  },
  "description": "grass"
}
```

USER: "I stopped in front of the house."
AI: 
```json
{
  "thinking": {
    "task": "I stopped in front of the house.",
    "directions": {
      "top": "[x,3]",
      "bottom": "[x,0]",
      "right": "[3,y]",
      "left": "[0,y]"
    },
    "stages": {
      "stage_1": {
        "task": "stopped in front of the house",
        "starting_position": "[0,3]",
        "vector": "right",
        "steps": 2,
        "end_position": "[2,3]",
        "reasoning": "Starting position is [0,3]. The house is located at [3,3]. Stopping before it means moving 2 steps to the right, ending at [2,3]."
      }
    },
    "summary": "The final stage ended at position [2,3]. According to the map, there is a tree at this position."
  },
  "description": "tree"
}
```
</prompt_examples>

"""

@api_view(['POST'])
def pilot_instruction(request):
    """Handle pilot instruction endpoint"""
    logger.info("Received pilot instruction request")
    
    try:
        # Próba dekodowania danych wejściowych
        try:
            if isinstance(request.data, bytes):
                instruction_data = json.loads(request.data.decode('utf-8'))
            else:
                instruction_data = request.data

            instruction = force_str(instruction_data.get('instruction', ''))
        except Exception as e:
            logger.error(f"Error decoding request data: {e}")
            return Response(
                {"error": "Invalid request data encoding"}, 
                status=400
            )

        if not instruction:
            logger.error("No instruction provided in request")
            return Response(
                {"error": "No instruction provided"}, 
                status=400
            )

        logger.info(f"Processing instruction: {instruction}")

        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction}
        ]

        # Get response from LLM using synchronous event loop
        client = OpenAIClient()
        response = asyncio.run(client.chat_completion(
            messages=messages,
            temperature=0.3
        ))

        logger.info(f"Raw LLM response: {response}")

        if response["status"] != "success":
            logger.error(f"LLM error: {response.get('error')}")
            return Response(
                {"error": "Failed to process instruction"}, 
                status=500
            )

        # Parse LLM response as JSON
        try:
            # Usuń znaczniki Markdown dla bloku kodu JSON
            content = response["content"]
            if content.startswith('```json\n'):
                content = content[8:]  # usuń ```json\n z początku
            if content.endswith('\n```'):
                content = content[:-4]  # usuń \n``` z końca
            
            llm_response = json.loads(content)
            logger.info(f"Parsed LLM response: {llm_response}")
            return Response(llm_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return Response(
                {"error": "Invalid response format from LLM"}, 
                status=500
            )

    except Exception as e:
        logger.error(f"Unexpected error in pilot_instruction: {e}")
        return Response(
            {"error": f"Internal server error: {str(e)}"}, 
            status=500
        ) 

@api_view(['GET'])
def test_connection(request):
    """Debug endpoint to test connection and show request details"""
    # Get all registered URLs
    resolver = get_resolver()
    all_urls = [str(pattern.pattern) for pattern in resolver.url_patterns]
    
    return Response({
        "status": "ok",
        "message": "Connection successful",
        "server_time": datetime.now().isoformat(),
        "debug_info": {
            "request_path": request.path,
            "registered_urls": all_urls,
            "allowed_hosts": settings.ALLOWED_HOSTS,
            "base_url": request.build_absolute_uri('/'),
            "request_headers": dict(request.headers),
            "request_method": request.method,
        }
    }) 