from pydantic import BaseModel, Field, field_validator
from app.schemas.validacoes import cnpj_valido, cpf_valido


class ClienteCriar(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    cpf_cnpj: str | None = None
    telefone: str | None = Field(default=None, min_length=10, max_length=15)
    endereco: str = Field(min_length=1, max_length=120)
    numero: str = Field(min_length=1, max_length=20)
    bairro: str = Field(min_length=1, max_length=60)
    cidade: str = Field(min_length=1, max_length=60)
    uf: str = Field(min_length=2, max_length=2)
    observacao: str | None = None

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_cpf_cnpj(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("CPF/CNPJ deve conter apenas números.")

        if len(valor) not in (11, 14):
            raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos.")

        if len(valor) == 11 and not cpf_valido(valor):
            raise ValueError("CPF inválido.")

        if len(valor) == 14 and not cnpj_valido(valor):
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


class ClienteResposta(BaseModel):
    id_cliente: int
    nome: str
    cpf_cnpj: str | None = None
    telefone: str | None = None
    endereco: str
    numero: str
    bairro: str
    cidade: str
    uf: str
    observacao: str | None = None
    ativo: bool

    model_config = {
        "from_attributes": True
    }


class ClienteAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    cpf_cnpj: str | None = None
    telefone: str | None = Field(default=None, min_length=10, max_length=15)
    endereco: str | None = Field(default=None, min_length=1, max_length=120)
    numero: str | None = Field(default=None, min_length=1, max_length=20)
    bairro: str | None = Field(default=None, min_length=1, max_length=60)
    cidade: str | None = Field(default=None, min_length=1, max_length=60)
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    observacao: str | None = None
    ativo: bool | None = None

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_cpf_cnpj(cls, valor):
        if valor is None:
            return valor

        if not valor.isdigit():
            raise ValueError("CPF/CNPJ deve conter apenas números.")

        if len(valor) not in (11, 14):
            raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos.")

        if len(valor) == 11 and not cpf_valido(valor):
            raise ValueError("CPF inválido.")

        if len(valor) == 14 and not cnpj_valido(valor):
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
