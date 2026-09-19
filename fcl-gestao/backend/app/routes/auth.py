from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import LOGIN_BLOQUEIO_MINUTOS, LOGIN_MAX_TENTATIVAS
from app.database import get_db
from app.limitador_login import LimitadorLogin
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResposta
from app.security import verificar_senha, criar_token_acesso
from app.dependencies import get_usuario_atual


router = APIRouter(
    tags=["Autenticação"]
)

limitador_login = LimitadorLogin(
    max_tentativas=LOGIN_MAX_TENTATIVAS,
    bloqueio_segundos=LOGIN_BLOQUEIO_MINUTOS * 60,
)


def chave_tentativa(request: Request, login: str) -> str:
    encaminhado = request.headers.get("x-real-ip", "")
    if not encaminhado:
        encaminhado = request.headers.get("x-forwarded-for", "")
    ip_cliente = encaminhado.split(",", 1)[0].strip()

    if not ip_cliente:
        ip_cliente = request.client.host if request.client else "desconhecido"

    return f"{ip_cliente}:{login.strip().lower()}"


def verificar_bloqueio(chave: str) -> None:
    segundos = limitador_login.tempo_bloqueio(chave)
    if segundos:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente.",
            headers={"Retry-After": str(segundos)},
        )


@router.post("/login", response_model=TokenResposta)
def login(
    dados: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    chave = chave_tentativa(request, dados.login)
    verificar_bloqueio(chave)

    usuario = db.query(Usuario).filter(
        Usuario.login == dados.login
    ).first()

    if not usuario:
        limitador_login.registrar_falha(chave)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha inválidos."
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado."
        )

    if not verificar_senha(dados.senha, usuario.senha):
        limitador_login.registrar_falha(chave)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha inválidos."
        )

    limitador_login.registrar_sucesso(chave)

    token = criar_token_acesso(
        id_usuario=usuario.id_usuario,
        login=usuario.login,
        perfil=usuario.perfil,
        versao_sessao=usuario.versao_sessao,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": usuario.nome,
        "perfil": usuario.perfil
    }

@router.get("/me")
def usuario_logado(
    usuario: Usuario = Depends(get_usuario_atual)
):
    return {
        "id_usuario": usuario.id_usuario,
        "nome": usuario.nome,
        "login": usuario.login,
        "perfil": usuario.perfil,
        "ativo": usuario.ativo
    }
