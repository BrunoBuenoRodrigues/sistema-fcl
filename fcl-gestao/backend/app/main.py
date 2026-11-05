from contextlib import asynccontextmanager
import logging

from app.armazenamento_arquivos import limpar_arquivos_orfaos
from app.config import ARQUIVO_ORFAO_RETENCAO_HORAS
from app.routes.fornecedores import router as fornecedores_router
from app.routes.produtos import router as produtos_router
from app.routes.clientes import router as clientes_router
from app.routes.usuarios import router as usuarios_router
from app.routes.auth import router as auth_router
from app.routes.solicitacoes import router as solicitacoes_router
from app.routes.pedidos import router as pedidos_router
from app.routes.recebimentos import router as recebimentos_router
from app.routes.entregas import router as entregas_router
from app.routes.notificacoes import router as notificacoes_router
from app.routes.relatorios import router as relatorios_router
from app.routes.arquivos import DIRETORIO_ANEXOS, router as arquivos_router
from app.routes.auditoria import router as auditoria_router
from app.routes.dashboard import router as dashboard_router
from app.routes.busca import router as busca_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.config import AMBIENTE, CORS_ORIGINS
from app.inicializacao import inicializar_banco


@asynccontextmanager
async def lifespan(_app: FastAPI):
    inicializar_banco()
    try:
        with SessionLocal() as db:
            removidos = limpar_arquivos_orfaos(
                db=db,
                diretorio=DIRETORIO_ANEXOS,
                retencao_horas=ARQUIVO_ORFAO_RETENCAO_HORAS,
            )
        if removidos:
            logging.getLogger(__name__).info(
                "%s arquivo(s) órfão(s) expirado(s) removido(s).",
                len(removidos),
            )
    except Exception:
        logging.getLogger(__name__).exception(
            "Não foi possível limpar arquivos órfãos expirados."
        )
    yield

app = FastAPI(
    title="Sistema FCL",
    description="API do Sistema Interno de Gestão de Compras e Entregas da FCL",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if AMBIENTE == "production" else "/docs",
    redoc_url=None if AMBIENTE == "production" else "/redoc",
    openapi_url=None if AMBIENTE == "production" else "/openapi.json",
)


@app.middleware("http")
async def adicionar_cabecalhos_seguranca(request, call_next):
    resposta = await call_next(request)
    resposta.headers.setdefault("Cache-Control", "no-store")
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resposta.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    return resposta

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(produtos_router)
app.include_router(fornecedores_router)
app.include_router(clientes_router)
app.include_router(usuarios_router)
app.include_router(auth_router)
app.include_router(solicitacoes_router)
app.include_router(pedidos_router)
app.include_router(recebimentos_router)
app.include_router(entregas_router)
app.include_router(notificacoes_router)
app.include_router(relatorios_router)
app.include_router(arquivos_router)
app.include_router(auditoria_router)
app.include_router(dashboard_router)
app.include_router(busca_router)

@app.get("/")
def inicio():
    return {
        "mensagem": "API da FCL funcionando!"
    }


if AMBIENTE != "production":
    @app.get("/teste-banco")
    def teste_banco():
        with engine.connect() as conexao:
            resultado = conexao.execute(
                text("SELECT current_database();")
            )

            banco = resultado.scalar()

        return {
            "status": "Conexão realizada com sucesso",
            "banco": banco
        }


@app.get("/health", tags=["Infraestrutura"])
def healthcheck():
    with engine.connect() as conexao:
        conexao.execute(text("SELECT 1"))

    return {"status": "ok"}
