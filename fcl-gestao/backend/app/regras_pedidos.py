from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.item_pedido import ItemPedido
from app.models.item_solicitacao import ItemSolicitacao
from app.models.pedido_fornecedor import PedidoCompra
from app.models.solicitacao_compra import SolicitacaoCompra


def obter_quantidades_pedidas_ativas(
    db: Session,
    ids_itens_solicitacao: set[int],
) -> dict[int, object]:
    if not ids_itens_solicitacao:
        return {}

    return dict(
        db.query(
            ItemPedido.id_item_solicitacao,
            func.sum(ItemPedido.quantidade),
        )
        .join(
            PedidoCompra,
            PedidoCompra.id_pedido_compra == ItemPedido.id_pedido_compra,
        )
        .filter(
            ItemPedido.id_item_solicitacao.in_(ids_itens_solicitacao),
            PedidoCompra.status != "CANCELADO",
        )
        .group_by(ItemPedido.id_item_solicitacao)
        .all()
    )


def recalcular_status_solicitacao(
    db: Session,
    solicitacao: SolicitacaoCompra,
) -> None:
    itens = db.query(ItemSolicitacao).filter(
        ItemSolicitacao.id_solicitacao == solicitacao.id_solicitacao
    ).all()
    ids_itens = {item.id_item_solicitacao for item in itens}
    quantidades_pedidas = obter_quantidades_pedidas_ativas(db, ids_itens)

    completa = bool(itens) and all(
        quantidades_pedidas.get(item.id_item_solicitacao, 0)
        >= item.quantidade
        for item in itens
    )
    solicitacao.status = "PEDIDO_REALIZADO" if completa else "APROVADA"
