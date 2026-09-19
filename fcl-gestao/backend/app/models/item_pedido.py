from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ItemPedido(Base):
    __tablename__ = "item_pedido"

    id_item_pedido: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_pedido_compra: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pedido_compra.id_pedido_compra"),
        nullable=False
    )

    id_item_solicitacao: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("item_solicitacao.id_item_solicitacao"),
        nullable=False
    )

    quantidade: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False
    )