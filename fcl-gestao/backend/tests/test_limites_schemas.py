import unittest

from pydantic import ValidationError

from app.schemas.cliente import ClienteCriar
from app.schemas.entrega import EntregaCriar
from app.schemas.fornecedor import FornecedorCriar
from app.schemas.produto import ProdutoCriar
from app.schemas.usuario import UsuarioCriar


class TestLimitesSchemas(unittest.TestCase):
    def test_rejeita_produto_maior_que_as_colunas_do_banco(self):
        with self.assertRaises(ValidationError):
            ProdutoCriar(
                codigo="C" * 31,
                nome="Produto",
                categoria="Categoria",
                marca="Marca",
                unidade="UN",
            )

    def test_rejeita_cliente_maior_que_as_colunas_do_banco(self):
        with self.assertRaises(ValidationError):
            ClienteCriar(
                nome="Cliente",
                endereco="Rua",
                numero="1",
                bairro="B" * 61,
                cidade="Cidade",
                uf="SP",
            )

    def test_rejeita_fornecedor_maior_que_as_colunas_do_banco(self):
        with self.assertRaises(ValidationError):
            FornecedorCriar(
                razao_social="F" * 121,
                cnpj="11222333000181",
            )

    def test_rejeita_usuario_maior_que_as_colunas_do_banco(self):
        with self.assertRaises(ValidationError):
            UsuarioCriar(
                nome="Usuário",
                login="u" * 51,
                senha="senha123",
                perfil="FUNCIONARIO",
            )

    def test_rejeita_anexo_maior_que_a_coluna_do_banco(self):
        with self.assertRaises(ValidationError):
            EntregaCriar(
                id_cliente=1,
                anexo_pedido="a" * 256,
            )


if __name__ == "__main__":
    unittest.main()
