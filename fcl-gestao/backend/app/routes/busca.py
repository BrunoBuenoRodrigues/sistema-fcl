from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.cliente import Cliente
from app.models.entrega import Entrega
from app.models.fornecedor import Fornecedor
from app.models.pedido_fornecedor import PedidoCompra
from app.models.produto import Produto
from app.models.solicitacao_compra import SolicitacaoCompra
from app.models.usuario import Usuario


router = APIRouter(prefix="/busca-global", tags=["Busca global"])


@router.get("")
def buscar_globalmente(
    q: str = Query(min_length=2, max_length=80),
    limite: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
):
    """Busca enxuta, limitada e filtrada pelas permissões já usadas nas rotas."""
    consulta = q.strip()
    if len(consulta) < 2:
        return {"consulta": consulta, "grupos": []}
    termo = f"%{consulta}%"
    grupos: list[dict] = []

    if usuario_atual.perfil in {"ADMINISTRADOR", "FUNCIONARIO", "ESTOQUE"}:
        solicitacoes = (
            db.query(SolicitacaoCompra)
            .filter(or_(
                cast(SolicitacaoCompra.id_solicitacao, String).ilike(termo),
                SolicitacaoCompra.motivo.ilike(termo),
                SolicitacaoCompra.observacao.ilike(termo),
            ))
            .order_by(SolicitacaoCompra.id_solicitacao.desc())
            .limit(limite)
            .all()
        )
        grupos.append({
            "tipo": "solicitacao",
            "rotulo": "Solicitações",
            "resultados": [
                {
                    "id": item.id_solicitacao,
                    "titulo": f"Solicitação #{item.id_solicitacao}",
                    "subtitulo": item.motivo,
                    "status": item.status,
                }
                for item in solicitacoes
            ],
        })

    if usuario_atual.perfil in {"ADMINISTRADOR", "ESTOQUE"}:
        pedidos = (
            db.query(PedidoCompra)
            .filter(or_(
                cast(PedidoCompra.id_pedido_compra, String).ilike(termo),
                PedidoCompra.numero_pedido.ilike(termo),
                PedidoCompra.observacao.ilike(termo),
            ))
            .order_by(PedidoCompra.id_pedido_compra.desc())
            .limit(limite)
            .all()
        )
        grupos.append({
            "tipo": "pedido",
            "rotulo": "Pedidos",
            "resultados": [
                {
                    "id": item.id_pedido_compra,
                    "titulo": item.numero_pedido or f"Pedido #{item.id_pedido_compra}",
                    "subtitulo": f"Pedido de compra #{item.id_pedido_compra}",
                    "status": item.status,
                }
                for item in pedidos
            ],
        })

    consulta_entregas = db.query(Entrega, Cliente).join(
        Cliente, Cliente.id_cliente == Entrega.id_cliente
    )
    if usuario_atual.perfil == "ENTREGADOR":
        consulta_entregas = consulta_entregas.filter(
            Entrega.id_entregador == usuario_atual.id_usuario
        )
    entregas = (
        consulta_entregas
        .filter(or_(
            cast(Entrega.id_entrega, String).ilike(termo),
            Cliente.nome.ilike(termo),
            Entrega.observacao.ilike(termo),
        ))
        .order_by(Entrega.id_entrega.desc())
        .limit(limite)
        .all()
    )
    grupos.append({
        "tipo": "entrega",
        "rotulo": "Entregas" if usuario_atual.perfil != "ENTREGADOR" else "Minhas entregas",
        "resultados": [
            {
                "id": entrega.id_entrega,
                "titulo": f"Entrega #{entrega.id_entrega}",
                "subtitulo": cliente.nome,
                "status": entrega.status,
            }
            for entrega, cliente in entregas
        ],
    })

    clientes = (
        db.query(Cliente)
        .filter(or_(
            cast(Cliente.id_cliente, String).ilike(termo),
            Cliente.nome.ilike(termo),
            Cliente.cidade.ilike(termo),
        ))
        .order_by(Cliente.nome)
        .limit(limite)
        .all()
    )
    grupos.append({
        "tipo": "cliente",
        "rotulo": "Clientes",
        "resultados": [
            {
                "id": item.id_cliente,
                "titulo": item.nome,
                "subtitulo": f"{item.cidade}/{item.uf}",
                "status": "ATIVO" if item.ativo else "INATIVO",
            }
            for item in clientes
        ],
    })

    if usuario_atual.perfil in {"ADMINISTRADOR", "FUNCIONARIO", "ESTOQUE"}:
        produtos = (
            db.query(Produto)
            .filter(or_(
                cast(Produto.id_produto, String).ilike(termo),
                Produto.codigo.ilike(termo),
                Produto.nome.ilike(termo),
            ))
            .order_by(Produto.nome)
            .limit(limite)
            .all()
        )
        fornecedores = (
            db.query(Fornecedor)
            .filter(or_(
                cast(Fornecedor.id_fornecedor, String).ilike(termo),
                Fornecedor.razao_social.ilike(termo),
                Fornecedor.nome_fantasia.ilike(termo),
            ))
            .order_by(Fornecedor.razao_social)
            .limit(limite)
            .all()
        )
        grupos.extend([
            {
                "tipo": "produto",
                "rotulo": "Produtos",
                "resultados": [
                    {
                        "id": item.id_produto,
                        "titulo": item.nome,
                        "subtitulo": item.codigo,
                        "status": "ATIVO" if item.ativo else "INATIVO",
                    }
                    for item in produtos
                ],
            },
            {
                "tipo": "fornecedor",
                "rotulo": "Fornecedores",
                "resultados": [
                    {
                        "id": item.id_fornecedor,
                        "titulo": item.nome_fantasia or item.razao_social,
                        "subtitulo": item.razao_social,
                        "status": "ATIVO" if item.ativo else "INATIVO",
                    }
                    for item in fornecedores
                ],
            },
        ])

    if usuario_atual.perfil == "ADMINISTRADOR":
        usuarios = (
            db.query(Usuario)
            .filter(or_(
                cast(Usuario.id_usuario, String).ilike(termo),
                Usuario.nome.ilike(termo),
                Usuario.login.ilike(termo),
            ))
            .order_by(Usuario.nome)
            .limit(limite)
            .all()
        )
        grupos.append({
            "tipo": "usuario",
            "rotulo": "Usuários",
            "resultados": [
                {
                    "id": item.id_usuario,
                    "titulo": item.nome,
                    "subtitulo": item.login,
                    "status": "ATIVO" if item.ativo else "INATIVO",
                }
                for item in usuarios
            ],
        })

    return {
        "consulta": consulta,
        "grupos": [grupo for grupo in grupos if grupo["resultados"]],
    }
