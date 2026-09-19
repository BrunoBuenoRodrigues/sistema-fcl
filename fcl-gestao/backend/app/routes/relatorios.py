import csv
import io
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.cliente import Cliente
from app.models.entrega import Entrega
from app.models.fornecedor import Fornecedor
from app.models.item_recebimento import ItemRecebimento
from app.models.item_solicitacao import ItemSolicitacao
from app.models.pedido_fornecedor import PedidoCompra
from app.models.produto import Produto
from app.models.recebimento import Recebimento
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.usuario import Usuario
from app.schemas.relatorio import ResumoGerencialResposta


router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
)


def aplicar_periodo_datetime(query, campo, data_inicio, data_fim):
    if data_inicio is not None:
        query = query.filter(
            campo >= datetime.combine(data_inicio, time.min)
        )

    if data_fim is not None:
        query = query.filter(
            campo <= datetime.combine(data_fim, time.max)
        )

    return query


def aplicar_periodo_data(query, campo, data_inicio, data_fim):
    if data_inicio is not None:
        query = query.filter(campo >= data_inicio)

    if data_fim is not None:
        query = query.filter(campo <= data_fim)

    return query


def converter_contagem_status(registros):
    return {
        status: quantidade
        for status, quantidade in registros
    }


def proteger_celula_csv(valor):
    texto = "" if valor is None else str(valor)

    if texto.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{texto}"

    return texto


def escrever_linha_csv(escritor, *valores):
    escritor.writerow([proteger_celula_csv(valor) for valor in valores])


