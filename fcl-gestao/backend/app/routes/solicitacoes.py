from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.produto import Produto
from app.models.notificacao import Notificacao
from app.models.item_solicitacao import ItemSolicitacao
from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.usuario import Usuario
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.pedido_fornecedor import PedidoCompra
from app.models.historico import Historico
from app.schemas.historico import HistoricoResposta
from app.regras_pedidos import recalcular_status_solicitacao
from app.schemas.solicitacao_compra import (
    SolicitacaoCompraCriar,
    SolicitacaoCompraAtualizar,
    SolicitacaoCompraResposta,
    SolicitacaoCancelar,
    SolicitacaoRejeitar
)


router = APIRouter(
    prefix="/solicitacoes",
    tags=["Solicitações de Compra"]
)


def adicionar_historico(
    db: Session,
    usuario: Usuario,
    solicitacao: SolicitacaoCompra,
    acao: str,
    descricao: str,
) -> None:
    db.add(
        Historico(
            id_usuario=usuario.id_usuario,
            tipo_registro="SOLICITACAO",
            id_registro=solicitacao.id_solicitacao,
            acao=acao,
            descricao=descricao,
            data_hora=datetime.now(),
        )
    )


@router.get("/", response_model=list[SolicitacaoCompraResposta])
def listar_solicitacoes(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    return db.query(SolicitacaoCompra).order_by(
        SolicitacaoCompra.id_solicitacao.desc()
    ).all()

@router.post(
    "/",
    response_model=SolicitacaoCompraResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_solicitacao(
    dados: SolicitacaoCompraCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    nova_solicitacao = SolicitacaoCompra(
    id_usuario_solicitante=usuario_atual.id_usuario,
    data_solicitacao=datetime.now(),
    prioridade=dados.prioridade,
    status="SOLICITADA",
    motivo=dados.motivo,
    observacao=dados.observacao
)

    db.add(nova_solicitacao)

# Gera o ID, mas ainda NÃO salva definitivamente
    db.flush()

    for item in dados.itens:
        produto = db.query(Produto).filter(
            Produto.id_produto == item.id_produto
        ).first()

        if not produto:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Produto {item.id_produto} não encontrado."
            )

        if not produto.ativo:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"O produto {item.id_produto} está inativo."
            )

        novo_item = ItemSolicitacao(
            id_solicitacao=nova_solicitacao.id_solicitacao,
            id_produto=item.id_produto,
            quantidade=item.quantidade
        )

        db.add(novo_item)

    adicionar_historico(
        db,
        usuario_atual,
        nova_solicitacao,
        "CADASTRO",
        (
            f"Solicitação cadastrada com prioridade {dados.prioridade} "
            f"e {len(dados.itens)} item(ns)."
        ),
    )

# só depois que terminar TODOS os itens
    db.commit()
    db.refresh(nova_solicitacao)

    return nova_solicitacao


@router.put(
    "/{id_solicitacao}",
    response_model=SolicitacaoCompraResposta,
)
def atualizar_solicitacao(
    id_solicitacao: int,
    dados: SolicitacaoCompraAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR", "FUNCIONARIO", "ESTOQUE")
    ),
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada.",
        )

    if (
        usuario_atual.perfil != "ADMINISTRADOR"
        and solicitacao.id_usuario_solicitante != usuario_atual.id_usuario
    ):
        raise HTTPException(
            status_code=403,
            detail="Somente o solicitante pode editar esta solicitação.",
        )

    if solicitacao.status != "SOLICITADA":
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações com status SOLICITADA podem ser editadas.",
        )

    for item in dados.itens:
        produto = db.query(Produto).filter(
            Produto.id_produto == item.id_produto
        ).first()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {item.id_produto} não encontrado.",
            )

        if not produto.ativo:
            raise HTTPException(
                status_code=400,
                detail=f"O produto {item.id_produto} está inativo.",
            )

    prioridade_anterior = solicitacao.prioridade
    itens_anteriores = [
        f"{item.id_produto}:{float(item.quantidade):g}"
        for item in solicitacao.itens
    ]

    solicitacao.prioridade = dados.prioridade
    solicitacao.motivo = dados.motivo
    solicitacao.observacao = dados.observacao

    for item_existente in list(solicitacao.itens):
        db.delete(item_existente)
    db.flush()

    for item in dados.itens:
        db.add(
            ItemSolicitacao(
                id_solicitacao=id_solicitacao,
                id_produto=item.id_produto,
                quantidade=item.quantidade,
            )
        )

    itens_novos = [
        f"{item.id_produto}:{item.quantidade}"
        for item in dados.itens
    ]
    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="SOLICITACAO",
        id_registro=id_solicitacao,
        acao="EDICAO",
        descricao=(
            f"Solicitação editada. Prioridade: {prioridade_anterior} para "
            f"{dados.prioridade}. Itens: {', '.join(itens_anteriores)} para "
            f"{', '.join(itens_novos)}."
        ),
        data_hora=datetime.now(),
    )
    db.add(historico)
    db.commit()

    return db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).first()

