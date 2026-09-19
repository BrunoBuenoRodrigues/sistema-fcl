from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    senha: Mapped[str] = mapped_column(String(255), nullable=False)
    versao_sessao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_cadastro: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
