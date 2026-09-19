from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

class AtribuirEntregador(BaseModel):
    id_entregador: int


class ComprovanteEntregaAtualizar(BaseModel):
    comprovante_entrega: str = Field(min_length=1, max_length=255)


class AgendamentoEntregaAtualizar(BaseModel):
    data_agendada: date


class EntregaCancelar(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, valor: str) -> str:
        motivo = valor.strip()
        if len(motivo) < 3:
            raise ValueError("Informe um motivo com pelo menos 3 caracteres.")
        if len(motivo) > 500:
            raise ValueError("O motivo deve possuir no máximo 500 caracteres.")
        return motivo


class EntregaNaoEntregue(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, valor: str) -> str:
        motivo = valor.strip()
        if len(motivo) < 3:
            raise ValueError("Informe um motivo com pelo menos 3 caracteres.")
        if len(motivo) > 500:
            raise ValueError("O motivo deve possuir no máximo 500 caracteres.")
        return motivo


class EntregaCriar(BaseModel):
    id_cliente: int
    id_entregador: int | None = None
    data_agendada: date | None = None
    anexo_pedido: str | None = Field(default=None, max_length=255)
    observacao: str | None = None


class EntregaAtualizar(BaseModel):
    id_cliente: int
    id_entregador: int | None = None
    data_agendada: date | None = None
    observacao: str | None = None


class EntregaResposta(BaseModel):
    id_entrega: int
    id_cliente: int
    id_usuario_cadastro: int
    id_entregador: int | None = None
    data_cadastro: datetime
    data_agendada: date | None = None
    status: str
    anexo_pedido: str | None = None
    comprovante_entrega: str | None = None
    observacao: str | None = None
    motivo_cancelamento: str | None = None
    data_cancelamento: datetime | None = None
    id_usuario_cancelamento: int | None = None
    motivo_nao_entrega: str | None = None
    data_ultima_tentativa: datetime | None = None
    id_usuario_ultima_tentativa: int | None = None

    model_config = {
        "from_attributes": True
    }
