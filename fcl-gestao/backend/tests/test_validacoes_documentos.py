import unittest

from pydantic import ValidationError

from app.schemas.cliente import ClienteCriar
from app.schemas.fornecedor import FornecedorCriar
from app.schemas.recebimento import RecebimentoCriar


class TestValidacoesDocumentos(unittest.TestCase):
    def dados_cliente(self, cpf_cnpj: str):
        return {
            "nome": "Cliente Teste",
            "cpf_cnpj": cpf_cnpj,
            "telefone": "11999999999",
            "endereco": "Rua Teste",
            "numero": "10",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "uf": "SP",
        }

    def test_aceita_cpf_e_cnpj_validos(self):
        cliente_cpf = ClienteCriar(**self.dados_cliente("52998224725"))
        cliente_cnpj = ClienteCriar(**self.dados_cliente("11222333000181"))

        self.assertEqual(cliente_cpf.cpf_cnpj, "52998224725")
        self.assertEqual(cliente_cnpj.cpf_cnpj, "11222333000181")

    def test_rejeita_cpf_e_cnpj_com_digitos_invalidos(self):
        with self.assertRaises(ValidationError):
            ClienteCriar(**self.dados_cliente("12345678901"))

        with self.assertRaises(ValidationError):
            FornecedorCriar(
                razao_social="Fornecedor Teste",
                cnpj="12345678000199",
            )

    def test_normaliza_numero_da_nota_fiscal(self):
        recebimento = RecebimentoCriar(
            id_pedido_compra=1,
            numero_nota_fiscal="  NF-123  ",
            itens=[],
        )

        self.assertEqual(recebimento.numero_nota_fiscal, "NF-123")


if __name__ == "__main__":
    unittest.main()
