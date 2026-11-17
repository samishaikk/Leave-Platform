from pydantic import BaseModel, ConfigDict

from app.models import Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: Role
    manager_id: int | None