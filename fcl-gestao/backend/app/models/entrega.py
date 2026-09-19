from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Entrega(Base):
    __tablename__ = "entrega"

    id_entrega: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_cliente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.id_cliente"),
        nullable=False
    )

    id_usuario_cadastro: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=False
    )

    id_entregador: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    data_agendada: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    anexo_pedido: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    comprovante_entrega: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    observacao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    motivo_cancelamento: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    data_cancelamento: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    id_usuario_cancelamento: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    motivo_nao_entrega: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    data_ultima_tentativa: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    id_usuario_ultima_tentativa: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )
