from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Produto(Base):
    __tablename__ = "produto"

    id_produto: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100))
    marca: Mapped[str | None] = mapped_column(String(100))
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)