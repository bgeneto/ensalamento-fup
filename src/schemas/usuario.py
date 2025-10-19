"""
Data Transfer Objects (DTOs) for user-related entities

These DTOs represent users and authentication without any database connection.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


# ============================================================================
# USER DTOs
# ============================================================================


class RoleEnum(str):
    """User role values"""

    ADMIN = "admin"
    PROFESSOR = "professor"


class UsuarioDTO(BaseModel):
    """Complete user representation"""

    username: str
    nome_completo: Optional[str] = None
    role: str = "professor"
    password_hash: Optional[str] = None  # Never included in API responses

    class Config:
        from_attributes = True


class UsuarioCreateDTO(BaseModel):
    """DTO for creating users"""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6)
    nome_completo: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default="professor")


class UsuarioUpdateDTO(BaseModel):
    """DTO for updating users"""

    nome_completo: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UsuarioSimplifiedDTO(BaseModel):
    """Simplified user for lists/dropdowns"""

    username: str
    nome_completo: str
    role: str

    class Config:
        from_attributes = True


class LoginRequestDTO(BaseModel):
    """DTO for login requests"""

    username: str
    password: str


class LoginResponseDTO(BaseModel):
    """DTO for login responses"""

    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[UsuarioDTO] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ChangePasswordDTO(BaseModel):
    """DTO for password changes"""

    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class UsuarioListDTO(BaseModel):
    """User info for lists"""

    username: str
    nome_completo: str
    role: str

    class Config:
        from_attributes = True
