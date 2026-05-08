from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role_name: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UserRoleUpdate(BaseModel):
    role_name: str


class UserTenantBind(BaseModel):
    tenant_code: str
    role_name: str = "learner"
    is_active: bool = True


class UserRead(ORMModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    role_name: str | None = None


class GroupRead(ORMModel):
    id: int
    name: str
    member_count: int


class GroupCreate(BaseModel):
    name: str


class GroupMemberRead(ORMModel):
    id: int
    group_id: int
    user_id: int
    full_name: str
    email: str


class GroupMemberCreate(BaseModel):
    user_id: int
