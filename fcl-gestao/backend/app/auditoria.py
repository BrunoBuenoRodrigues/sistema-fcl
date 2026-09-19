from datetime import datetime

from sqlalchemy.orm import Session

from app.models.historico import Historico
from app.models.usuario import Usuario


def registrar_evento_auditoria(
    db: Session,
    usuario: Usuario,
    tipo_registro: str,
    id_registro: int,
    acao: str,
    descricao: str,
) -> None:
    db.add(
        Historico(
            id_usuario=usuario.id_usuario,
            tipo_registro=tipo_registro,
            id_registro=id_registro,
            acao=acao,
            descricao=descricao,
            data_hora=datetime.now(),
        )
    )


def listar_campos_alterados(campos: set[str]) -> str:
    nomes = {
        "ativo": "status",
        "cpf_cnpj": "CPF/CNPJ",
        "cnpj": "CNPJ",
        "nome_fantasia": "nome fantasia",
        "razao_social": "razão social",
    }
    campos_seguros = [
        "senha" if campo == "senha" else nomes.get(campo, campo.replace("_", " "))
        for campo in sorted(campos)
    ]
    return ", ".join(campos_seguros)
