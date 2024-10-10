# constraints/models.py

from typing import List, Optional, Union, Dict
from enum import Enum
from pydantic import BaseModel, Field

class ConstraintCategory(str, Enum):
    GEOGRAPHIC = "Geographic"
    EQUIPMENT = "Equipment"
    PARTNER = "Partner"

class ConstraintType(str, Enum):
    UPPER_BOUND = "Upper Bound"
    EXCLUSION = "Exclusion"

class Condition(BaseModel):
    type: str
    condition: str
    values: Union[List[str], Dict[str, float]] = Field(default_factory=list)
    value: Optional[str] = None

class Constraint(BaseModel):
    name: str
    category: Optional[ConstraintCategory] = None
    constraint_type: ConstraintType = ConstraintType.UPPER_BOUND
    attribute: str = ""
    measure: str = "FMV"
    upper_bound: Optional[float] = None
    aggregation: Optional[str] = None
    apply_per_value: bool = False
    conditions: List[Condition] = Field(default_factory=list)
    group_name: Optional[str] = None
    current_allocation: float = 0.0
    remaining_capacity: float = 0.0
    active: bool = True

class Fund(BaseModel):
    name: str
    capacity: float
    constraints: List[Constraint] = Field(default_factory=list)