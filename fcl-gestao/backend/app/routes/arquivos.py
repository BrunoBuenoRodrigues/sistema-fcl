import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.armazenamento_arquivos import limpar_arquivos_orfaos
from app.config import ARQUIVO_ORFAO_RETENCAO_HORAS
from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.entrega import Entrega
from app.models.usuario import Usuario
from app.schemas.arquivo import ArquivoResposta


router = APIRouter(
    prefix="/arquivos",
    tags=["Arquivos"],
)

DIRETORIO_ANEXOS = Path(__file__).resolve().parents[2] / "uploads" / "entregas"
TAMANHO_MAXIMO = 5 * 1024 * 1024
PREFIXO_URL_ENTREGAS = "/arquivos/entregas/"


def detectar_tipo_arquivo(conteudo: bytes):
    if conteudo.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"

    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"

    if conteudo.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"

    if (
        len(conteudo) >= 12
        and conteudo.startswith(b"RIFF")
        and conteudo[8:12] == b"WEBP"
    ):
        return ".webp", "image/webp"

    return None


def normalizar_nome(nome: str):
    nome_decodificado = unquote(nome or "arquivo")
    base = Path(nome_decodificado).stem
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-_").lower()
    return (base or "arquivo")[:60]


def resolver_arquivo_entrega(url_arquivo: str) -> Path | None:
    if not url_arquivo.startswith(PREFIXO_URL_ENTREGAS):
        return None

    nome_arquivo = url_arquivo.removeprefix(PREFIXO_URL_ENTREGAS)
    if not nome_arquivo or Path(nome_arquivo).name != nome_arquivo:
        return None

    arquivo = (DIRETORIO_ANEXOS / nome_arquivo).resolve()
    diretorio = DIRETORIO_ANEXOS.resolve()
    if arquivo.parent != diretorio or not arquivo.is_file():
        return None

    return arquivo


@router.post("/entregas", response_model=ArquivoResposta)
async def enviar_arquivo_entrega(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR",
        )
    ),
):
    limpar_arquivos_orfaos(
        db=db,
        diretorio=DIRETORIO_ANEXOS,
        retencao_horas=ARQUIVO_ORFAO_RETENCAO_HORAS,
    )

    tamanho_declarado = request.headers.get("content-length")
    if tamanho_declarado:
        try:
            tamanho_informado = int(tamanho_declarado)
        except ValueError as erro:
            raise HTTPException(
                status_code=400,
                detail="O tamanho informado para o arquivo é inválido.",
            ) from erro

        if tamanho_informado < 0:
            raise HTTPException(
                status_code=400,
                detail="O tamanho informado para o arquivo é inválido.",
            )
        if tamanho_informado > TAMANHO_MAXIMO:
            raise HTTPException(
                status_code=413,
                detail="O arquivo deve possuir no máximo 5 MB.",
            )

    conteudo = await request.body()

    if not conteudo:
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")

    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(
            status_code=413,
            detail="O arquivo deve possuir no máximo 5 MB.",
        )

    tipo_detectado = detectar_tipo_arquivo(conteudo)
    if tipo_detectado is None:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Envie PDF, PNG, JPG ou WEBP.",
        )

    extensao, tipo_mime = tipo_detectado
    nome_original = request.headers.get("x-nome-arquivo", "arquivo")
    nome_seguro = normalizar_nome(nome_original)
    nome_armazenado = f"{uuid4().hex}-{nome_seguro}{extensao}"

    DIRETORIO_ANEXOS.mkdir(parents=True, exist_ok=True)
    destino = DIRETORIO_ANEXOS / nome_armazenado
    destino.write_bytes(conteudo)

    return {
        "nome": nome_armazenado,
        "url": f"{PREFIXO_URL_ENTREGAS}{nome_armazenado}",
        "tipo": tipo_mime,
        "tamanho": len(conteudo),
    }


@router.get("/entregas/{nome_arquivo}")
def baixar_arquivo_entrega(
    nome_arquivo: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR",
        )
    ),
):
    arquivo = resolver_arquivo_entrega(f"{PREFIXO_URL_ENTREGAS}{nome_arquivo}")
    if arquivo is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    if usuario_atual.perfil == "ENTREGADOR":
        url_arquivo = f"{PREFIXO_URL_ENTREGAS}{nome_arquivo}"
        entrega_permitida = db.query(Entrega.id_entrega).filter(
            Entrega.id_entregador == usuario_atual.id_usuario,
            or_(
                Entrega.anexo_pedido == url_arquivo,
                Entrega.comprovante_entrega == url_arquivo,
            ),
        ).first()

        if entrega_permitida is None:
            raise HTTPException(
                status_code=403,
                detail="Você não possui acesso a este arquivo de entrega.",
            )

    return FileResponse(
        path=arquivo,
        filename=nome_arquivo,
        media_type="application/octet-stream",
    )
