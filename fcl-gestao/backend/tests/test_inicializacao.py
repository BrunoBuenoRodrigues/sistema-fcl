import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.usuario import Usuario
from app.security import verificar_senha
from app import inicializacao


class TestInicializacao(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(bind=self.engine)
        self.valores_originais = {
            "engine": inicializacao.engine,
            "SessionLocal": inicializacao.SessionLocal,
            "ADMIN_INICIAL_NOME": inicializacao.ADMIN_INICIAL_NOME,
            "ADMIN_INICIAL_LOGIN": inicializacao.ADMIN_INICIAL_LOGIN,
            "ADMIN_INICIAL_SENHA": inicializacao.ADMIN_INICIAL_SENHA,
        }
        inicializacao.engine = self.engine
        inicializacao.SessionLocal = self.session_factory
        inicializacao.ADMIN_INICIAL_NOME = "Administrador Inicial"
        inicializacao.ADMIN_INICIAL_LOGIN = "admin_inicial"
        inicializacao.ADMIN_INICIAL_SENHA = "senha-segura"

    def tearDown(self):
        for nome, valor in self.valores_originais.items():
            setattr(inicializacao, nome, valor)
        self.engine.dispose()

    def test_cria_estrutura_e_administrador_apenas_uma_vez(self):
        inicializacao.inicializar_banco()
        inicializacao.inicializar_banco()

        with self.session_factory() as db:
            quantidade = db.scalar(select(func.count(Usuario.id_usuario)))
            usuario = db.scalar(
                select(Usuario).where(Usuario.login == "admin_inicial")
            )

        self.assertEqual(quantidade, 1)
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.perfil, "ADMINISTRADOR")
        self.assertTrue(verificar_senha("senha-segura", usuario.senha))


if __name__ == "__main__":
    unittest.main()
