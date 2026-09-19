import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()

AMBIENTE = os.getenv("APP_ENV", "development").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL and os.getenv("DB_HOST"):
    usuario_banco = quote_plus(os.getenv("DB_USER", "fcl"))
    senha_banco = quote_plus(os.getenv("DB_PASSWORD", ""))
    host_banco = os.getenv("DB_HOST", "db")
    porta_banco = os.getenv("DB_PORT", "5432")
    nome_banco = os.getenv("DB_NAME", "fcl_gestao")
    DATABASE_URL = (
        f"postgresql+psycopg2://{usuario_banco}:{senha_banco}"
        f"@{host_banco}:{porta_banco}/{nome_banco}"
    )
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chave-temporaria-dev-fcl")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
TOKEN_EXPIRACAO_MINUTOS = int(os.getenv("TOKEN_EXPIRACAO_MINUTOS", "60"))
LOGIN_MAX_TENTATIVAS = int(os.getenv("LOGIN_MAX_TENTATIVAS", "5"))
LOGIN_BLOQUEIO_MINUTOS = int(os.getenv("LOGIN_BLOQUEIO_MINUTOS", "15"))
ARQUIVO_ORFAO_RETENCAO_HORAS = int(
    os.getenv("ARQUIVO_ORFAO_RETENCAO_HORAS", "168")
)
ADMIN_INICIAL_NOME = os.getenv("ADMIN_INICIAL_NOME", "Administrador").strip()
ADMIN_INICIAL_LOGIN = os.getenv("ADMIN_INICIAL_LOGIN", "").strip()
ADMIN_INICIAL_SENHA = os.getenv("ADMIN_INICIAL_SENHA", "")

origens_padrao = "http://localhost:4200,http://127.0.0.1:4200"
CORS_ORIGINS = [
    origem.strip().rstrip("/")
    for origem in os.getenv("CORS_ORIGINS", origens_padrao).split(",")
    if origem.strip()
]

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não encontrada nas variáveis de ambiente.")

if AMBIENTE == "production" and JWT_SECRET_KEY == "chave-temporaria-dev-fcl":
    raise RuntimeError("Defina uma JWT_SECRET_KEY segura no ambiente de produção.")

if ADMIN_INICIAL_SENHA and len(ADMIN_INICIAL_SENHA) < 6:
    raise RuntimeError("ADMIN_INICIAL_SENHA deve possuir pelo menos 6 caracteres.")

if LOGIN_MAX_TENTATIVAS < 1:
    raise RuntimeError("LOGIN_MAX_TENTATIVAS deve ser maior que zero.")

if LOGIN_BLOQUEIO_MINUTOS < 1:
    raise RuntimeError("LOGIN_BLOQUEIO_MINUTOS deve ser maior que zero.")

if ARQUIVO_ORFAO_RETENCAO_HORAS < 1:
    raise RuntimeError("ARQUIVO_ORFAO_RETENCAO_HORAS deve ser maior que zero.")
