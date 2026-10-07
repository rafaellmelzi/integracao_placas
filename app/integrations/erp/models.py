from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ERPProduct:
    internal_code: str
    factory_code: Optional[str]
    description: str
    brand: Optional[str]
    application: Optional[str]

@dataclass
class ERPAvailability:
    internal_code: str
    company: str
    stock: float
    price: float
