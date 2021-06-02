from pydantic import BaseModel
from pydantic.typing import List


class ResponseModel(BaseModel):
    # There's good reason for having this child class later on.
    # It is to allow for global response model configuration via inheritance.
    pass

class Entity(ResponseModel):
    entity_id: int
    entity_type: str
    name: str

class Origin(ResponseModel):
    id: int
    name: str
    description: str
