from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Literal

class ItemSolicitacaoCriar(BaseModel):
    id_produto: int
    quantidade: int = Field(..., gt=0)


class SolicitacaoCompraCriar(BaseModel):
    prioridade: Literal["BAIXA", "MEDIA", "ALTA"]
    motivo: str = Field(..., min_length=1)
    observacao: str | None = None
    itens: list[ItemSolicitacaoCriar] = Field(..., min_length=1)

    @field_validator("motivo", mode="before")
    @classmethod
    def validar_motivo(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O motivo não pode estar vazio.")
        return valor.strip()

    @field_validator("itens")
    @classmethod
    def validar_produtos_duplicados(cls, itens):
        ids_produtos = [item.id_produto for item in itens]

        if len(ids_produtos) != len(set(ids_produtos)):
            raise ValueError(
                "Não é permitido repetir o mesmo produto na solicitação."
            )

        return itens


class SolicitacaoCompraAtualizar(SolicitacaoCompraCriar):
    pass

class ItemSolicitacaoResposta(BaseModel):
    id_item_solicitacao: int
    id_produto: int
    quantidade: float

    model_config = {
        "from_attributes": True
    }


class SolicitacaoCompraResposta(BaseModel):
    id_solicitacao: int
    id_usuario_solicitante: int
    data_solicitacao: datetime
    prioridade: str
    status: str
    motivo: str
    observacao: str | None = None
    motivo_rejeicao: str | None = None
    motivo_cancelamento: str | None = None
    data_cancelamento: datetime | None = None
    id_usuario_cancelamento: int | None = None
    itens: list[ItemSolicitacaoResposta] = []

    model_config = {
        "from_attributes": True
    }

class SolicitacaoRejeitar(BaseModel):
    motivo_rejeicao: str = Field(..., min_length=1)

    @field_validator("motivo_rejeicao", mode="before")
    @classmethod
    def validar_motivo_rejeicao(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O motivo da rejeição não pode estar vazio.")

        return valor.strip()


class SolicitacaoCancelar(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def validar_motivo_cancelamento(cls, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ValueError(
                "O motivo do cancelamento deve possuir pelo menos 3 caracteres."
            )

        return valor.strip()