@router.get(
    "/{id_solicitacao}",
    response_model=SolicitacaoCompraResposta
)
def buscar_solicitacao(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    return solicitacao

@router.patch(
    "/{id_solicitacao}/iniciar-analise",
    response_model=SolicitacaoCompraResposta
)
def iniciar_analise(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    if solicitacao.status != "SOLICITADA":
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações com status SOLICITADA podem entrar em análise."
        )

    solicitacao.status = "EM_ANALISE"
    adicionar_historico(
        db,
        usuario_atual,
        solicitacao,
        "ALTERACAO_STATUS",
        "Status alterado de SOLICITADA para EM_ANALISE.",
    )

    db.commit()
    db.refresh(solicitacao)

    return solicitacao

@router.patch(
    "/{id_solicitacao}/aprovar",
    response_model=SolicitacaoCompraResposta
)
def aprovar_solicitacao(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    if solicitacao.status != "EM_ANALISE":
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações EM_ANALISE podem ser aprovadas."
        )

    solicitacao.status = "APROVADA"
    solicitacao.motivo_rejeicao = None
    adicionar_historico(
        db,
        usuario_atual,
        solicitacao,
        "APROVACAO",
        "Solicitação aprovada.",
    )

    nova_notificacao = Notificacao(
        id_usuario=solicitacao.id_usuario_solicitante,
        titulo="Solicitação aprovada",
        mensagem=f"A solicitação {solicitacao.id_solicitacao} foi aprovada.",
        lida=False,
        data_hora=datetime.now()
    )

    db.add(nova_notificacao)

    db.commit()
    db.refresh(solicitacao)

    return solicitacao

@router.patch(
    "/{id_solicitacao}/rejeitar",
    response_model=SolicitacaoCompraResposta
)
def rejeitar_solicitacao(
    id_solicitacao: int,
    dados: SolicitacaoRejeitar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    if solicitacao.status != "EM_ANALISE":
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações EM_ANALISE podem ser rejeitadas."
        )

    solicitacao.status = "REJEITADA"
    solicitacao.motivo_rejeicao = dados.motivo_rejeicao
    adicionar_historico(
        db,
        usuario_atual,
        solicitacao,
        "REJEICAO",
        f"Solicitação rejeitada. Motivo: {dados.motivo_rejeicao}",
    )

    notificacao = Notificacao(
        id_usuario=solicitacao.id_usuario_solicitante,
        titulo="Solicitação rejeitada",
        mensagem=f"A solicitação {solicitacao.id_solicitacao} foi rejeitada.",
        lida=False,
        data_hora=datetime.now()
    )

    db.add(notificacao)

    db.commit()
    db.refresh(solicitacao)

    return solicitacao

@router.patch(
    "/{id_solicitacao}/pedido-realizado",
    response_model=SolicitacaoCompraResposta
)
def marcar_pedido_realizado(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    if solicitacao.status != "APROVADA":
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações APROVADAS podem ser marcadas como PEDIDO_REALIZADO."
        )

    recalcular_status_solicitacao(db, solicitacao)
    if solicitacao.status != "PEDIDO_REALIZADO":
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ainda existem quantidades sem pedido nesta solicitação."
        )

    adicionar_historico(
        db,
        usuario_atual,
        solicitacao,
        "PEDIDO_REALIZADO",
        "Todos os itens da solicitação foram distribuídos em pedidos.",
    )

    db.commit()
    db.refresh(solicitacao)

    return solicitacao


