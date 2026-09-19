from pydantic import BaseModel, Field, field_validator
from app.schemas.validacoes import cnpj_valido


class FornecedorCriar(BaseModel):
    razao_social: str = Field(min_length=1, max_length=120)
    nome_fantasia: str | None = Field(default=None, max_length=120)
    cnpj: str = Field(min_length=14, max_length=14)
    telefone: str | None = Field(default=None, min_length=10, max_length=15)
    email: str | None = Field(default=None, max_length=100)

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("CNPJ deve conter apenas números.")

        if not cnpj_valido(valor):
            raise ValueError("CNPJ inválido.")

        return valor

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("Telefone deve conter apenas números.")

        return valor


class FornecedorResposta(BaseModel):
    id_fornecedor: int
    razao_social: str
    nome_fantasia: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    email: str | None = None
    ativo: bool

    model_config = {
        "from_attributes": True
    }


class FornecedorAtualizar(BaseModel):
    razao_social: str | None = Field(default=None, min_length=1, max_length=120)
    nome_fantasia: str | None = Field(default=None, max_length=120)
    cnpj: str | None = Field(default=None, min_length=14, max_length=14)
    telefone: str | None = Field(default=None, min_length=10, max_length=15)
    email: str | None = Field(default=None, max_length=100)
    ativo: bool | None = None

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("CNPJ deve conter apenas números.")

        if not cnpj_valido(valor):
            raise ValueError("CNPJ inválido.")

        return valor

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("Telefone deve conter apenas números.")

        return valor
