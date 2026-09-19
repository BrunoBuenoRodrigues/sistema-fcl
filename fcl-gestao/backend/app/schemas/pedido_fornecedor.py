from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class ItemPedidoCriar(BaseModel):
    id_item_solicitacao: int
    quantidade: Decimal = Field(..., gt=0)


class PedidoCompraCriar(BaseModel):
    id_solicitacao: int
    id_fornecedor: int
    numero_pedido: str = Field(..., min_length=1, max_length=30)
    data_pedido: date
    observacao: str | None = None
    itens: list[ItemPedidoCriar] | None = Field(default=None, min_length=1)

    @field_validator("numero_pedido", mode="before")
    @classmethod
    def validar_numero_pedido(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O número do pedido não pode estar vazio.")

        return valor.strip()

    @field_validator("itens")
    @classmethod
    def validar_itens_duplicados(cls, itens):
        if itens is None:
            return itens

        ids_itens = [item.id_item_solicitacao for item in itens]
        if len(ids_itens) != len(set(ids_itens)):
            raise ValueError("Não é permitido repetir o mesmo item no pedido.")

        return itens


class PedidoCompraAtualizar(BaseModel):
    id_fornecedor: int
    numero_pedido: str = Field(..., min_length=1, max_length=30)
    data_pedido: date
    observacao: str | None = None
    itens: list[ItemPedidoCriar] = Field(..., min_length=1)

    @field_validator("numero_pedido", mode="before")
    @classmethod
    def validar_numero_pedido(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O número do pedido não pode estar vazio.")

        return valor.strip()

    @field_validator("itens")
    @classmethod
    def validar_itens_duplicados(cls, itens):
        ids_itens = [item.id_item_solicitacao for item in itens]
        if len(ids_itens) != len(set(ids_itens)):
            raise ValueError("Não é permitido repetir o mesmo item no pedido.")

        return itens


class PedidoCompraCancelar(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def validar_motivo_cancelamento(cls, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ValueError(
                "O motivo do cancelamento deve possuir pelo menos 3 caracteres."
            )

        return valor.strip()


class PedidoCompraResposta(BaseModel):
    id_pedido_compra: int
    id_solicitacao: int
    id_fornecedor: int
    numero_pedido: str | None = None
    data_pedido: date
    status: str
    observacao: str | None = None
    motivo_cancelamento: str | None = None
    data_cancelamento: datetime | None = None
    id_usuario_cancelamento: int | None = None

    model_config = {
        "from_attributes": True
    }


class ItemPedidoDetalheResposta(BaseModel):
    id_item_pedido: int
    id_item_solicitacao: int
    id_produto: int
    quantidade: Decimal
    quantidade_recebida: Decimal
    saldo_pendente: Decimal


class PedidoCompraDetalheResposta(PedidoCompraResposta):
    itens: list[ItemPedidoDetalheResposta]
