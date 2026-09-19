from datetime import datetime

from pydantic import BaseModel


class ResumoDashboardResposta(BaseModel):
    solicitacoes_em_andamento: int | None
    pedidos_aguardando_recebimento: int | None
    entregas_em_aberto: int
    gerado_em: datetime
