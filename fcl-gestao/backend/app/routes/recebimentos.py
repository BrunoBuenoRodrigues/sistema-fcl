from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auditoria import registrar_evento_auditoria
from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.item_pedido import ItemPedido
from app.models.item_recebimento import ItemRecebimento
from app.models.item_solicitacao import ItemSolicitacao
from app.models.notificacao import Notificacao
from app.models.pedido_fornecedor import PedidoCompra
from app.models.recebimento import Recebimento
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.usuario import Usuario
from app.schemas.recebimento import (
    RecebimentoCriar,
    RecebimentoEstornar,
    RecebimentoResposta,
)


router = APIRouter(prefix="/recebimentos", tags=["Recebimentos"])


def obter_total_recebido_ativo(db: Session, id_item_pedido: int):
    return (
        db.query(
            func.coalesce(func.sum(ItemRecebimento.quantidade_recebida), 0)
        )
        .join(
            Recebimento,
            Recebimento.id_recebimento == ItemRecebimento.id_recebimento,
        )
        .filter(
            ItemRecebimento.id_item_pedido == id_item_pedido,
            Recebimento.status == "REGISTRADO",
        )
        .scalar()
    )


def recalcular_status_pedido(db: Session, pedido: PedidoCompra) -> None:
    itens_pedido = db.query(ItemPedido).filter(
        ItemPedido.id_pedido_compra == pedido.id_pedido_compra
    ).all()
    totais = [
        obter_total_recebido_ativo(db, item.id_item_pedido)
        for item in itens_pedido
    ]

    if itens_pedido and all(
        total >= item.quantidade
        for item, total in zip(itens_pedido, totais)
    ):
        pedido.status = "RECEBIDO_TOTAL"
    elif any(total > 0 for total in totais):
        pedido.status = "RECEBIDO_PARCIAL"
    else:
        pedido.status = "AGUARDANDO_RECEBIMENTO"


def montar_recebimento(db: Session, recebimento: Recebimento):
    itens = (
        db.query(
            ItemRecebimento.id_item_recebimento,
            ItemRecebimento.id_item_pedido,
            ItemSolicitacao.id_produto,
            ItemRecebimento.quantidade_recebida,
        )
        .join(
            ItemPedido,
            ItemPedido.id_item_pedido == ItemRecebimento.id_item_pedido,
        )
        .join(
            ItemSolicitacao,
            ItemSolicitacao.id_item_solicitacao
            == ItemPedido.id_item_solicitacao,
        )
        .filter(ItemRecebimento.id_recebimento == recebimento.id_recebimento)
        .order_by(ItemRecebimento.id_item_recebimento)
        .all()
    )

    return {
        "id_recebimento": recebimento.id_recebimento,
        "id_pedido_compra": recebimento.id_pedido_compra,
        "id_usuario_recebimento": recebimento.id_usuario_recebimento,
        "data_recebimento": recebimento.data_recebimento,
        "numero_nota_fiscal": recebimento.numero_nota_fiscal,
        "observacao": recebimento.observacao,
        "status": recebimento.status,
        "motivo_estorno": recebimento.motivo_estorno,
        "data_estorno": recebimento.data_estorno,
        "id_usuario_estorno": recebimento.id_usuario_estorno,
        "itens": [
            {
                "id_item_recebimento": item.id_item_recebimento,
                "id_item_pedido": item.id_item_pedido,
                "id_produto": item.id_produto,
                "quantidade_recebida": item.quantidade_recebida,
            }
            for item in itens
        ],
    }


@router.get("/", response_model=list[RecebimentoResposta])
def listar_recebimentos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ESTOQUE", "ADMINISTRADOR")
    ),
):
    recebimentos = db.query(Recebimento).order_by(
        Recebimento.id_recebimento.desc()
    ).all()
    return [montar_recebimento(db, recebimento) for recebimento in recebimentos]