@router.get("/resumo", response_model=ResumoGerencialResposta)
def obter_resumo_gerencial(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    ),
):
    if (
        data_inicio is not None
        and data_fim is not None
        and data_inicio > data_fim
    ):
        raise HTTPException(
            status_code=400,
            detail="A data inicial não pode ser posterior à data final.",
        )

    solicitacoes_query = db.query(
        SolicitacaoCompra.status,
        func.count(SolicitacaoCompra.id_solicitacao),
    )
    solicitacoes_query = aplicar_periodo_datetime(
        solicitacoes_query,
        SolicitacaoCompra.data_solicitacao,
        data_inicio,
        data_fim,
    )
    solicitacoes_por_status = converter_contagem_status(
        solicitacoes_query.group_by(SolicitacaoCompra.status).all()
    )

    pedidos_query = db.query(
        PedidoCompra.status,
        func.count(PedidoCompra.id_pedido_compra),
    )
    pedidos_query = aplicar_periodo_data(
        pedidos_query,
        PedidoCompra.data_pedido,
        data_inicio,
        data_fim,
    )
    pedidos_por_status = converter_contagem_status(
        pedidos_query.group_by(PedidoCompra.status).all()
    )

    recebimentos_query = db.query(
        func.count(Recebimento.id_recebimento)
    ).filter(Recebimento.status == "REGISTRADO")
    recebimentos_query = aplicar_periodo_datetime(
        recebimentos_query,
        Recebimento.data_recebimento,
        data_inicio,
        data_fim,
    )
    total_recebimentos = recebimentos_query.scalar() or 0

    quantidade_recebida_query = (
        db.query(
            func.coalesce(
                func.sum(ItemRecebimento.quantidade_recebida),
                0,
            )
        )
        .join(
            Recebimento,
            Recebimento.id_recebimento == ItemRecebimento.id_recebimento,
        )
        .filter(Recebimento.status == "REGISTRADO")
    )
    quantidade_recebida_query = aplicar_periodo_datetime(
        quantidade_recebida_query,
        Recebimento.data_recebimento,
        data_inicio,
        data_fim,
    )
    quantidade_recebida = quantidade_recebida_query.scalar() or 0

    entregas_query = db.query(
        Entrega.status,
        func.count(Entrega.id_entrega),
    )
    entregas_query = aplicar_periodo_datetime(
        entregas_query,
        Entrega.data_cadastro,
        data_inicio,
        data_fim,
    )
    entregas_por_status = converter_contagem_status(
        entregas_query.group_by(Entrega.status).all()
    )

    atrasadas_query = db.query(func.count(Entrega.id_entrega)).filter(
        Entrega.data_agendada < date.today(),
        Entrega.status.notin_(["ENTREGUE", "CANCELADA"]),
    )
    atrasadas_query = aplicar_periodo_datetime(
        atrasadas_query,
        Entrega.data_cadastro,
        data_inicio,
        data_fim,
    )
    entregas_atrasadas = atrasadas_query.scalar() or 0

    agendadas_hoje_query = db.query(func.count(Entrega.id_entrega)).filter(
        Entrega.data_agendada == date.today(),
        Entrega.status.notin_(["ENTREGUE", "CANCELADA"]),
    )
    agendadas_hoje_query = aplicar_periodo_datetime(
        agendadas_hoje_query,
        Entrega.data_cadastro,
        data_inicio,
        data_fim,
    )
    entregas_agendadas_hoje = agendadas_hoje_query.scalar() or 0

    produtos_query = (
        db.query(
            Produto.id_produto,
            Produto.nome,
            func.sum(ItemSolicitacao.quantidade).label(
                "quantidade_solicitada"
            ),
        )
        .join(
            ItemSolicitacao,
            ItemSolicitacao.id_produto == Produto.id_produto,
        )
        .join(
            SolicitacaoCompra,
            SolicitacaoCompra.id_solicitacao
            == ItemSolicitacao.id_solicitacao,
        )
    )
    produtos_query = aplicar_periodo_datetime(
        produtos_query,
        SolicitacaoCompra.data_solicitacao,
        data_inicio,
        data_fim,
    )
    produtos_mais_solicitados = (
        produtos_query
        .group_by(Produto.id_produto, Produto.nome)
        .order_by(func.sum(ItemSolicitacao.quantidade).desc())
        .limit(5)
        .all()
    )

    fornecedores_query = (
        db.query(
            Fornecedor.id_fornecedor,
            Fornecedor.nome_fantasia,
            Fornecedor.razao_social,
            func.count(PedidoCompra.id_pedido_compra).label("total_pedidos"),
        )
        .join(
            PedidoCompra,
            PedidoCompra.id_fornecedor == Fornecedor.id_fornecedor,
        )
    )
    fornecedores_query = aplicar_periodo_data(
        fornecedores_query,
        PedidoCompra.data_pedido,
        data_inicio,
        data_fim,
    )
    fornecedores_mais_utilizados = (
        fornecedores_query
        .group_by(
            Fornecedor.id_fornecedor,
            Fornecedor.nome_fantasia,
            Fornecedor.razao_social,
        )
        .order_by(func.count(PedidoCompra.id_pedido_compra).desc())
        .limit(5)
        .all()
    )

    return {
        "gerado_em": datetime.now(),
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
        "solicitacoes": {
            "total": sum(solicitacoes_por_status.values()),
            "por_status": solicitacoes_por_status,
        },
        "pedidos": {
            "total": sum(pedidos_por_status.values()),
            "por_status": pedidos_por_status,
        },
        "recebimentos": {
            "total": total_recebimentos,
            "quantidade_recebida": float(quantidade_recebida),
        },
        "entregas": {
            "total": sum(entregas_por_status.values()),
            "por_status": entregas_por_status,
            "atrasadas": entregas_atrasadas,
            "agendadas_hoje": entregas_agendadas_hoje,
        },
        "cadastros": {
            "produtos_ativos": db.query(Produto).filter(
                Produto.ativo.is_(True)
            ).count(),
            "fornecedores_ativos": db.query(Fornecedor).filter(
                Fornecedor.ativo.is_(True)
            ).count(),
            "clientes_ativos": db.query(Cliente).filter(
                Cliente.ativo.is_(True)
            ).count(),
        },
        "produtos_mais_solicitados": [
            {
                "id_produto": item.id_produto,
                "nome": item.nome,
                "quantidade_solicitada": float(item.quantidade_solicitada),
            }
            for item in produtos_mais_solicitados
        ],
        "fornecedores_mais_utilizados": [
            {
                "id_fornecedor": item.id_fornecedor,
                "nome": item.nome_fantasia or item.razao_social,
                "total_pedidos": item.total_pedidos,
            }
            for item in fornecedores_mais_utilizados
        ],
    }


