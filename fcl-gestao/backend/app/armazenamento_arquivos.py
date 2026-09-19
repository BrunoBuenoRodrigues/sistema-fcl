import re
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.entrega import Entrega


PADRAO_ARQUIVO_GERADO = re.compile(
    r"^[0-9a-f]{32}-[a-zA-Z0-9_-]+\.(pdf|png|jpg|webp)$"
)


def obter_urls_vinculadas(db: Session) -> set[str]:
    urls: set[str] = set()

    for anexo_pedido, comprovante_entrega in db.query(
        Entrega.anexo_pedido,
        Entrega.comprovante_entrega,
    ).all():
        if anexo_pedido:
            urls.add(anexo_pedido)
        if comprovante_entrega:
            urls.add(comprovante_entrega)

    return urls


def remover_arquivos_orfaos_expirados(
    diretorio: Path,
    urls_vinculadas: set[str],
    retencao_horas: int,
    agora: float | None = None,
) -> list[str]:
    if not diretorio.is_dir():
        return []

    limite = (agora if agora is not None else time.time()) - (
        retencao_horas * 60 * 60
    )
    removidos: list[str] = []

    for arquivo in diretorio.iterdir():
        if not arquivo.is_file():
            continue
        if not PADRAO_ARQUIVO_GERADO.fullmatch(arquivo.name):
            continue

        url_arquivo = f"/arquivos/entregas/{arquivo.name}"
        if url_arquivo in urls_vinculadas:
            continue
        if arquivo.stat().st_mtime > limite:
            continue

        arquivo.unlink()
        removidos.append(arquivo.name)

    return removidos


def limpar_arquivos_orfaos(
    db: Session,
    diretorio: Path,
    retencao_horas: int,
) -> list[str]:
    return remover_arquivos_orfaos_expirados(
        diretorio=diretorio,
        urls_vinculadas=obter_urls_vinculadas(db),
        retencao_horas=retencao_horas,
    )
