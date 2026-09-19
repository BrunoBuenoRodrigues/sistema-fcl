from pydantic import BaseModel


class ArquivoResposta(BaseModel):
    nome: str
    url: str
    tipo: str
    tamanho: int
