from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Historico(Base):
    __tablename__ = "historico"

    id_historico: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_usuario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=False
    )

    tipo_registro: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    id_registro: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    acao: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    descricao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    data_hora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )