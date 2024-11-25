import aiohttp
from django.conf import settings
import json

class BaseReporter:
    @staticmethod
    async def send_report(task: str, answer: dict) -> None:
        """Send report to central server"""
        report = {
            "task": task,
            "apikey": settings.DEFAULT_API_KEY,
            "answer": answer
        }
        
        print("Sending report with payload:", json.dumps(report, indent=2))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{settings.CENTRAL_URL}/report", json=report) as response:
                    response_text = await response.text()
                    print(f"Server response status: {response.status}")
                    print(f"Server response body: {response_text}")
                    
                    if response.status != 200:
                        raise Exception(f"Error sending report: {response_text}")
                    else:
                        print("Report sent successfully")
        except Exception as e:
            print(f"Error sending report: {str(e)}")
            raise 