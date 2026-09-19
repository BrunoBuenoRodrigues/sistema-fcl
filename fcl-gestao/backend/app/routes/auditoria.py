from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.historico import Historico
from app.models.usuario import Usuario
from app.schemas.auditoria import EventoAuditoriaResposta


router = APIRouter(
    prefix="/auditoria",
    tags=["Auditoria"],
)


@router.get("/", response_model=list[EventoAuditoriaResposta])
def listar_eventos_auditoria(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfis("ADMINISTRADOR")),
):
    registros = (
        db.query(Historico, Usuario.nome, Usuario.login)
        .join(Usuario, Usuario.id_usuario == Historico.id_usuario)
        .order_by(Historico.data_hora.desc(), Historico.id_historico.desc())
        .all()
    )

    return [
        {
            "id_historico": historico.id_historico,
            "id_usuario": historico.id_usuario,
            "usuario_nome": nome_usuario,
            "usuario_login": login_usuario,
            "tipo_registro": historico.tipo_registro,
            "id_registro": historico.id_registro,
            "acao": historico.acao,
            "descricao": historico.descricao,
            "data_hora": historico.data_hora,
        }
        for historico, nome_usuario, login_usuario in registros
    ]
