from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PedidoCompra(Base):
    __tablename__ = "pedido_compra"
    __table_args__ = (
        UniqueConstraint(
            "numero_pedido",
            name="uq_pedido_compra_numero_pedido",
        ),
    )

    id_pedido_compra: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_solicitacao: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitacao_compra.id_solicitacao"),
        nullable=False
    )

    id_fornecedor: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fornecedor.id_fornecedor"),
        nullable=False
    )

    numero_pedido: Mapped[str | None] = mapped_column(
        String(30)
    )

    data_pedido: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    observacao: Mapped[str | None] = mapped_column(
        Text
    )

    motivo_cancelamento: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    data_cancelamento: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    id_usuario_cancelamento: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=True,
    )
