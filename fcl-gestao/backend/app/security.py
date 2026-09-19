from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from datetime import datetime, timedelta, timezone

import jwt

from app.config import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    TOKEN_EXPIRACAO_MINUTOS,
)

password_hash = PasswordHash.recommended()

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = JWT_ALGORITHM
TEMPO_TOKEN_MINUTOS = TOKEN_EXPIRACAO_MINUTOS


def gerar_hash_senha(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return password_hash.verify(senha, senha_hash)
    except PwdlibError:
        return False

def criar_token_acesso(
    id_usuario: int,
    login: str,
    perfil: str,
    versao_sessao: int = 1,
) -> str:

    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=TEMPO_TOKEN_MINUTOS
    )
    dados_token = {
        "sub": str(id_usuario),
        "login": login,
        "perfil": perfil,
        "sessao": versao_sessao,
        "exp": expiracao
    }

    return jwt.encode(
        dados_token,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def decodificar_token(token: str):
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )
