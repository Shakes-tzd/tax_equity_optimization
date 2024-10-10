from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field
from enum import Enum

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
    category: ConstraintCategory
    constraint_type: ConstraintType
    attribute: str
    measure: str
    upper_bound: float
    conditions: List[Condition]
    group_name: Optional[str] = None
    aggregation: Optional[str] = None
    apply_per_value: bool = False
    current_allocation: float = 0.0
    remaining_capacity: float = 0.0
    active: bool = True

class Fund(BaseModel):
    name: str
    capacity: float
    constraints: List[Constraint]