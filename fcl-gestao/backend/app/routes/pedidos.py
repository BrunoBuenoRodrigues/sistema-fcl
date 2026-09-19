from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exigir_perfis
from app.auditoria import registrar_evento_auditoria
from app.integridade import tratar_conflito_unicidade
from app.models.item_solicitacao import ItemSolicitacao
from app.models.item_pedido import ItemPedido
from app.models.item_recebimento import ItemRecebimento
from app.models.historico import Historico
from app.models.usuario import Usuario
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.fornecedor import Fornecedor
from app.models.pedido_fornecedor import PedidoCompra
from app.models.recebimento import Recebimento
from app.regras_pedidos import (
    obter_quantidades_pedidas_ativas,
    recalcular_status_solicitacao,
)
from app.schemas.pedido_fornecedor import (
    PedidoCompraAtualizar,
    PedidoCompraCancelar,
    PedidoCompraCriar,
    PedidoCompraDetalheResposta,
    PedidoCompraResposta
)


router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos de Compra"]
)
from app.schemas.historico import HistoricoResposta


def montar_detalhe_pedido(db: Session, pedido: PedidoCompra):
    itens = (
        db.query(
            ItemPedido.id_item_pedido,
            ItemPedido.id_item_solicitacao,
            ItemSolicitacao.id_produto,
            ItemPedido.quantidade,
            func.coalesce(
                func.sum(
                    case(
                        (
                            Recebimento.status == "REGISTRADO",
                            ItemRecebimento.quantidade_recebida,
                        ),
                        else_=0,
                    )
                ),
                0
            ).label("quantidade_recebida")
        )
        .join(
            ItemSolicitacao,
            ItemSolicitacao.id_item_solicitacao == ItemPedido.id_item_solicitacao
        )
        .outerjoin(
            ItemRecebimento,
            ItemRecebimento.id_item_pedido == ItemPedido.id_item_pedido
        )
        .outerjoin(
            Recebimento,
            Recebimento.id_recebimento == ItemRecebimento.id_recebimento,
        )
        .filter(ItemPedido.id_pedido_compra == pedido.id_pedido_compra)
        .group_by(
            ItemPedido.id_item_pedido,
            ItemPedido.id_item_solicitacao,
            ItemSolicitacao.id_produto,
            ItemPedido.quantidade
        )
        .order_by(ItemPedido.id_item_pedido)
        .all()
    )

    return {
        "id_pedido_compra": pedido.id_pedido_compra,
        "id_solicitacao": pedido.id_solicitacao,
        "id_fornecedor": pedido.id_fornecedor,
        "numero_pedido": pedido.numero_pedido,
        "data_pedido": pedido.data_pedido,
        "status": pedido.status,
        "observacao": pedido.observacao,
        "motivo_cancelamento": pedido.motivo_cancelamento,
        "data_cancelamento": pedido.data_cancelamento,
        "id_usuario_cancelamento": pedido.id_usuario_cancelamento,
        "itens": [
            {
                "id_item_pedido": item.id_item_pedido,
                "id_item_solicitacao": item.id_item_solicitacao,
                "id_produto": item.id_produto,
                "quantidade": item.quantidade,
                "quantidade_recebida": item.quantidade_recebida,
                "saldo_pendente": item.quantidade - item.quantidade_recebida
            }
            for item in itens
        ]
    }

@router.get(
    "/",
    response_model=list[PedidoCompraDetalheResposta]
)
def listar_pedidos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "ESTOQUE"
        )
    )
):
    pedidos = db.query(PedidoCompra).order_by(
        PedidoCompra.id_pedido_compra.desc()
    ).all()

    return [montar_detalhe_pedido(db, pedido) for pedido in pedidos]

