from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import exigir_perfis
from app.models.usuario import Usuario
from app.database import get_db
from app.models.produto import Produto
from app.auditoria import listar_campos_alterados, registrar_evento_auditoria
from app.integridade import tratar_conflito_unicidade
from app.schemas.produto import ProdutoCriar, ProdutoResposta, ProdutoAtualizar

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"]
)


@router.get("/", response_model=list[ProdutoResposta])
def listar_produtos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    return db.query(Produto).order_by(
        Produto.id_produto
    ).all()


@router.post(
    "/",
    response_model=ProdutoResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_produto(
    produto: ProdutoCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "ESTOQUE"
        )
    )
):
    produto_existente = (
        db.query(Produto)
        .filter(Produto.codigo == produto.codigo)
        .first()
    )

    if produto_existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe um produto com esse código."
        )

    novo_produto = Produto(
        codigo=produto.codigo,
        nome=produto.nome,
        categoria=produto.categoria,
        marca=produto.marca,
        unidade=produto.unidade,
        descricao=produto.descricao
    )

    db.add(novo_produto)
    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"produto_codigo_key"},
            colunas={"produto.codigo"},
            detalhe="Já existe um produto com esse código.",
        )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PRODUTO",
        novo_produto.id_produto,
        "CADASTRO",
        f"Produto {novo_produto.codigo} - {novo_produto.nome} cadastrado.",
    )
    db.commit()
    db.refresh(novo_produto)

    return novo_produto

@router.get("/{id_produto}", response_model=ProdutoResposta)
def buscar_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    produto = db.query(Produto).filter(
        Produto.id_produto == id_produto
    ).first()

    if not produto:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado."
        )

    return produto

@router.put("/{id_produto}", response_model=ProdutoResposta)
def atualizar_produto(
    id_produto: int,
    dados: ProdutoAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "ESTOQUE"
        )
    )
):
    produto = db.query(Produto).filter(
        Produto.id_produto == id_produto
    ).first()

    if not produto:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado."
        )

    if dados.codigo is not None:
        codigo_existente = db.query(Produto).filter(
            Produto.codigo == dados.codigo,
            Produto.id_produto != id_produto
        ).first()

        if codigo_existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe outro produto com esse código."
            )

    dados_atualizacao = dados.model_dump(exclude_unset=True)

    for campo, valor in dados_atualizacao.items():
        setattr(produto, campo, valor)

    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"produto_codigo_key"},
            colunas={"produto.codigo"},
            detalhe="Já existe outro produto com esse código.",
        )

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PRODUTO",
        produto.id_produto,
        "EDICAO",
        f"Produto {produto.codigo} - {produto.nome} editado. Campos: {listar_campos_alterados(set(dados_atualizacao))}.",
    )

    db.commit()
    db.refresh(produto)

    return produto

@router.patch("/{id_produto}/desativar", response_model=ProdutoResposta)
def desativar_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    produto = db.query(Produto).filter(
        Produto.id_produto == id_produto
    ).first()

    if not produto:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado."
        )

    produto.ativo = False

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PRODUTO",
        produto.id_produto,
        "DESATIVACAO",
        f"Produto {produto.codigo} - {produto.nome} desativado.",
    )

    db.commit()
    db.refresh(produto)

    return produto

@router.patch("/{id_produto}/ativar", response_model=ProdutoResposta)
def ativar_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    produto = db.query(Produto).filter(
        Produto.id_produto == id_produto
    ).first()

    if not produto:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado."
        )

    produto.ativo = True

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "PRODUTO",
        produto.id_produto,
        "ATIVACAO",
        f"Produto {produto.codigo} - {produto.nome} ativado.",
    )

    db.commit()
    db.refresh(produto)

    return produto
