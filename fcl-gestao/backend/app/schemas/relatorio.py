from datetime import date, datetime

from pydantic import BaseModel


class PeriodoRelatorio(BaseModel):
    data_inicio: date | None = None
    data_fim: date | None = None


class ContagemPorStatus(BaseModel):
    total: int
    por_status: dict[str, int]


class ResumoRecebimentos(BaseModel):
    total: int
    quantidade_recebida: float


class ResumoEntregas(ContagemPorStatus):
    atrasadas: int
    agendadas_hoje: int


class ResumoCadastros(BaseModel):
    produtos_ativos: int
    fornecedores_ativos: int
    clientes_ativos: int


class ProdutoMaisSolicitado(BaseModel):
    id_produto: int
    nome: str
    quantidade_solicitada: float


class FornecedorMaisUtilizado(BaseModel):
    id_fornecedor: int
    nome: str
    total_pedidos: int


class ResumoGerencialResposta(BaseModel):
    gerado_em: datetime
    periodo: PeriodoRelatorio
    solicitacoes: ContagemPorStatus
    pedidos: ContagemPorStatus
    recebimentos: ResumoRecebimentos
    entregas: ResumoEntregas
    cadastros: ResumoCadastros
    produtos_mais_solicitados: list[ProdutoMaisSolicitado]
    fornecedores_mais_utilizados: list[FornecedorMaisUtilizado]