@router.post(
    "/",
    response_model=PedidoCompraResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_pedido(
    dados: PedidoCompraCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == dados.id_fornecedor
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado."
        )

    if not fornecedor.ativo:
        raise HTTPException(
            status_code=400,
            detail="Não é possível criar pedido para fornecedor inativo."
        )

    pedido_existente = db.query(PedidoCompra).filter(
        PedidoCompra.numero_pedido == dados.numero_pedido
    ).first()

    solicitacao = (
        db.query(SolicitacaoCompra)
        .filter(SolicitacaoCompra.id_solicitacao == dados.id_solicitacao)
        .with_for_update()
        .first()
    )

    if not solicitacao:
        raise HTTPException(
            status_code=404,
            detail="Solicitação não encontrada."
        )

    if solicitacao.status not in ("APROVADA", "PEDIDO_REALIZADO"):
        raise HTTPException(
            status_code=400,
            detail="Somente solicitações APROVADAS podem gerar pedidos."
        )

    itens_solicitacao = db.query(ItemSolicitacao).filter(
        ItemSolicitacao.id_solicitacao == dados.id_solicitacao
    ).all()

    if not itens_solicitacao:
        raise HTTPException(
            status_code=400,
            detail="Não é possível criar pedido para uma solicitação sem itens."
        )

    ids_itens_solicitacao = {
        item.id_item_solicitacao for item in itens_solicitacao
    }
    quantidades_ja_pedidas = obter_quantidades_pedidas_ativas(
        db,
        ids_itens_solicitacao,
    )
    saldos = {
        item.id_item_solicitacao: (
            item.quantidade
            - quantidades_ja_pedidas.get(item.id_item_solicitacao, 0)
        )
        for item in itens_solicitacao
    }

    if dados.itens is None:
        itens_selecionados = [
            (item.id_item_solicitacao, saldo)
            for item in itens_solicitacao
            if (saldo := saldos[item.id_item_solicitacao]) > 0
        ]
    else:
        itens_selecionados = [
            (item.id_item_solicitacao, item.quantidade)
            for item in dados.itens
        ]

    if not itens_selecionados:
        raise HTTPException(
            status_code=400,
            detail="A solicitação não possui saldo disponível para novo pedido."
        )

    for id_item_solicitacao, quantidade in itens_selecionados:
        if id_item_solicitacao not in ids_itens_solicitacao:
            raise HTTPException(
                status_code=400,
                detail="O item informado não pertence à solicitação."
            )

        if quantidade > saldos[id_item_solicitacao]:
            raise HTTPException(
                status_code=400,
                detail="A quantidade do pedido ultrapassa o saldo da solicitação."
            )

    if pedido_existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe um pedido com este número."
        )

    if dados.data_pedido > date.today():
        raise HTTPException(
            status_code=400,
            detail="A data do pedido não pode ser futura."
        )

    novo_pedido = PedidoCompra(
        id_solicitacao=dados.id_solicitacao,
        id_fornecedor=dados.id_fornecedor,
        numero_pedido=dados.numero_pedido,
        data_pedido=dados.data_pedido,
        status="CRIADO",
        observacao=dados.observacao
    )

    db.add(novo_pedido)
    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"uq_pedido_compra_numero_pedido"},
            colunas={"pedido_compra.numero_pedido"},
            detalhe="Já existe um pedido com este número.",
        )

    for id_item_solicitacao, quantidade in itens_selecionados:
        novo_item_pedido = ItemPedido(
            id_pedido_compra=novo_pedido.id_pedido_compra,
            id_item_solicitacao=id_item_solicitacao,
            quantidade=quantidade
        )

        db.add(novo_item_pedido)
        saldos[id_item_solicitacao] -= quantidade

    solicitacao.status = (
        "PEDIDO_REALIZADO"
        if all(saldo <= 0 for saldo in saldos.values())
        else "APROVADA"
    )

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "SOLICITACAO",
        solicitacao.id_solicitacao,
        (
            "PEDIDO_REALIZADO"
            if solicitacao.status == "PEDIDO_REALIZADO"
            else "PEDIDO_CRIADO"
        ),
        (
            f"Pedido {novo_pedido.numero_pedido or novo_pedido.id_pedido_compra} "
            "criado a partir da solicitação."
        ),
    )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        novo_pedido.id_pedido_compra,
        "CADASTRO",
        (
            f"Pedido {novo_pedido.numero_pedido or novo_pedido.id_pedido_compra} "
            f"criado a partir da solicitação #{solicitacao.id_solicitacao} "
            f"com {len(itens_selecionados)} item(ns)."
        ),
    )

    db.commit()
    db.refresh(novo_pedido)

    return novo_pedido

