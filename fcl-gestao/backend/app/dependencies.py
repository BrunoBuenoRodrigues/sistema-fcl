from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from app.database import get_db
from app.models.usuario import Usuario
from app.security import decodificar_token


security = HTTPBearer()


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credenciais.credentials

    try:
        dados_token = decodificar_token(token)

        id_usuario = int(dados_token.get("sub"))

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado."
        )

    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado."
        )

    try:
        versao_sessao_token = int(dados_token.get("sessao", 1))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida. Entre novamente.",
        )

    if versao_sessao_token != usuario.versao_sessao:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada após alteração de senha. Entre novamente.",
        )

    return usuario

def exigir_perfis(*perfis_permitidos):
    def verificar_perfil(
        usuario: Usuario = Depends(get_usuario_atual)
    ):
        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para realizar esta ação."
            )

        return usuario

    return verificar_perfil
