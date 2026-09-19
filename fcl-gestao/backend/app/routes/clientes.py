from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.dependencies import exigir_perfis
from app.database import get_db
from app.models.cliente import Cliente
from app.auditoria import listar_campos_alterados, registrar_evento_auditoria
from app.schemas.cliente import (
    ClienteCriar,
    ClienteResposta,
    ClienteAtualizar
)

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)


@router.get("/", response_model=list[ClienteResposta])
def listar_clientes(
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
    return db.query(Cliente).order_by(
        Cliente.id_cliente
    ).all()

@router.post(
    "/",
    response_model=ClienteResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_cliente(
    cliente: ClienteCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ADMINISTRADOR"
        )
    )
):
    novo_cliente = Cliente(
        nome=cliente.nome,
        cpf_cnpj=cliente.cpf_cnpj,
        telefone=cliente.telefone,
        endereco=cliente.endereco,
        numero=cliente.numero,
        bairro=cliente.bairro,
        cidade=cliente.cidade,
        uf=cliente.uf,
        observacao=cliente.observacao
    )

    db.add(novo_cliente)
    db.flush()
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "CLIENTE",
        novo_cliente.id_cliente,
        "CADASTRO",
        f"Cliente {novo_cliente.nome} cadastrado.",
    )
    db.commit()
    db.refresh(novo_cliente)

    return novo_cliente

@router.get("/{id_cliente}", response_model=ClienteResposta)
def buscar_cliente(
    id_cliente: int,
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
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado."
        )

    return cliente

@router.put("/{id_cliente}", response_model=ClienteResposta)
def atualizar_cliente(
    id_cliente: int,
    dados: ClienteAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ADMINISTRADOR"
        )
    )
):
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado."
        )

    dados_atualizacao = dados.model_dump(exclude_unset=True)

    for campo, valor in dados_atualizacao.items():
        setattr(cliente, campo, valor)

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "CLIENTE",
        cliente.id_cliente,
        "EDICAO",
        f"Cliente {cliente.nome} editado. Campos: {listar_campos_alterados(set(dados_atualizacao))}.",
    )

    db.commit()
    db.refresh(cliente)

    return cliente

@router.patch("/{id_cliente}/desativar", response_model=ClienteResposta)
def desativar_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado."
        )

    cliente.ativo = False

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "CLIENTE",
        cliente.id_cliente,
        "DESATIVACAO",
        f"Cliente {cliente.nome} desativado.",
    )

    db.commit()
    db.refresh(cliente)

    return cliente

@router.patch("/{id_cliente}/ativar", response_model=ClienteResposta)
def ativar_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado."
        )

    cliente.ativo = True

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "CLIENTE",
        cliente.id_cliente,
        "ATIVACAO",
        f"Cliente {cliente.nome} ativado.",
    )

    db.commit()
    db.refresh(cliente)

    return cliente
