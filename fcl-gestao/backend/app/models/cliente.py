from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    cpf_cnpj: Mapped[str | None] = mapped_column(String(20))
    telefone: Mapped[str | None] = mapped_column(String(20))
    endereco: Mapped[str] = mapped_column(String(120), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    bairro: Mapped[str] = mapped_column(String(60), nullable=False)
    cidade: Mapped[str] = mapped_column(String(60), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)