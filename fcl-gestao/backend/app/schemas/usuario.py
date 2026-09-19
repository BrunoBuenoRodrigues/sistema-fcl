from datetime import datetime

from pydantic import BaseModel, Field


class UsuarioCriar(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=6, max_length=128)
    perfil: str


class UsuarioResposta(BaseModel):
    id_usuario: int
    nome: str
    login: str
    perfil: str
    ativo: bool
    data_cadastro: datetime

    model_config = {
        "from_attributes": True
    }


class UsuarioResumoResposta(BaseModel):
    id_usuario: int
    nome: str
    perfil: str
    ativo: bool

    model_config = {
        "from_attributes": True
    }


class UsuarioAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    login: str | None = Field(default=None, min_length=1, max_length=50)
    senha: str | None = Field(default=None, min_length=6, max_length=128)
    perfil: str | None = None
    ativo: bool | None = None


class AlterarPropriaSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=6, max_length=128)
    confirmar_nova_senha: str = Field(min_length=1, max_length=128)
