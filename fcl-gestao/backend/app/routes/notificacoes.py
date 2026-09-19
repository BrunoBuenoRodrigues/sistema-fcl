from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.notificacao import Notificacao
from app.models.usuario import Usuario
from app.schemas.notificacao import NotificacaoResposta, NotificacoesLidasResposta


router = APIRouter(
    prefix="/notificacoes",
    tags=["Notificações"]
)


@router.get(
    "/",
    response_model=list[NotificacaoResposta]
)
def listar_notificacoes(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    return db.query(Notificacao).filter(
        Notificacao.id_usuario == usuario_atual.id_usuario
    ).order_by(
        Notificacao.data_hora.desc()
    ).all()


@router.patch(
    "/todas/lidas",
    response_model=NotificacoesLidasResposta,
)
def marcar_todas_como_lidas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    quantidade_atualizada = db.query(Notificacao).filter(
        Notificacao.id_usuario == usuario_atual.id_usuario,
        Notificacao.lida.is_(False),
    ).update(
        {Notificacao.lida: True},
        synchronize_session=False,
    )

    db.commit()

    return {"quantidade_atualizada": quantidade_atualizada}


@router.patch(
    "/{id_notificacao}/lida",
    response_model=NotificacaoResposta
)
def marcar_como_lida(
    id_notificacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    notificacao = db.query(Notificacao).filter(
        Notificacao.id_notificacao == id_notificacao,
        Notificacao.id_usuario == usuario_atual.id_usuario
    ).first()

    if not notificacao:
        raise HTTPException(
            status_code=404,
            detail="Notificação não encontrada."
        )

    notificacao.lida = True

    db.commit()
    db.refresh(notificacao)

    return notificacao