@router.patch(
    "/{id_solicitacao}/cancelar",
    response_model=SolicitacaoCompraResposta,
)
def cancelar_solicitacao(
    id_solicitacao: int,
    dados: SolicitacaoCancelar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR", "FUNCIONARIO", "ESTOQUE")
    ),
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).with_for_update().first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada.",
        )

    administrador = usuario_atual.perfil == "ADMINISTRADOR"
    if not administrador:
        if solicitacao.id_usuario_solicitante != usuario_atual.id_usuario:
            raise HTTPException(
                status_code=403,
                detail="Somente o solicitante pode cancelar esta solicitação.",
            )

        if solicitacao.status != "SOLICITADA":
            raise HTTPException(
                status_code=400,
                detail=(
                    "O solicitante só pode cancelar enquanto a solicitação "
                    "estiver com status SOLICITADA."
                ),
            )
    elif solicitacao.status not in ["SOLICITADA", "EM_ANALISE", "APROVADA"]:
        raise HTTPException(
            status_code=400,
            detail="Não é possível cancelar a solicitação neste status.",
        )

    pedido_ativo = db.query(PedidoCompra.id_pedido_compra).filter(
        PedidoCompra.id_solicitacao == id_solicitacao,
        PedidoCompra.status != "CANCELADO",
    ).first()
    if pedido_ativo:
        raise HTTPException(
            status_code=400,
            detail="Cancele os pedidos ativos antes de cancelar a solicitação.",
        )

    agora = datetime.now()
    status_anterior = solicitacao.status
    solicitacao.status = "CANCELADA"
    solicitacao.motivo_cancelamento = dados.motivo
    solicitacao.data_cancelamento = agora
    solicitacao.id_usuario_cancelamento = usuario_atual.id_usuario

    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="SOLICITACAO",
        id_registro=solicitacao.id_solicitacao,
        acao="CANCELAMENTO",
        descricao=(
            f"Solicitação cancelada quando estava em {status_anterior}. "
            f"Motivo: {dados.motivo}"
        ),
        data_hora=agora,
    )
    db.add(historico)

    if solicitacao.id_usuario_solicitante != usuario_atual.id_usuario:
        notificacao = Notificacao(
            id_usuario=solicitacao.id_usuario_solicitante,
            titulo="Solicitação cancelada",
            mensagem=(
                f"A solicitação {solicitacao.id_solicitacao} foi cancelada. "
                f"Motivo: {dados.motivo}"
            ),
            lida=False,
            data_hora=agora,
        )
        db.add(notificacao)

    db.commit()
    db.refresh(solicitacao)

    return solicitacao


@router.get(
    "/{id_solicitacao}/historico",
    response_model=list[HistoricoResposta],
)
def listar_historico_solicitacao(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR", "FUNCIONARIO", "ESTOQUE")
    ),
):
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == id_solicitacao
    ).first()

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada.",
        )

    return db.query(Historico).filter(
        Historico.tipo_registro == "SOLICITACAO",
        Historico.id_registro == id_solicitacao,
    ).order_by(
        Historico.data_hora.asc(),
        Historico.id_historico.asc(),
    ).all()
