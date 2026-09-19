from pydantic import BaseModel, Field


class ProdutoCriar(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    nome: str = Field(min_length=1, max_length=100)
    categoria: str = Field(min_length=1, max_length=100)
    marca: str = Field(min_length=1, max_length=100)
    unidade: str = Field(min_length=1, max_length=20)
    descricao: str | None = None


class ProdutoResposta(BaseModel):
    id_produto: int
    codigo: str
    nome: str
    categoria: str | None = None
    marca: str | None = None
    unidade: str
    descricao: str | None = None
    ativo: bool

    model_config = {
        "from_attributes": True
    }

class ProdutoAtualizar(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    categoria: str | None = Field(default=None, min_length=1, max_length=100)
    marca: str | None = Field(default=None, min_length=1, max_length=100)
    unidade: str | None = Field(default=None, min_length=1, max_length=20)
    descricao: str | None = None
    ativo: bool | None = None