@router.get("/exportar.csv")
def exportar_resumo_csv(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    ),
):
    resumo = obter_resumo_gerencial(
        data_inicio=data_inicio,
        data_fim=data_fim,
        db=db,
        usuario_atual=usuario_atual,
    )

    arquivo = io.StringIO(newline="")
    escritor = csv.writer(arquivo, delimiter=";", lineterminator="\n")

    escrever_linha_csv(escritor, "Relatório gerencial FCL")
    escrever_linha_csv(
        escritor,
        "Gerado em",
        resumo["gerado_em"].strftime("%d/%m/%Y %H:%M"),
    )
    escrever_linha_csv(
        escritor,
        "Período",
        data_inicio.strftime("%d/%m/%Y") if data_inicio else "Início",
        data_fim.strftime("%d/%m/%Y") if data_fim else "Hoje",
    )
    escrever_linha_csv(escritor)

    escrever_linha_csv(escritor, "Indicador", "Total")
    escrever_linha_csv(
        escritor,
        "Solicitações",
        resumo["solicitacoes"]["total"],
    )
    escrever_linha_csv(escritor, "Pedidos", resumo["pedidos"]["total"])
    escrever_linha_csv(
        escritor,
        "Recebimentos",
        resumo["recebimentos"]["total"],
    )
    escrever_linha_csv(
        escritor,
        "Quantidade recebida",
        resumo["recebimentos"]["quantidade_recebida"],
    )
    escrever_linha_csv(escritor, "Entregas", resumo["entregas"]["total"])
    escrever_linha_csv(
        escritor,
        "Entregas atrasadas",
        resumo["entregas"]["atrasadas"],
    )
    escrever_linha_csv(
        escritor,
        "Entregas agendadas para hoje",
        resumo["entregas"]["agendadas_hoje"],
    )
    escrever_linha_csv(
        escritor,
        "Produtos ativos",
        resumo["cadastros"]["produtos_ativos"],
    )
    escrever_linha_csv(
        escritor,
        "Fornecedores ativos",
        resumo["cadastros"]["fornecedores_ativos"],
    )
    escrever_linha_csv(
        escritor,
        "Clientes ativos",
        resumo["cadastros"]["clientes_ativos"],
    )

    for titulo, chave in (
        ("Solicitações por status", "solicitacoes"),
        ("Pedidos por status", "pedidos"),
        ("Entregas por status", "entregas"),
    ):
        escrever_linha_csv(escritor)
        escrever_linha_csv(escritor, titulo)
        escrever_linha_csv(escritor, "Status", "Quantidade")

        for status_registro, quantidade in resumo[chave]["por_status"].items():
            escrever_linha_csv(
                escritor,
                status_registro.replace("_", " "),
                quantidade,
            )

    escrever_linha_csv(escritor)
    escrever_linha_csv(escritor, "Produtos mais solicitados")
    escrever_linha_csv(escritor, "Produto", "Quantidade solicitada")
    for produto in resumo["produtos_mais_solicitados"]:
        escrever_linha_csv(
            escritor,
            produto["nome"],
            produto["quantidade_solicitada"],
        )

    escrever_linha_csv(escritor)
    escrever_linha_csv(escritor, "Fornecedores com mais pedidos")
    escrever_linha_csv(escritor, "Fornecedor", "Total de pedidos")
    for fornecedor in resumo["fornecedores_mais_utilizados"]:
        escrever_linha_csv(
            escritor,
            fornecedor["nome"],
            fornecedor["total_pedidos"],
        )

    nome_arquivo = f"relatorio-gerencial-fcl-{date.today().isoformat()}.csv"
    conteudo = "\ufeff" + arquivo.getvalue()

    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"'
        },
    )
