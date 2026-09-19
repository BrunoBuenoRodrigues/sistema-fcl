from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import exigir_perfis, get_usuario_atual
from app.database import get_db
from app.auditoria import listar_campos_alterados, registrar_evento_auditoria
from app.integridade import tratar_conflito_unicidade
from app.models.usuario import Usuario
from app.schemas.auth import TokenResposta
from app.schemas.usuario import (
    AlterarPropriaSenha,
    UsuarioCriar,
    UsuarioResposta,
    UsuarioResumoResposta,
    UsuarioAtualizar
)
from app.security import criar_token_acesso, gerar_hash_senha, verificar_senha

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


@router.get("/", response_model=list[UsuarioResposta])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    return db.query(Usuario).order_by(
        Usuario.id_usuario
    ).all()

@router.post(
    "/",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar_usuario(
    usuario: UsuarioCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfis("ADMINISTRADOR"))
):
    usuario_existente = (
        db.query(Usuario)
        .filter(Usuario.login == usuario.login)
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe um usuário com esse login."
        )

    perfis_validos = [
        "FUNCIONARIO",
        "ESTOQUE",
        "ADMINISTRADOR",
        "ENTREGADOR"
    ]

    if usuario.perfil not in perfis_validos:
        raise HTTPException(
            status_code=400,
            detail="Perfil de usuário inválido."
        )

    novo_usuario = Usuario(
        nome=usuario.nome,
        login=usuario.login,
        senha=gerar_hash_senha(usuario.senha),
        perfil=usuario.perfil
    )

    db.add(novo_usuario)
    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"usuario_login_key"},
            colunas={"usuario.login"},
            detalhe="Já existe um usuário com esse login.",
        )
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "USUARIO",
        novo_usuario.id_usuario,
        "CADASTRO",
        f"Usuário {novo_usuario.nome} cadastrado com perfil {novo_usuario.perfil}.",
    )
    db.commit()
    db.refresh(novo_usuario)

    return novo_usuario


@router.get("/resumo/", response_model=list[UsuarioResumoResposta])
def listar_resumo_usuarios(
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
    return db.query(Usuario).order_by(
        Usuario.nome
    ).all()


@router.patch(
    "/minha-conta/senha",
    response_model=TokenResposta,
)
def alterar_propria_senha(
    dados: AlterarPropriaSenha,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
):
    if not verificar_senha(dados.senha_atual, usuario_atual.senha):
        raise HTTPException(
            status_code=400,
            detail="A senha atual está incorreta.",
        )

    if dados.nova_senha != dados.confirmar_nova_senha:
        raise HTTPException(
            status_code=400,
            detail="A confirmação da nova senha não confere.",
        )

    if verificar_senha(dados.nova_senha, usuario_atual.senha):
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ser diferente da senha atual.",
        )

    usuario_atual.senha = gerar_hash_senha(dados.nova_senha)
    usuario_atual.versao_sessao += 1
    registrar_evento_auditoria(
        db,
        usuario_atual,
        "USUARIO",
        usuario_atual.id_usuario,
        "ALTERACAO_SENHA",
        "O usuário alterou a própria senha.",
    )
    db.commit()
    db.refresh(usuario_atual)

    return {
        "access_token": criar_token_acesso(
            id_usuario=usuario_atual.id_usuario,
            login=usuario_atual.login,
            perfil=usuario_atual.perfil,
            versao_sessao=usuario_atual.versao_sessao,
        ),
        "token_type": "bearer",
        "usuario": usuario_atual.nome,
        "perfil": usuario_atual.perfil,
    }

@router.get("/{id_usuario}", response_model=UsuarioResposta)
def buscar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    return usuario
@router.put("/{id_usuario}", response_model=UsuarioResposta)
def atualizar_usuario(
    id_usuario: int,
    dados: UsuarioAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if (
        usuario.id_usuario == usuario_atual.id_usuario
        and dados.perfil is not None
        and dados.perfil != usuario.perfil
    ):
        raise HTTPException(
            status_code=400,
            detail="Você não pode alterar o perfil da própria conta."
        )

    if (
        usuario.id_usuario == usuario_atual.id_usuario
        and dados.ativo is False
    ):
        raise HTTPException(
            status_code=400,
            detail="Você não pode desativar a própria conta."
        )

    if dados.login is not None:
        login_existente = db.query(Usuario).filter(
            Usuario.login == dados.login,
            Usuario.id_usuario != id_usuario
        ).first()

        if login_existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe outro usuário com esse login."
            )

    if dados.perfil is not None:
        perfis_validos = [
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        ]

        if dados.perfil not in perfis_validos:
            raise HTTPException(
                status_code=400,
                detail="Perfil de usuário inválido."
            )

    dados_atualizacao = dados.model_dump(exclude_unset=True)

    if "senha" in dados_atualizacao:
        dados_atualizacao["senha"] = gerar_hash_senha(
            dados_atualizacao["senha"]
        )
        usuario.versao_sessao += 1

    for campo, valor in dados_atualizacao.items():
        setattr(usuario, campo, valor)

    try:
        db.flush()
    except IntegrityError as erro:
        tratar_conflito_unicidade(
            db,
            erro,
            restricoes={"usuario_login_key"},
            colunas={"usuario.login"},
            detalhe="Já existe outro usuário com esse login.",
        )

    acao = "EDICAO"
    if set(dados_atualizacao) == {"ativo"}:
        acao = "ATIVACAO" if usuario.ativo else "DESATIVACAO"

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "USUARIO",
        usuario.id_usuario,
        acao,
        f"Usuário {usuario.nome} alterado. Campos: {listar_campos_alterados(set(dados_atualizacao))}.",
    )

    db.commit()
    db.refresh(usuario)

    return usuario
@router.patch("/{id_usuario}/desativar", response_model=UsuarioResposta)
def desativar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    )
):
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if usuario.id_usuario == usuario_atual.id_usuario:
        raise HTTPException(
            status_code=400,
            detail="Você não pode desativar a própria conta."
        )

    usuario.ativo = False

    registrar_evento_auditoria(
        db,
        usuario_atual,
        "USUARIO",
        usuario.id_usuario,
        "DESATIVACAO",
        f"Usuário {usuario.nome} desativado.",
    )

    db.commit()
    db.refresh(usuario)

    return usuario
