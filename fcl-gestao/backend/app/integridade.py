from collections.abc import Collection

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def tratar_conflito_unicidade(
    db: Session,
    erro: IntegrityError,
    *,
    restricoes: Collection[str],
    colunas: Collection[str],
    detalhe: str,
) -> None:
    origem = erro.orig
    diagnostico = getattr(origem, "diag", None)
    nome_restricao = getattr(diagnostico, "constraint_name", None)
    mensagem = str(origem).lower()

    db.rollback()

    if nome_restricao in restricoes or any(
        coluna.lower() in mensagem for coluna in colunas
    ):
        raise HTTPException(status_code=400, detail=detalhe) from erro

    raise erro
