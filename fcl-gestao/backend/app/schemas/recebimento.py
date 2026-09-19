from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

class ItemRecebimentoCriar(BaseModel):
    id_item_pedido: int
    quantidade_recebida: Decimal


class RecebimentoCriar(BaseModel):
    id_pedido_compra: int
    numero_nota_fiscal: str | None = Field(default=None, max_length=30)
    observacao: str | None = None
    itens: list[ItemRecebimentoCriar]

    @field_validator("numero_nota_fiscal", mode="before")
    @classmethod
    def normalizar_numero_nota_fiscal(cls, valor):
        if valor is None:
            return None

        numero = str(valor).strip()
        return numero or None


class ItemRecebimentoResposta(BaseModel):
    id_item_recebimento: int
    id_item_pedido: int
    id_produto: int
    quantidade_recebida: Decimal


class RecebimentoResposta(BaseModel):
    id_recebimento: int
    id_pedido_compra: int
    id_usuario_recebimento: int
    data_recebimento: datetime
    numero_nota_fiscal: str | None = None
    observacao: str | None = None
    status: str
    motivo_estorno: str | None = None
    data_estorno: datetime | None = None
    id_usuario_estorno: int | None = None
    itens: list[ItemRecebimentoResposta] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }

class RecebimentoEstornar(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def validar_motivo(cls, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ValueError("Informe o motivo do estorno.")
        return valor.strip()
