from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Fornecedor(Base):
    __tablename__ = "fornecedor"

    id_fornecedor: Mapped[int] = mapped_column(Integer, primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(120))
    cnpj: Mapped[str | None] = mapped_column(String(20), unique=True)
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)