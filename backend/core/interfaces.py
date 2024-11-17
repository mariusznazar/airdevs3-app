from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseModule(ABC):
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data and return results"""
        pass
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate input data"""
        pass
    
    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return module name"""
        pass

class ModuleRegistry:
    _modules = {}
    
    @classmethod
    def register(cls, module_instance: BaseModule):
        cls._modules[module_instance.module_name] = module_instance
    
    @classmethod
    def get_module(cls, module_name: str) -> BaseModule:
        return cls._modules.get(module_name) 