@router.get(
    "/{id_pedido_compra}",
    response_model=PedidoCompraDetalheResposta
)
def buscar_pedido(
    id_pedido_compra: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "ESTOQUE"
        )
    )
):
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id_pedido_compra == id_pedido_compra
    ).first()

    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado."
        )

    return montar_detalhe_pedido(db, pedido)


@router.get(
    "/{id_pedido_compra}/historico",
    response_model=list[HistoricoResposta],
)
def listar_historico_pedido(
    id_pedido_compra: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR", "ESTOQUE")
    ),
):
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id_pedido_compra == id_pedido_compra
    ).first()

    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado.",
        )

    return db.query(Historico).filter(
        Historico.tipo_registro == "PEDIDO",
        Historico.id_registro == id_pedido_compra,
    ).order_by(
        Historico.data_hora.asc(),
        Historico.id_historico.asc(),
    ).all()


@router.put(
    "/{id_pedido_compra}",
    response_model=PedidoCompraDetalheResposta,
)
def atualizar_pedido(
    id_pedido_compra: int,
    dados: PedidoCompraAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfis("ADMINISTRADOR")),
):
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id_pedido_compra == id_pedido_compra)
        .with_for_update()
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if pedido.status != "CRIADO":
        raise HTTPException(
            status_code=400,
            detail="Somente pedidos com status CRIADO podem ser editados.",
        )

    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == dados.id_fornecedor
    ).first()
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    if not fornecedor.ativo:
        raise HTTPException(
            status_code=400,
            detail="Não é possível utilizar um fornecedor inativo.",
        )

    pedido_com_mesmo_numero = db.query(PedidoCompra).filter(
        PedidoCompra.numero_pedido == dados.numero_pedido,
        PedidoCompra.id_pedido_compra != id_pedido_compra,
    ).first()
    if pedido_com_mesmo_numero:
        raise HTTPException(
            status_code=400,
            detail="Já existe um pedido com este número.",
        )
    if dados.data_pedido > date.today():
        raise HTTPException(
            status_code=400,
            detail="A data do pedido não pode ser futura.",
        )

    solicitacao = (
        db.query(SolicitacaoCompra)
        .filter(SolicitacaoCompra.id_solicitacao == pedido.id_solicitacao)
        .with_for_update()
        .first()
    )
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    itens_solicitacao = db.query(ItemSolicitacao).filter(
        ItemSolicitacao.id_solicitacao == pedido.id_solicitacao
    ).all()
    ids_itens_solicitacao = {
        item.id_item_solicitacao for item in itens_solicitacao
    }
    itens_atuais = db.query(ItemPedido).filter(
        ItemPedido.id_pedido_compra == id_pedido_compra
    ).all()
    quantidades_atuais = {
        item.id_item_solicitacao: item.quantidade for item in itens_atuais
    }
    quantidades_pedidas = obter_quantidades_pedidas_ativas(
        db,
        ids_itens_solicitacao,
    )
    saldos_editaveis = {
        item.id_item_solicitacao: (
            item.quantidade
            - quantidades_pedidas.get(item.id_item_solicitacao, 0)
            + quantidades_atuais.get(item.id_item_solicitacao, 0)
        )
        for item in itens_solicitacao
    }

    for item in dados.itens:
        if item.id_item_solicitacao not in ids_itens_solicitacao:
            raise HTTPException(
                status_code=400,
                detail="O item informado não pertence à solicitação.",
            )
        if item.quantidade > saldos_editaveis[item.id_item_solicitacao]:
            raise HTTPException(
                status_code=400,
                detail="A quantidade do pedido ultrapassa o saldo da solicitação.",
            )

    numero_anterior = pedido.numero_pedido or str(pedido.id_pedido_compra)
    pedido.id_fornecedor = dados.id_fornecedor
    pedido.numero_pedido = dados.numero_pedido
    pedido.data_pedido = dados.data_pedido
    pedido.observacao = dados.observacao

    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"uq_pedido_compra_numero_pedido"},
            colunas={"pedido_compra.numero_pedido"},
            detalhe="Já existe um pedido com este número.",
        )

    db.query(ItemPedido).filter(
        ItemPedido.id_pedido_compra == id_pedido_compra
    ).delete(synchronize_session="fetch")
    db.flush()
    for item in dados.itens:
        db.add(
            ItemPedido(
                id_pedido_compra=id_pedido_compra,
                id_item_solicitacao=item.id_item_solicitacao,
                quantidade=item.quantidade,
            )
        )
    db.flush()
    recalcular_status_solicitacao(db, solicitacao)

    descricao = (
        f"Pedido {numero_anterior} editado para {pedido.numero_pedido}, com "
        f"fornecedor #{pedido.id_fornecedor} e {len(dados.itens)} item(ns)."
    )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        pedido.id_pedido_compra,
        "EDICAO",
        descricao,
    )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "SOLICITACAO",
        solicitacao.id_solicitacao,
        "PEDIDO_EDITADO",
        descricao,
    )
    db.commit()
    db.refresh(pedido)

    return montar_detalhe_pedido(db, pedido)


