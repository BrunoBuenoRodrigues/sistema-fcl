import unittest
from unittest.mock import Mock

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.integridade import tratar_conflito_unicidade


class OrigemComRestricao(Exception):
    def __init__(self, nome_restricao: str, mensagem: str = ""):
        super().__init__(mensagem)
        self.diag = Mock(constraint_name=nome_restricao)


class TestIntegridade(unittest.TestCase):
    def test_converte_restricao_nomeada_em_erro_funcional(self):
        db = Mock()
        erro = IntegrityError(
            "insert",
            {},
            OrigemComRestricao("produto_codigo_key"),
        )

        with self.assertRaises(HTTPException) as contexto:
            tratar_conflito_unicidade(
                db,
                erro,
                restricoes={"produto_codigo_key"},
                colunas={"produto.codigo"},
                detalhe="Código já cadastrado.",
            )

        db.rollback.assert_called_once_with()
        self.assertEqual(contexto.exception.status_code, 400)
        self.assertEqual(contexto.exception.detail, "Código já cadastrado.")

    def test_reconhece_mensagem_de_unicidade_do_sqlite(self):
        db = Mock()
        erro = IntegrityError(
            "insert",
            {},
            Exception("UNIQUE constraint failed: usuario.login"),
        )

        with self.assertRaises(HTTPException):
            tratar_conflito_unicidade(
                db,
                erro,
                restricoes={"usuario_login_key"},
                colunas={"usuario.login"},
                detalhe="Login já cadastrado.",
            )

        db.rollback.assert_called_once_with()

    def test_repassa_erro_de_integridade_desconhecido(self):
        db = Mock()
        erro = IntegrityError(
            "insert",
            {},
            OrigemComRestricao("outra_restricao"),
        )

        with self.assertRaises(IntegrityError) as contexto:
            tratar_conflito_unicidade(
                db,
                erro,
                restricoes={"produto_codigo_key"},
                colunas={"produto.codigo"},
                detalhe="Código já cadastrado.",
            )

        db.rollback.assert_called_once_with()
        self.assertIs(contexto.exception, erro)


if __name__ == "__main__":
    unittest.main()
