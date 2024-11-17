from celery import shared_task
from typing import Any, Dict
from abc import ABC, abstractmethod

class BaseProcessor(ABC):
    @abstractmethod
    async def process(self, data: Any) -> Dict[str, Any]:
        """
        Abstract method for processing data
        """
        pass

    @shared_task
    def process_async(self, data: Any) -> Dict[str, Any]:
        """
        Process data asynchronously using Celery
        """
        return self.process(data)

    def validate_input(self, data: Any) -> bool:
        """
        Validate input data before processing
        """
        return True 