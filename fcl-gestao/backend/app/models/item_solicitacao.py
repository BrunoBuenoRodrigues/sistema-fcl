from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ItemSolicitacao(Base):
    __tablename__ = "item_solicitacao"

    id_item_solicitacao: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    id_solicitacao: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitacao_compra.id_solicitacao"),
        nullable=False
    )

    solicitacao: Mapped["SolicitacaoCompra"] = relationship(
        "SolicitacaoCompra",
        back_populates="itens"
    )

    id_produto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("produto.id_produto"),
        nullable=False
    )

    quantidade: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False
    )