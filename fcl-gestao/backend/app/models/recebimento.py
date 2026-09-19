from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Recebimento(Base):
    __tablename__ = "recebimento"

    id_recebimento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_pedido_compra: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pedido_compra.id_pedido_compra"),
        nullable=False
    )

    id_usuario_recebimento: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=False
    )

    data_recebimento: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    numero_nota_fiscal: Mapped[str | None] = mapped_column(
        String(30)
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="REGISTRADO",
        server_default="REGISTRADO",
    )

    motivo_estorno: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_estorno: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    id_usuario_estorno: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=True,
    )

    observacao: Mapped[str | None] = mapped_column(
        Text
    )
