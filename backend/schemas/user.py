from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    """
    Schema para registro de novos usuários.
    
    Usado após criação no Supabase Auth para criar tenant e membership.
    """
    user_id: str = Field(..., description="ID do usuário no Supabase Auth")
    email: EmailStr = Field(..., description="Email do usuário")
    full_name: str = Field(..., min_length=3, description="Nome completo")
    company_name: str = Field(..., min_length=2, description="Nome da empresa/tenant")
    
    # Campos opcionais
    phone: Optional[str] = Field(None, description="Telefone para contato")
    company_size: Optional[str] = Field(None, description="Tamanho da empresa")
    industry: Optional[str] = Field(None, description="Setor/indústria")
    country: Optional[str] = Field(None, description="País")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                "email": "joao@empresa.com",
                "full_name": "João Silva",
                "company_name": "Tech Corp LTDA",
                "phone": "+55 11 99999-9999",
                "company_size": "1-10 funcionários",
                "industry": "Tecnologia",
                "country": "Brasil"
            }
        }


class UserLogin(BaseModel):
    """Schema para login (se implementar endpoint dedicado)."""
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserInfo(BaseModel):
    """Schema para informações do usuário."""
    user_id: str
    email: str
    full_name: Optional[str] = None
    tenants: list = []