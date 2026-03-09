from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class AnalystType(str, Enum):
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