@router.patch(
    "/{id_pedido_compra}/aguardando-recebimento",
    response_model=PedidoCompraResposta
)
def marcar_aguardando_recebimento(
    id_pedido_compra: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id_pedido_compra == id_pedido_compra
    ).with_for_update().first()

    if not pedido:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado."
        )

    if pedido.status != "CRIADO":
        raise HTTPException(
            status_code=400,
            detail="Somente pedidos com status CRIADO podem avançar para AGUARDANDO_RECEBIMENTO."
        )

    possui_itens = db.query(ItemPedido).filter(
        ItemPedido.id_pedido_compra == id_pedido_compra
    ).first()

    if not possui_itens:
        raise HTTPException(
            status_code=400,
            detail="O pedido não possui itens e não pode ser enviado para recebimento."
        )

    pedido.status = "AGUARDANDO_RECEBIMENTO"

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        pedido.id_pedido_compra,
        "ENVIO_RECEBIMENTO",
        (
            f"Pedido {pedido.numero_pedido or pedido.id_pedido_compra} enviado "
            "para recebimento."
        ),
    )

    db.commit()
    db.refresh(pedido)

    return pedido


@router.patch(
    "/{id_pedido_compra}/cancelar",
    response_model=PedidoCompraResposta,
)
def cancelar_pedido(
    id_pedido_compra: int,
    dados: PedidoCompraCancelar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    ),
):
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id_pedido_compra == id_pedido_compra)
        .with_for_update()
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status not in ("CRIADO", "AGUARDANDO_RECEBIMENTO"):
        raise HTTPException(
            status_code=400,
            detail="Somente pedidos ainda não recebidos podem ser cancelados.",
        )

    possui_recebimento = db.query(Recebimento.id_recebimento).filter(
        Recebimento.id_pedido_compra == id_pedido_compra,
        Recebimento.status == "REGISTRADO",
    ).first()
    if possui_recebimento:
        raise HTTPException(
            status_code=400,
            detail="O pedido possui recebimento registrado e não pode ser cancelado.",
        )

    agora = datetime.now()
    pedido.status = "CANCELADO"
    pedido.motivo_cancelamento = dados.motivo
    pedido.data_cancelamento = agora
    pedido.id_usuario_cancelamento = usuario_atual.id_usuario
    db.flush()
    solicitacao = db.query(SolicitacaoCompra).filter(
        SolicitacaoCompra.id_solicitacao == pedido.id_solicitacao
    ).first()
    if solicitacao:
        recalcular_status_solicitacao(db, solicitacao)
        registrar_evento_auditoria(
            db,
            usuario_atual,
            "SOLICITACAO",
            solicitacao.id_solicitacao,
            "PEDIDO_CANCELADO",
            (
                f"Pedido {pedido.numero_pedido or pedido.id_pedido_compra} "
                "cancelado; as quantidades retornaram ao saldo da solicitação. "
                f"Motivo: {dados.motivo}"
            ),
        )

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PEDIDO",
        pedido.id_pedido_compra,
        "CANCELAMENTO",
        (
            f"Pedido {pedido.numero_pedido or pedido.id_pedido_compra} cancelado. "
            f"Motivo: {dados.motivo}"
        ),
    )
    db.commit()
    db.refresh(pedido)

    return pedido
