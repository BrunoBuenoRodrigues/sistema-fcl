from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import exigir_perfis
from app.models.usuario import Usuario
from app.database import get_db
from app.models.fornecedor import Fornecedor
from app.auditoria import listar_campos_alterados, registrar_evento_auditoria
from app.integridade import tratar_conflito_unicidade
from app.schemas.fornecedor import (
    FornecedorCriar,
    FornecedorResposta,
    FornecedorAtualizar
)

router = APIRouter(
    prefix="/fornecedores",
    tags=["Fornecedores"]
)


@router.get("/", response_model=list[FornecedorResposta])
def listar_fornecedores(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    return db.query(Fornecedor).order_by(
        Fornecedor.id_fornecedor
    ).all()

@router.post(
    "/",
    response_model=FornecedorResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_fornecedor(
    fornecedor: FornecedorCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    if fornecedor.cnpj is not None:
        fornecedor_existente = (
            db.query(Fornecedor)
            .filter(Fornecedor.cnpj == fornecedor.cnpj)
            .first()
        )

        if fornecedor_existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe um fornecedor com esse CNPJ."
            )

    novo_fornecedor = Fornecedor(
        razao_social=fornecedor.razao_social,
        nome_fantasia=fornecedor.nome_fantasia,
        cnpj=fornecedor.cnpj,
        telefone=fornecedor.telefone,
        email=fornecedor.email
    )

    db.add(novo_fornecedor)
    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"fornecedor_cnpj_key"},
            colunas={"fornecedor.cnpj"},
            detalhe="Já existe um fornecedor com esse CNPJ.",
        )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "FORNECEDOR",
        novo_fornecedor.id_fornecedor,
        "CADASTRO",
        f"Fornecedor {novo_fornecedor.razao_social} cadastrado.",
    )
    db.commit()
    db.refresh(novo_fornecedor)

    return novo_fornecedor

@router.get("/{id_fornecedor}", response_model=FornecedorResposta)
def buscar_fornecedor(
    id_fornecedor: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ADMINISTRADOR",
            "FUNCIONARIO",
            "ESTOQUE"
        )
    )
):
    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == id_fornecedor
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado."
        )

    return fornecedor

@router.put("/{id_fornecedor}", response_model=FornecedorResposta)
def atualizar_fornecedor(
    id_fornecedor: int,
    dados: FornecedorAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == id_fornecedor
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado."
        )

    if dados.cnpj is not None:
        cnpj_existente = db.query(Fornecedor).filter(
            Fornecedor.cnpj == dados.cnpj,
            Fornecedor.id_fornecedor != id_fornecedor
        ).first()

        if cnpj_existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe outro fornecedor com esse CNPJ."
            )

    dados_atualizacao = dados.model_dump(exclude_unset=True)

    for campo, valor in dados_atualizacao.items():
        setattr(fornecedor, campo, valor)

    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"fornecedor_cnpj_key"},
            colunas={"fornecedor.cnpj"},
            detalhe="Já existe outro fornecedor com esse CNPJ.",
        )

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "FORNECEDOR",
        fornecedor.id_fornecedor,
        "EDICAO",
        f"Fornecedor {fornecedor.razao_social} editado. Campos: {listar_campos_alterados(set(dados_atualizacao))}.",
    )

    db.commit()
    db.refresh(fornecedor)

    return fornecedor

@router.patch("/{id_fornecedor}/desativar", response_model=FornecedorResposta)
def desativar_fornecedor(
    id_fornecedor: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == id_fornecedor
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado."
        )

    fornecedor.ativo = False

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "FORNECEDOR",
        fornecedor.id_fornecedor,
        "DESATIVACAO",
        f"Fornecedor {fornecedor.razao_social} desativado.",
    )

    db.commit()
    db.refresh(fornecedor)

    return fornecedor

@router.patch("/{id_fornecedor}/ativar", response_model=FornecedorResposta)
def ativar_fornecedor(
    id_fornecedor: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    fornecedor = db.query(Fornecedor).filter(
        Fornecedor.id_fornecedor == id_fornecedor
    ).first()

    if not fornecedor:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado."
        )

    fornecedor.ativo = True

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "FORNECEDOR",
        fornecedor.id_fornecedor,
        "ATIVACAO",
        f"Fornecedor {fornecedor.razao_social} ativado.",
    )

    db.commit()
    db.refresh(fornecedor)

    return fornecedor
