from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notificacao(Base):
    __tablename__ = "notificacao"

    id_notificacao: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_usuario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id_usuario"),
        nullable=False
    )

    titulo: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    mensagem: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    lida: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    data_hora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )