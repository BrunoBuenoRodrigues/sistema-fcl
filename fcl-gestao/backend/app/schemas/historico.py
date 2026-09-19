from datetime import datetime

from pydantic import BaseModel


class HistoricoResposta(BaseModel):
    id_historico: int
    id_usuario: int
    tipo_registro: str
    id_registro: int
    acao: str
    descricao: str | None = None
    data_hora: datetime

    model_config = {
        "from_attributes": True
    }