@router.post(
    "/",
    response_model=RecebimentoResposta,
    status_code=status.HTTP_201_CREATED,
)
def registrar_recebimento(
    dados: RecebimentoCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ESTOQUE", "ADMINISTRADOR")
    ),
):
    if not dados.itens:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item para registrar o recebimento.",
        )

    ids_itens = [item.id_item_pedido for item in dados.itens]
    if len(ids_itens) != len(set(ids_itens)):
        raise HTTPException(
            status_code=400,
            detail="Cada item do pedido deve ser informado apenas uma vez.",
        )

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id_pedido_compra == dados.id_pedido_compra)
        .with_for_update()
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if pedido.status not in ("AGUARDANDO_RECEBIMENTO", "RECEBIDO_PARCIAL"):
        raise HTTPException(
            status_code=400,
            detail="O pedido não está disponível para recebimento.",
        )

    novo_recebimento = Recebimento(
        id_pedido_compra=dados.id_pedido_compra,
        id_usuario_recebimento=usuario_atual.id_usuario,
        data_recebimento=datetime.now(),
        numero_nota_fiscal=dados.numero_nota_fiscal,
        observacao=dados.observacao,
        status="REGISTRADO",
    )
    db.add(novo_recebimento)
    db.flush()

    for item in dados.itens:
        if item.quantidade_recebida <= 0:
            raise HTTPException(
                status_code=400,
                detail="A quantidade recebida deve ser maior que zero.",
            )

        item_pedido = db.query(ItemPedido).filter(
            ItemPedido.id_item_pedido == item.id_item_pedido,
            ItemPedido.id_pedido_compra == dados.id_pedido_compra,
        ).first()
        if not item_pedido:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Item do pedido {item.id_item_pedido} não encontrado.",
            )

        total_recebido = obter_total_recebido_ativo(db, item.id_item_pedido)
        if total_recebido + item.quantidade_recebida > item_pedido.quantidade:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"A quantidade recebida do item {item.id_item_pedido} "
                    "ultrapassa a quantidade pedida."
                ),
            )

        db.add(
            ItemRecebimento(
                id_recebimento=novo_recebimento.id_recebimento,
                id_item_pedido=item.id_item_pedido,
                quantidade_recebida=item.quantidade_recebida,
            )
        )
        db.flush()

    recalcular_status_pedido(db, pedido)

    quantidade_total = sum(
        item.quantidade_recebida for item in dados.itens
    )
    nota_fiscal = dados.numero_nota_fiscal or "não informada"
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        pedido.id_pedido_compra,
        (
            "RECEBIMENTO_TOTAL"
            if pedido.status == "RECEBIDO_TOTAL"
            else "RECEBIMENTO_PARCIAL"
        ),
        (
            f"Recebimento #{novo_recebimento.id_recebimento} registrado com "
            f"{quantidade_total} unidade(s). Nota fiscal: {nota_fiscal}. "
            f"Status do pedido: {pedido.status}."
        ),
    )

    if pedido.status == "RECEBIDO_TOTAL":
        solicitacao = db.query(SolicitacaoCompra).filter(
            SolicitacaoCompra.id_solicitacao == pedido.id_solicitacao
        ).first()
        if solicitacao:
            db.add(
                Notificacao(
                    id_usuario=solicitacao.id_usuario_solicitante,
                    titulo="Pedido recebido",
                    mensagem=(
                        f"O pedido {pedido.id_pedido_compra} foi recebido "
                        "totalmente."
                    ),
                    lida=False,
                    data_hora=datetime.now(),
                )
            )

    db.commit()
    db.refresh(novo_recebimento)
    return montar_recebimento(db, novo_recebimento)


@router.patch(
    "/{id_recebimento}/estornar",
    response_model=RecebimentoResposta,
)
def estornar_recebimento(
    id_recebimento: int,
    dados: RecebimentoEstornar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    ),
):
    recebimento = (
        db.query(Recebimento)
        .filter(Recebimento.id_recebimento == id_recebimento)
        .with_for_update()
        .first()
    )
    if not recebimento:
        raise HTTPException(status_code=404, detail="Recebimento não encontrado.")
    if recebimento.status == "ESTORNADO":
        raise HTTPException(
            status_code=400,
            detail="Este recebimento já foi estornado.",
        )

    pedido = (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.id_pedido_compra == recebimento.id_pedido_compra
        )
        .with_for_update()
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    recebimento.status = "ESTORNADO"
    recebimento.motivo_estorno = dados.motivo
    recebimento.data_estorno = datetime.now()
    recebimento.id_usuario_estorno = usuario_atual.id_usuario
    db.flush()
    recalcular_status_pedido(db, pedido)

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "RECEBIMENTO",
        recebimento.id_recebimento,
        "ESTORNO",
        (
            f"Recebimento {recebimento.id_recebimento} estornado. "
            f"Motivo: {dados.motivo}"
        ),
    )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        pedido.id_pedido_compra,
        "ESTORNO_RECEBIMENTO",
        (
            f"Recebimento #{recebimento.id_recebimento} estornado. "
            f"Motivo: {dados.motivo}. Status do pedido: {pedido.status}."
        ),
    )
    db.commit()
    db.refresh(recebimento)
    return montar_recebimento(db, recebimento)
