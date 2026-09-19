from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SolicitacaoCompra(Base):
    __tablename__ = "solicitacao_compra"

    id_solicitacao: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_usuario_solicitante: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=False
    )

    data_solicitacao: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    prioridade: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    motivo: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    observacao: Mapped[str | None] = mapped_column(
        Text
    )

    motivo_rejeicao: Mapped[str | None] = mapped_column(
        Text
    )

    motivo_cancelamento: Mapped[str | None] = mapped_column(
        Text
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

    itens: Mapped[list["ItemSolicitacao"]] = relationship(
        "ItemSolicitacao",
        back_populates="solicitacao"
    )
