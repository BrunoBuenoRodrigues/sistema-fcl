from datetime import datetime

from pydantic import BaseModel


class NotificacaoResposta(BaseModel):
    id_notificacao: int
    id_usuario: int
    titulo: str
    mensagem: str
    lida: bool
    data_hora: datetime

    model_config = {
        "from_attributes": True
    }


class NotificacoesLidasResposta(BaseModel):
    quantidade_atualizada: int
