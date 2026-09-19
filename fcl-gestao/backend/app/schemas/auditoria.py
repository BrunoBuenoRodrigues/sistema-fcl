from datetime import datetime

from pydantic import BaseModel


class EventoAuditoriaResposta(BaseModel):
    id_historico: int
    id_usuario: int
    usuario_nome: str
    usuario_login: str
    tipo_registro: str
    id_registro: int
    acao: str
    descricao: str | None = None
    data_hora: datetime
