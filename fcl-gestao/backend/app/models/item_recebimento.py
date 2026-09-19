from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ItemRecebimento(Base):
    __tablename__ = "item_recebimento"

    id_item_recebimento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_recebimento: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recebimento.id_recebimento"),
        nullable=False
    )

    id_item_pedido: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("item_pedido.id_item_pedido"),
        nullable=False
    )

    quantidade_recebida: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False
    )