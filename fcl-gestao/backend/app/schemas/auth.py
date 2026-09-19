from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def normalizar_login(cls, valor: str):
        return valor.strip()


class TokenResposta(BaseModel):
    access_token: str
    token_type: str
    usuario: str
    perfil: str
