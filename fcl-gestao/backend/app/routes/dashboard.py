from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.entrega import Entrega
from app.models.pedido_fornecedor import PedidoCompra
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.usuario import Usuario
from app.schemas.dashboard import ResumoDashboardResposta


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/resumo", response_model=ResumoDashboardResposta)
def obter_resumo_dashboard(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR",
        )
    ),
):
    solicitacoes_em_andamento = None
    if usuario_atual.perfil != "ENTREGADOR":
        consulta_solicitacoes = db.query(SolicitacaoCompra).filter(
            SolicitacaoCompra.status.in_([
                "SOLICITADA",
                "EM_ANALISE",
                "APROVADA",
            ])
        )

        if usuario_atual.perfil == "FUNCIONARIO":
            consulta_solicitacoes = consulta_solicitacoes.filter(
                SolicitacaoCompra.id_usuario_solicitante
                == usuario_atual.id_usuario
            )

        solicitacoes_em_andamento = consulta_solicitacoes.count()

    pedidos_aguardando_recebimento = None
    if usuario_atual.perfil in ["ADMINISTRADOR", "ESTOQUE"]:
        pedidos_aguardando_recebimento = db.query(PedidoCompra).filter(
            PedidoCompra.status.in_([
                "AGUARDANDO_RECEBIMENTO",
                "RECEBIDO_PARCIAL",
            ])
        ).count()

    consulta_entregas = db.query(Entrega).filter(
        Entrega.status.notin_(["ENTREGUE", "CANCELADA"])
    )
    if usuario_atual.perfil == "ENTREGADOR":
        consulta_entregas = consulta_entregas.filter(
            Entrega.id_entregador == usuario_atual.id_usuario
        )

    return {
        "solicitacoes_em_andamento": solicitacoes_em_andamento,
        "pedidos_aguardando_recebimento": pedidos_aguardando_recebimento,
        "entregas_em_aberto": consulta_entregas.count(),
        "gerado_em": datetime.now(),
    }
