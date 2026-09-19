from sqlalchemy import select

from app.config import (
    ADMIN_INICIAL_LOGIN,
    ADMIN_INICIAL_NOME,
    ADMIN_INICIAL_SENHA,
)
from app.database import Base, SessionLocal, engine
from app.models.cliente import Cliente  # noqa: F401
from app.models.entrega import Entrega  # noqa: F401
from app.models.fornecedor import Fornecedor  # noqa: F401
from app.models.historico import Historico  # noqa: F401
from app.models.item_pedido import ItemPedido  # noqa: F401
from app.models.item_recebimento import ItemRecebimento  # noqa: F401
from app.models.item_solicitacao import ItemSolicitacao  # noqa: F401
from app.models.notificacao import Notificacao  # noqa: F401
from app.models.pedido_fornecedor import PedidoCompra  # noqa: F401
from app.models.produto import Produto  # noqa: F401
from app.models.recebimento import Recebimento  # noqa: F401
from app.models.solicitacao_compra import SolicitacaoCompra  # noqa: F401
from app.models.usuario import Usuario
from app.security import gerar_hash_senha


def inicializar_banco() -> None:
    Base.metadata.create_all(bind=engine)

    if not ADMIN_INICIAL_LOGIN or not ADMIN_INICIAL_SENHA:
        return

    with SessionLocal() as db:
        usuario_existente = db.scalar(
            select(Usuario).where(Usuario.login == ADMIN_INICIAL_LOGIN)
        )

        if usuario_existente:
            return

        db.add(
            Usuario(
                nome=ADMIN_INICIAL_NOME or "Administrador",
                login=ADMIN_INICIAL_LOGIN,
                senha=gerar_hash_senha(ADMIN_INICIAL_SENHA),
                perfil="ADMINISTRADOR",
                ativo=True,
            )
        )
        db.commit()
