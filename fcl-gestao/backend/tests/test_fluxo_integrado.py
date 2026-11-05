import os
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ["JWT_SECRET_KEY"] = "segredo-exclusivo-para-testes-integrados-fcl"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.limitador_login import LimitadorLogin
from app.routes import arquivos as arquivos_route
from app.routes import auth as auth_route
from app.models.historico import Historico
from app.models.cliente import Cliente
from app.models.entrega import Entrega
from app.models.notificacao import Notificacao
from app.models.fornecedor import Fornecedor
from app.models.pedido_fornecedor import PedidoCompra
from app.models.usuario import Usuario
from app.security import gerar_hash_senha


class TestFluxoIntegrado(unittest.TestCase):
    def test_numero_pedido_possui_restricao_unica_nomeada(self):
        restricoes = {
            restricao.name
            for restricao in PedidoCompra.__table__.constraints
            if isinstance(restricao, UniqueConstraint)
        }

        self.assertIn("uq_pedido_compra_numero_pedido", restricoes)

    @classmethod
    def setUpClass(cls):
        cls.diretorio_upload_original = arquivos_route.DIRETORIO_ANEXOS
        cls.diretorio_upload_teste = Path(__file__).parent / "arquivos_teste"
        cls.arquivos_upload_anteriores = set(
            cls.diretorio_upload_teste.iterdir()
        )
        arquivos_route.DIRETORIO_ANEXOS = cls.diretorio_upload_teste
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)

        def substituir_banco():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = substituir_banco
        cls.client = TestClient(app)

        db = cls.session_factory()
        try:
            senha = gerar_hash_senha("senha123")
            db.add_all(
                [
                    Usuario(
                        nome="Administrador Teste",
                        login="admin_teste",
                        senha=senha,
                        perfil="ADMINISTRADOR",
                        ativo=True,
                    ),
                    Usuario(
                        nome="Funcionário Teste",
                        login="funcionario_teste",
                        senha=senha,
                        perfil="FUNCIONARIO",
                        ativo=True,
                    ),
                    Usuario(
                        nome="Estoque Teste",
                        login="estoque_teste",
                        senha=senha,
                        perfil="ESTOQUE",
                        ativo=True,
                    ),
                    Usuario(
                        nome="Entregador Teste",
                        login="entregador_teste",
                        senha=senha,
                        perfil="ENTREGADOR",
                        ativo=True,
                    ),
                    Usuario(
                        nome="ZZ Entregador Dois",
                        login="entregador_dois_teste",
                        senha=senha,
                        perfil="ENTREGADOR",
                        ativo=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        arquivos_route.DIRETORIO_ANEXOS = cls.diretorio_upload_original

        for arquivo in cls.diretorio_upload_teste.iterdir():
            if arquivo not in cls.arquivos_upload_anteriores and arquivo.is_file():
                arquivo.unlink()

    def autenticar(self, login):
        resposta = self.client.post(
            "/login",
            json={"login": login, "senha": "senha123"},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return {"Authorization": f"Bearer {resposta.json()['access_token']}"}

    def validar_status(self, resposta, status_esperado):
        self.assertEqual(resposta.status_code, status_esperado, resposta.text)
        return resposta.json()

    def test_bloqueio_temporario_apos_falhas_de_login(self):
        limitador_original = auth_route.limitador_login
        auth_route.limitador_login = LimitadorLogin(
            max_tentativas=3,
            bloqueio_segundos=60,
        )

        try:
            for _ in range(3):
                resposta = self.client.post(
                    "/login",
                    json={"login": "admin_teste", "senha": "incorreta"},
                )
                self.assertEqual(resposta.status_code, 401)

            bloqueado = self.client.post(
                "/login",
                json={"login": "admin_teste", "senha": "senha123"},
            )
            self.assertEqual(bloqueado.status_code, 429)
            self.assertIn("Retry-After", bloqueado.headers)

            auth_route.limitador_login.limpar()
            liberado = self.client.post(
                "/login",
                json={"login": "admin_teste", "senha": "senha123"},
            )
            self.assertEqual(liberado.status_code, 200)
        finally:
            auth_route.limitador_login = limitador_original

    def test_api_envia_cabecalhos_de_seguranca(self):
        resposta = self.client.get("/")

        self.assertEqual(resposta.headers["cache-control"], "no-store")
        self.assertEqual(resposta.headers["x-content-type-options"], "nosniff")
        self.assertEqual(resposta.headers["x-frame-options"], "SAMEORIGIN")

    def test_login_com_hash_corrompido_falha_sem_expor_erro_interno(self):
        db = self.session_factory()
        try:
            db.add(
                Usuario(
                    nome="Usuário com hash inválido",
                    login="hash_invalido_teste",
                    senha="hash-corrompido",
                    perfil="FUNCIONARIO",
                    ativo=True,
                )
            )
            db.commit()
        finally:
            db.close()

        resposta = self.client.post(
            "/login",
            json={"login": "hash_invalido_teste", "senha": "senha123"},
        )

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["detail"], "Login ou senha inválidos.")

    def test_auditoria_geral_exige_administrador_e_identifica_usuario(self):
        db = self.session_factory()
        try:
            administrador = db.query(Usuario).filter(
                Usuario.login == "admin_teste"
            ).first()
            db.add(
                Historico(
                    id_usuario=administrador.id_usuario,
                    tipo_registro="SISTEMA",
                    id_registro=1,
                    acao="HOMOLOGACAO",
                    descricao="Evento criado pelo teste de auditoria.",
                    data_hora=datetime.now(),
                )
            )
            db.commit()
        finally:
            db.close()

        admin = self.autenticar("admin_teste")
        resposta = self.client.get("/auditoria/", headers=admin)
        eventos = self.validar_status(resposta, 200)

        self.assertEqual(eventos[0]["acao"], "HOMOLOGACAO")
        self.assertEqual(eventos[0]["usuario_login"], "admin_teste")

        funcionario = self.autenticar("funcionario_teste")
        sem_permissao = self.client.get("/auditoria/", headers=funcionario)
        self.assertEqual(sem_permissao.status_code, 403)

    def test_auditoria_registra_ciclo_dos_cadastros_administrativos(self):
        admin = self.autenticar("admin_teste")

        produto = self.criar_produto(admin, "PROD-AUD-001")
        fornecedor = self.validar_status(
            self.client.post(
                "/fornecedores/",
                headers=admin,
                json={
                    "razao_social": "Fornecedor Auditoria Ltda",
                    "nome_fantasia": "Fornecedor Auditoria",
                    "cnpj": "04252011000110",
                    "telefone": "11977777777",
                    "email": "auditoria@example.test",
                },
            ),
            201,
        )
        cliente = self.validar_status(
            self.client.post(
                "/clientes/",
                headers=admin,
                json={
                    "nome": "Cliente Auditoria",
                    "cpf_cnpj": "11144477735",
                    "telefone": "11966666666",
                    "endereco": "Rua da Auditoria",
                    "numero": "10",
                    "bairro": "Centro",
                    "cidade": "Sao Paulo",
                    "uf": "SP",
                    "observacao": "Registro temporario de teste.",
                },
            ),
            201,
        )

        recursos = [
            ("PRODUTO", "produtos", produto["id_produto"], {"nome": "Produto auditado"}),
            (
                "FORNECEDOR",
                "fornecedores",
                fornecedor["id_fornecedor"],
                {"nome_fantasia": "Fornecedor auditado"},
            ),
            ("CLIENTE", "clientes", cliente["id_cliente"], {"telefone": "11955555555"}),
        ]

        for _, rota, id_registro, alteracao in recursos:
            self.validar_status(
                self.client.put(
                    f"/{rota}/{id_registro}",
                    headers=admin,
                    json=alteracao,
                ),
                200,
            )
            self.validar_status(
                self.client.patch(
                    f"/{rota}/{id_registro}/desativar",
                    headers=admin,
                ),
                200,
            )
            self.validar_status(
                self.client.patch(
                    f"/{rota}/{id_registro}/ativar",
                    headers=admin,
                ),
                200,
            )

        db = self.session_factory()
        try:
            for tipo, _, id_registro, _ in recursos:
                acoes = {
                    evento.acao
                    for evento in db.query(Historico).filter(
                        Historico.tipo_registro == tipo,
                        Historico.id_registro == id_registro,
                    )
                }
                self.assertTrue(
                    {"CADASTRO", "EDICAO", "DESATIVACAO", "ATIVACAO"}
                    .issubset(acoes)
                )
        finally:
            db.close()

    def criar_produto(self, headers, codigo):
        return self.validar_status(
            self.client.post(
                "/produtos/",
                headers=headers,
                json={
                    "codigo": codigo,
                    "nome": "Produto de teste integrado",
                    "categoria": "Testes",
                    "marca": "FCL",
                    "unidade": "UN",
                    "descricao": "Criado somente no SQLite em memória.",
                },
            ),
            201,
        )

    def test_criacao_entrega_define_status_inicial_e_valida_data(self):
        funcionario = self.autenticar("funcionario_teste")
        cliente = self.validar_status(
            self.client.post(
                "/clientes/",
                headers=funcionario,
                json={
                    "nome": "Cliente Fluxo Inicial Entrega",
                    "endereco": "Rua do Agendamento",
                    "numero": "10",
                    "bairro": "Centro",
                    "cidade": "São Paulo",
                    "uf": "SP",
                },
            ),
            201,
        )
        id_cliente = cliente["id_cliente"]
        ids_entregas = []

        def limpar_dados_temporarios():
            db = self.session_factory()
            try:
                if ids_entregas:
                    db.query(Historico).filter(
                        Historico.tipo_registro == "ENTREGA",
                        Historico.id_registro.in_(ids_entregas),
                    ).delete(synchronize_session=False)
                    db.query(Entrega).filter(
                        Entrega.id_entrega.in_(ids_entregas),
                    ).delete(synchronize_session=False)
                db.query(Historico).filter(
                    Historico.tipo_registro == "CLIENTE",
                    Historico.id_registro == id_cliente,
                ).delete(synchronize_session=False)
                db.query(Cliente).filter(
                    Cliente.id_cliente == id_cliente,
                ).delete(synchronize_session=False)
                db.commit()
            finally:
                db.close()

        self.addCleanup(limpar_dados_temporarios)
        data_futura = date.today() + timedelta(days=1)

        sem_data = self.validar_status(
            self.client.post(
                "/entregas/",
                headers=funcionario,
                json={"id_cliente": id_cliente},
            ),
            201,
        )
        ids_entregas.append(sem_data["id_entrega"])
        self.assertEqual(sem_data["status"], "CADASTRADA")
        self.assertIsNone(sem_data["data_agendada"])

        com_data = self.validar_status(
            self.client.post(
                "/entregas/",
                headers=funcionario,
                json={
                    "id_cliente": id_cliente,
                    "data_agendada": data_futura.isoformat(),
                },
            ),
            201,
        )
        ids_entregas.append(com_data["id_entrega"])
        self.assertEqual(com_data["status"], "AGENDADA")
        self.assertEqual(com_data["data_agendada"], data_futura.isoformat())

        data_inexistente = self.client.post(
            "/entregas/",
            headers=funcionario,
            json={
                "id_cliente": id_cliente,
                "data_agendada": "2099-02-30",
            },
        )
        self.assertEqual(data_inexistente.status_code, 422)

        data_passada = self.client.post(
            "/entregas/",
            headers=funcionario,
            json={
                "id_cliente": id_cliente,
                "data_agendada": (date.today() - timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(data_passada.status_code, 400)

        agendada_posteriormente = self.validar_status(
            self.client.patch(
                f"/entregas/{sem_data['id_entrega']}/agendamento",
                headers=funcionario,
                json={"data_agendada": data_futura.isoformat()},
            ),
            200,
        )
        self.assertEqual(agendada_posteriormente["status"], "AGENDADA")

        historico_com_data = self.validar_status(
            self.client.get(
                f"/entregas/{com_data['id_entrega']}/historico",
                headers=funcionario,
            ),
            200,
        )
        historico_sem_data = self.validar_status(
            self.client.get(
                f"/entregas/{sem_data['id_entrega']}/historico",
                headers=funcionario,
            ),
            200,
        )
        self.assertEqual(
            [evento["acao"] for evento in historico_com_data],
            ["CADASTRO", "AGENDAMENTO"],
        )
        self.assertEqual(
            [evento["acao"] for evento in historico_sem_data],
            ["CADASTRO", "AGENDAMENTO"],
        )

    def test_fluxo_completo_de_compras_recebimento_e_entrega(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        estoque = self.autenticar("estoque_teste")
        entregador = self.autenticar("entregador_teste")

        produto = self.criar_produto(admin, "PROD-E2E-001")

        fornecedor = self.validar_status(
            self.client.post(
                "/fornecedores/",
                headers=admin,
                json={
                    "razao_social": "Fornecedor Teste Integrado Ltda",
                    "nome_fantasia": "Fornecedor E2E",
                    "cnpj": "11222333000181",
                    "telefone": "11999999999",
                    "email": "fornecedor@example.test",
                },
            ),
            201,
        )

        cliente = self.validar_status(
            self.client.post(
                "/clientes/",
                headers=funcionario,
                json={
                    "nome": "Cliente Teste Integrado",
                    "cpf_cnpj": "52998224725",
                    "telefone": "11988888888",
                    "endereco": "Rua dos Testes",
                    "numero": "100",
                    "bairro": "Centro",
                    "cidade": "São Paulo",
                    "uf": "SP",
                    "observacao": "Registro temporário.",
                },
            ),
            201,
        )

        solicitacao = self.validar_status(
            self.client.post(
                "/solicitacoes/",
                headers=funcionario,
                json={
                    "prioridade": "MEDIA",
                    "motivo": "Validar o fluxo completo",
                    "observacao": "Teste integrado",
                    "itens": [
                        {
                            "id_produto": produto["id_produto"],
                            "quantidade": 2,
                        }
                    ],
                },
            ),
            201,
        )
        id_solicitacao = solicitacao["id_solicitacao"]

        resposta_sem_permissao = self.client.patch(
            f"/solicitacoes/{id_solicitacao}/iniciar-analise",
            headers=funcionario,
        )
        self.assertEqual(resposta_sem_permissao.status_code, 403)

        em_analise = self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/iniciar-analise",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(em_analise["status"], "EM_ANALISE")

        aprovada = self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/aprovar",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(aprovada["status"], "APROVADA")

        pedido = self.validar_status(
            self.client.post(
                "/pedidos/",
                headers=admin,
                json={
                    "id_solicitacao": id_solicitacao,
                    "id_fornecedor": fornecedor["id_fornecedor"],
                    "numero_pedido": "PED-E2E-001",
                    "data_pedido": date.today().isoformat(),
                    "observacao": "Pedido temporário.",
                },
            ),
            201,
        )
        id_pedido = pedido["id_pedido_compra"]

        historico_solicitacao = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}/historico",
                headers=funcionario,
            ),
            200,
        )
        acoes_historico_solicitacao = {
            evento["acao"] for evento in historico_solicitacao
        }
        self.assertTrue(
            {
                "CADASTRO",
                "ALTERACAO_STATUS",
                "APROVACAO",
                "PEDIDO_REALIZADO",
            }.issubset(acoes_historico_solicitacao)
        )

        detalhe_pedido = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}", headers=admin),
            200,
        )
        self.assertEqual(len(detalhe_pedido["itens"]), 1)
        self.assertEqual(float(detalhe_pedido["itens"][0]["quantidade"]), 2)
        id_item_pedido = detalhe_pedido["itens"][0]["id_item_pedido"]

        aguardando = self.validar_status(
            self.client.patch(
                f"/pedidos/{id_pedido}/aguardando-recebimento",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(aguardando["status"], "AGUARDANDO_RECEBIMENTO")

        recebimento_sem_itens = self.client.post(
            "/recebimentos/",
            headers=estoque,
            json={
                "id_pedido_compra": id_pedido,
                "numero_nota_fiscal": "NF-SEM-ITENS",
                "itens": [],
            },
        )
        self.assertEqual(recebimento_sem_itens.status_code, 400)

        recebimento_com_item_repetido = self.client.post(
            "/recebimentos/",
            headers=estoque,
            json={
                "id_pedido_compra": id_pedido,
                "numero_nota_fiscal": "NF-ITEM-REPETIDO",
                "itens": [
                    {
                        "id_item_pedido": id_item_pedido,
                        "quantidade_recebida": 0.5,
                    },
                    {
                        "id_item_pedido": id_item_pedido,
                        "quantidade_recebida": 0.5,
                    },
                ],
            },
        )
        self.assertEqual(recebimento_com_item_repetido.status_code, 400)

        recebimento_final = self.validar_status(
            self.client.post(
                "/recebimentos/",
                headers=estoque,
                json={
                    "id_pedido_compra": id_pedido,
                    "numero_nota_fiscal": "NF-E2E-001",
                    "observacao": "Recebimento parcial.",
                    "itens": [
                        {
                            "id_item_pedido": id_item_pedido,
                            "quantidade_recebida": 1,
                        }
                    ],
                },
            ),
            201,
        )
        parcial = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}", headers=estoque),
            200,
        )
        self.assertEqual(parcial["status"], "RECEBIDO_PARCIAL")
        self.assertEqual(float(parcial["itens"][0]["saldo_pendente"]), 1)

        self.validar_status(
            self.client.post(
                "/recebimentos/",
                headers=estoque,
                json={
                    "id_pedido_compra": id_pedido,
                    "numero_nota_fiscal": "NF-E2E-002",
                    "observacao": "Recebimento final.",
                    "itens": [
                        {
                            "id_item_pedido": id_item_pedido,
                            "quantidade_recebida": 1,
                        }
                    ],
                },
            ),
            201,
        )
        completo = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}", headers=estoque),
            200,
        )
        self.assertEqual(completo["status"], "RECEBIDO_TOTAL")
        self.assertEqual(float(completo["itens"][0]["saldo_pendente"]), 0)

        self.assertEqual(
            self.client.patch(
                f"/recebimentos/{recebimento_final['id_recebimento']}/estornar",
                headers=estoque,
                json={"motivo": "Lançamento incorreto"},
            ).status_code,
            403,
        )
        estornado = self.validar_status(
            self.client.patch(
                f"/recebimentos/{recebimento_final['id_recebimento']}/estornar",
                headers=admin,
                json={"motivo": "Quantidade lançada na nota errada"},
            ),
            200,
        )
        self.assertEqual(estornado["status"], "ESTORNADO")
        self.assertEqual(
            estornado["motivo_estorno"],
            "Quantidade lançada na nota errada",
        )
        apos_estorno = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}", headers=estoque),
            200,
        )
        self.assertEqual(apos_estorno["status"], "RECEBIDO_PARCIAL")
        self.assertEqual(float(apos_estorno["itens"][0]["saldo_pendente"]), 1)
        self.assertEqual(
            self.client.patch(
                f"/recebimentos/{recebimento_final['id_recebimento']}/estornar",
                headers=admin,
                json={"motivo": "Segundo estorno"},
            ).status_code,
            400,
        )

        historico_recebimentos = self.validar_status(
            self.client.get("/recebimentos/", headers=estoque),
            200,
        )
        recebimento_no_historico = next(
            item
            for item in historico_recebimentos
            if item["id_recebimento"] == recebimento_final["id_recebimento"]
        )
        self.assertEqual(recebimento_no_historico["status"], "ESTORNADO")
        self.assertEqual(len(recebimento_no_historico["itens"]), 1)

        self.validar_status(
            self.client.post(
                "/recebimentos/",
                headers=estoque,
                json={
                    "id_pedido_compra": id_pedido,
                    "numero_nota_fiscal": "NF-E2E-003",
                    "observacao": "Correção após estorno.",
                    "itens": [
                        {
                            "id_item_pedido": id_item_pedido,
                            "quantidade_recebida": 1,
                        }
                    ],
                },
            ),
            201,
        )
        corrigido = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}", headers=estoque),
            200,
        )
        self.assertEqual(corrigido["status"], "RECEBIDO_TOTAL")
        self.assertEqual(float(corrigido["itens"][0]["saldo_pendente"]), 0)
        self.assertEqual(
            self.client.patch(
                f"/pedidos/{id_pedido}/cancelar",
                headers=admin,
                json={"motivo": "Pedido já recebido não pode ser cancelado."},
            ).status_code,
            400,
        )

        historico_pedido = self.validar_status(
            self.client.get(
                f"/pedidos/{id_pedido}/historico",
                headers=estoque,
            ),
            200,
        )
        self.assertEqual(
            [evento["acao"] for evento in historico_pedido],
            [
                "CADASTRO",
                "ENVIO_RECEBIMENTO",
                "RECEBIMENTO_PARCIAL",
                "RECEBIMENTO_TOTAL",
                "ESTORNO_RECEBIMENTO",
                "RECEBIMENTO_TOTAL",
            ],
        )
        self.assertEqual(
            self.client.get(
                f"/pedidos/{id_pedido}/historico",
                headers=funcionario,
            ).status_code,
            403,
        )

        usuarios = self.validar_status(
            self.client.get("/usuarios/resumo/", headers=funcionario),
            200,
        )
        id_entregador = next(
            usuario["id_usuario"]
            for usuario in usuarios
            if usuario["nome"] == "Entregador Teste"
        )

        conteudo_anexo = b"%PDF-1.4\nArquivo de teste do pedido"
        anexo_enviado = self.validar_status(
            self.client.post(
                "/arquivos/entregas",
                headers={
                    **funcionario,
                    "Content-Type": "application/pdf",
                    "X-Nome-Arquivo": "pedido-integrado.pdf",
                },
                content=conteudo_anexo,
            ),
            200,
        )
        self.assertTrue(anexo_enviado["url"].startswith("/arquivos/entregas/"))

        download_anexo = self.client.get(
            anexo_enviado["url"],
            headers=funcionario,
        )
        self.assertEqual(download_anexo.status_code, 200)
        self.assertEqual(download_anexo.content, conteudo_anexo)

        entrega = self.validar_status(
            self.client.post(
                "/entregas/",
                headers=funcionario,
                json={
                    "id_cliente": cliente["id_cliente"],
                    "id_entregador": id_entregador,
                    "data_agendada": date.today().isoformat(),
                    "anexo_pedido": anexo_enviado["url"],
                    "observacao": "Entrega temporária.",
                },
            ),
            201,
        )
        id_entrega = entrega["id_entrega"]
        self.assertEqual(entrega["status"], "AGENDADA")

        outro_entregador = self.autenticar("entregador_dois_teste")
        download_anexo_responsavel = self.client.get(
            anexo_enviado["url"],
            headers=entregador,
        )
        self.assertEqual(download_anexo_responsavel.status_code, 200)
        self.assertEqual(download_anexo_responsavel.content, conteudo_anexo)
        self.assertEqual(
            self.client.get(
                anexo_enviado["url"],
                headers=outro_entregador,
            ).status_code,
            403,
        )

        entregas_do_responsavel = self.validar_status(
            self.client.get("/entregas/", headers=entregador),
            200,
        )
        entregas_do_outro = self.validar_status(
            self.client.get("/entregas/", headers=outro_entregador),
            200,
        )
        self.assertIn(
            id_entrega,
            {item["id_entrega"] for item in entregas_do_responsavel},
        )
        self.assertNotIn(
            id_entrega,
            {item["id_entrega"] for item in entregas_do_outro},
        )

        self.assertEqual(
            self.client.get(
                f"/entregas/{id_entrega}",
                headers=outro_entregador,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                f"/entregas/{id_entrega}/historico",
                headers=outro_entregador,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/em-rota",
                headers=outro_entregador,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/entregue",
                headers=outro_entregador,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/comprovante",
                headers=outro_entregador,
                json={"comprovante_entrega": "/arquivos/entregas/teste.png"},
            ).status_code,
            403,
        )

        resumo_entregador = self.validar_status(
            self.client.get("/dashboard/resumo", headers=entregador),
            200,
        )
        resumo_outro_entregador = self.validar_status(
            self.client.get("/dashboard/resumo", headers=outro_entregador),
            200,
        )
        resumo_funcionario = self.validar_status(
            self.client.get("/dashboard/resumo", headers=funcionario),
            200,
        )
        resumo_admin = self.validar_status(
            self.client.get("/dashboard/resumo", headers=admin),
            200,
        )

        self.assertIsNone(resumo_entregador["solicitacoes_em_andamento"])
        self.assertIsNone(resumo_entregador["pedidos_aguardando_recebimento"])
        self.assertEqual(resumo_entregador["entregas_em_aberto"], 1)
        self.assertEqual(resumo_outro_entregador["entregas_em_aberto"], 0)
        self.assertEqual(resumo_funcionario["solicitacoes_em_andamento"], 0)
        self.assertIsNone(resumo_funcionario["pedidos_aguardando_recebimento"])
        self.assertEqual(resumo_admin["pedidos_aguardando_recebimento"], 0)
        self.assertEqual(resumo_admin["entregas_em_aberto"], 1)

        entrega_para_cancelar = self.validar_status(
            self.client.post(
                "/entregas/",
                headers=funcionario,
                json={
                    "id_cliente": cliente["id_cliente"],
                    "observacao": "Entrega criada para validar cancelamento.",
                },
            ),
            201,
        )
        id_entrega_cancelada = entrega_para_cancelar["id_entrega"]

        cancelamento_sem_permissao = self.client.patch(
            f"/entregas/{id_entrega_cancelada}/cancelar",
            headers=funcionario,
            json={"motivo": "Entrega duplicada."},
        )
        self.assertEqual(cancelamento_sem_permissao.status_code, 403)

        entrega_cancelada = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega_cancelada}/cancelar",
                headers=admin,
                json={"motivo": "Entrega cadastrada em duplicidade."},
            ),
            200,
        )
        self.assertEqual(entrega_cancelada["status"], "CANCELADA")
        self.assertEqual(
            entrega_cancelada["motivo_cancelamento"],
            "Entrega cadastrada em duplicidade.",
        )
        self.assertIsNotNone(entrega_cancelada["data_cancelamento"])
        self.assertIsNotNone(entrega_cancelada["id_usuario_cancelamento"])

        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega_cancelada}/cancelar",
                headers=admin,
                json={"motivo": "Tentar cancelar novamente."},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega_cancelada}/agendar",
                headers=funcionario,
            ).status_code,
            400,
        )

        historico_cancelamento = self.validar_status(
            self.client.get(
                f"/entregas/{id_entrega_cancelada}/historico",
                headers=funcionario,
            ),
            200,
        )
        self.assertEqual(historico_cancelamento[-1]["acao"], "CANCELAMENTO")
        self.assertIn(
            "Entrega cadastrada em duplicidade.",
            historico_cancelamento[-1]["descricao"],
        )

        resumo_apos_cancelamento = self.validar_status(
            self.client.get("/dashboard/resumo", headers=admin),
            200,
        )
        self.assertEqual(resumo_apos_cancelamento["entregas_em_aberto"], 1)

        data_passada = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/agendamento",
                headers=funcionario,
                json={"data_agendada": data_passada},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/agendamento",
                headers=entregador,
                json={"data_agendada": date.today().isoformat()},
            ).status_code,
            403,
        )

        primeira_data = date.today() + timedelta(days=1)
        entrega_agendada = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/agendamento",
                headers=funcionario,
                json={"data_agendada": primeira_data.isoformat()},
            ),
            200,
        )
        self.assertEqual(entrega_agendada["status"], "AGENDADA")
        self.assertEqual(
            entrega_agendada["data_agendada"],
            primeira_data.isoformat(),
        )

        segunda_data = date.today() + timedelta(days=2)
        entrega_reagendada = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/agendamento",
                headers=funcionario,
                json={"data_agendada": segunda_data.isoformat()},
            ),
            200,
        )
        self.assertEqual(
            entrega_reagendada["data_agendada"],
            segunda_data.isoformat(),
        )

        transicoes = [
            ("iniciar-separacao", funcionario, "EM_SEPARACAO"),
            ("pronta", funcionario, "PRONTA_PARA_ENTREGA"),
            ("em-rota", entregador, "EM_ROTA"),
        ]
        for acao, cabecalhos, status_esperado in transicoes:
            entrega_atualizada = self.validar_status(
                self.client.patch(
                    f"/entregas/{id_entrega}/{acao}",
                    headers=cabecalhos,
                ),
                200,
            )
            self.assertEqual(entrega_atualizada["status"], status_esperado)

        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/nao-entregue",
                headers=entregador,
                json={"motivo": "  "},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/nao-entregue",
                headers=outro_entregador,
                json={"motivo": "Cliente ausente."},
            ).status_code,
            403,
        )

        nao_entregue = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/nao-entregue",
                headers=entregador,
                json={"motivo": "Cliente ausente no endereço."},
            ),
            200,
        )
        self.assertEqual(nao_entregue["status"], "NAO_ENTREGUE")
        self.assertEqual(
            nao_entregue["motivo_nao_entrega"],
            "Cliente ausente no endereço.",
        )
        self.assertIsNotNone(nao_entregue["data_ultima_tentativa"])
        self.assertIsNotNone(nao_entregue["id_usuario_ultima_tentativa"])

        nova_tentativa = date.today() + timedelta(days=3)
        reagendada_apos_tentativa = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/agendamento",
                headers=funcionario,
                json={"data_agendada": nova_tentativa.isoformat()},
            ),
            200,
        )
        self.assertEqual(reagendada_apos_tentativa["status"], "AGENDADA")

        novas_transicoes = [
            ("iniciar-separacao", funcionario, "EM_SEPARACAO"),
            ("pronta", funcionario, "PRONTA_PARA_ENTREGA"),
            ("em-rota", entregador, "EM_ROTA"),
            ("entregue", entregador, "ENTREGUE"),
        ]
        for acao, cabecalhos, status_esperado in novas_transicoes:
            entrega_atualizada = self.validar_status(
                self.client.patch(
                    f"/entregas/{id_entrega}/{acao}",
                    headers=cabecalhos,
                ),
                200,
            )
            self.assertEqual(entrega_atualizada["status"], status_esperado)

        self.assertEqual(
            self.client.patch(
                f"/entregas/{id_entrega}/cancelar",
                headers=admin,
                json={"motivo": "Cancelamento tardio."},
            ).status_code,
            400,
        )

        comprovante_inexistente = self.client.patch(
            f"/entregas/{id_entrega}/comprovante",
            headers=entregador,
            json={
                "comprovante_entrega": (
                    "/arquivos/entregas/"
                    "00000000000000000000000000000000-inexistente.png"
                )
            },
        )
        self.assertEqual(comprovante_inexistente.status_code, 400)

        conteudo_comprovante = b"\x89PNG\r\n\x1a\ncomprovante-teste"
        comprovante_enviado = self.validar_status(
            self.client.post(
                "/arquivos/entregas",
                headers={
                    **entregador,
                    "Content-Type": "image/png",
                    "X-Nome-Arquivo": "comprovante.png",
                },
                content=conteudo_comprovante,
            ),
            200,
        )
        entrega_com_comprovante = self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/comprovante",
                headers=entregador,
                json={"comprovante_entrega": comprovante_enviado["url"]},
            ),
            200,
        )
        self.assertEqual(
            entrega_com_comprovante["comprovante_entrega"],
            comprovante_enviado["url"],
        )
        download_comprovante_responsavel = self.client.get(
            comprovante_enviado["url"],
            headers=entregador,
        )
        self.assertEqual(download_comprovante_responsavel.status_code, 200)
        self.assertEqual(
            download_comprovante_responsavel.content,
            conteudo_comprovante,
        )
        self.assertEqual(
            self.client.get(
                comprovante_enviado["url"],
                headers=outro_entregador,
            ).status_code,
            403,
        )

        historico = self.validar_status(
            self.client.get(
                f"/entregas/{id_entrega}/historico",
                headers=funcionario,
            ),
            200,
        )
        self.assertEqual(len(historico), 14)
        self.assertEqual(historico[-1]["acao"], "ANEXO_COMPROVANTE")
        self.assertEqual(historico[1]["acao"], "AGENDAMENTO")
        self.assertEqual(historico[2]["acao"], "REAGENDAMENTO")
        self.assertEqual(historico[3]["acao"], "REAGENDAMENTO")
        self.assertEqual(historico[7]["acao"], "NAO_ENTREGA")
        self.assertEqual(historico[8]["acao"], "REAGENDAMENTO")

        notificacoes_funcionario = self.validar_status(
            self.client.get("/notificacoes/", headers=funcionario),
            200,
        )
        titulos_funcionario = {
            notificacao["titulo"] for notificacao in notificacoes_funcionario
        }
        self.assertTrue(
            {
                "Solicitação aprovada",
                "Pedido recebido",
                "Entrega não concluída",
                "Entrega concluída",
            }
            <= titulos_funcionario
        )

        notificacoes_entregador = self.validar_status(
            self.client.get("/notificacoes/", headers=entregador),
            200,
        )
        self.assertIn(
            "Entrega pronta",
            {notificacao["titulo"] for notificacao in notificacoes_entregador},
        )

        resumo = self.validar_status(
            self.client.get(
                "/relatorios/resumo",
                headers=admin,
                params={
                    "data_inicio": date.today().isoformat(),
                    "data_fim": date.today().isoformat(),
                },
            ),
            200,
        )
        self.assertGreaterEqual(resumo["solicitacoes"]["total"], 1)
        self.assertGreaterEqual(resumo["pedidos"]["total"], 1)
        self.assertEqual(resumo["recebimentos"]["total"], 2)
        self.assertEqual(resumo["entregas"]["por_status"]["ENTREGUE"], 1)
        self.assertEqual(resumo["entregas"]["por_status"]["CANCELADA"], 1)
        self.assertEqual(
            resumo["produtos_mais_solicitados"][0]["id_produto"],
            produto["id_produto"],
        )
        self.assertEqual(
            resumo["fornecedores_mais_utilizados"][0]["id_fornecedor"],
            fornecedor["id_fornecedor"],
        )

        exportacao_csv = self.client.get(
            "/relatorios/exportar.csv",
            headers=admin,
            params={
                "data_inicio": date.today().isoformat(),
                "data_fim": date.today().isoformat(),
            },
        )
        self.assertEqual(exportacao_csv.status_code, 200, exportacao_csv.text)
        self.assertTrue(exportacao_csv.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn("text/csv", exportacao_csv.headers["content-type"])
        self.assertIn(
            "attachment; filename=",
            exportacao_csv.headers["content-disposition"],
        )
        conteudo_csv = exportacao_csv.content.decode("utf-8-sig")
        self.assertIn("Relatório gerencial FCL", conteudo_csv)
        self.assertIn("Produto de teste integrado", conteudo_csv)
        self.assertIn("Fornecedor E2E", conteudo_csv)

        relatorio_sem_permissao = self.client.get(
            "/relatorios/resumo",
            headers=funcionario,
        )
        self.assertEqual(relatorio_sem_permissao.status_code, 403)

        exportacao_sem_permissao = self.client.get(
            "/relatorios/exportar.csv",
            headers=funcionario,
        )
        self.assertEqual(exportacao_sem_permissao.status_code, 403)

        periodo_invalido = self.client.get(
            "/relatorios/resumo",
            headers=admin,
            params={
                "data_inicio": "2026-02-02",
                "data_fim": "2026-02-01",
            },
        )
        self.assertEqual(periodo_invalido.status_code, 400)

    def test_t_entrega_pode_ser_editada_antes_de_entrar_em_rota(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        entregador = self.autenticar("entregador_teste")

        clientes = []
        for indice in (1, 2):
            clientes.append(
                self.validar_status(
                    self.client.post(
                        "/clientes/",
                        headers=funcionario,
                        json={
                            "nome": f"Cliente Edicao Entrega {indice}",
                            "cpf_cnpj": None,
                            "telefone": f"1198888000{indice}",
                            "endereco": "Rua de Teste",
                            "numero": str(indice),
                            "bairro": "Centro",
                            "cidade": "Sao Paulo",
                            "uf": "SP",
                        },
                    ),
                    201,
                )
            )

        usuarios = self.validar_status(
            self.client.get("/usuarios/resumo/", headers=funcionario),
            200,
        )
        id_entregador_dois = next(
            usuario["id_usuario"]
            for usuario in usuarios
            if usuario["nome"] == "ZZ Entregador Dois"
        )

        entrega = self.validar_status(
            self.client.post(
                "/entregas/",
                headers=funcionario,
                json={
                    "id_cliente": clientes[0]["id_cliente"],
                    "observacao": "Dados originais.",
                },
            ),
            201,
        )
        id_entrega = entrega["id_entrega"]
        dados_atualizados = {
            "id_cliente": clientes[1]["id_cliente"],
            "id_entregador": id_entregador_dois,
            "data_agendada": date.today().isoformat(),
            "observacao": "Dados corrigidos antes da rota.",
        }

        self.assertEqual(
            self.client.put(
                f"/entregas/{id_entrega}",
                headers=entregador,
                json=dados_atualizados,
            ).status_code,
            403,
        )

        editada = self.validar_status(
            self.client.put(
                f"/entregas/{id_entrega}",
                headers=funcionario,
                json=dados_atualizados,
            ),
            200,
        )
        self.assertEqual(editada["status"], "AGENDADA")
        self.assertEqual(editada["id_cliente"], clientes[1]["id_cliente"])
        self.assertEqual(editada["id_entregador"], id_entregador_dois)
        self.assertEqual(editada["data_agendada"], date.today().isoformat())
        self.assertEqual(editada["observacao"], dados_atualizados["observacao"])

        self.assertEqual(
            self.client.put(
                f"/entregas/{id_entrega}",
                headers=funcionario,
                json=dados_atualizados,
            ).status_code,
            400,
        )

        for rota in ("iniciar-separacao", "pronta"):
            self.validar_status(
                self.client.patch(
                    f"/entregas/{id_entrega}/{rota}",
                    headers=funcionario,
                ),
                200,
            )

        dados_atualizados["observacao"] = "Ultima correcao antes da rota."
        self.validar_status(
            self.client.put(
                f"/entregas/{id_entrega}",
                headers=admin,
                json=dados_atualizados,
            ),
            200,
        )
        self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/em-rota",
                headers=admin,
            ),
            200,
        )
        dados_atualizados["observacao"] = "Edicao tardia."
        self.assertEqual(
            self.client.put(
                f"/entregas/{id_entrega}",
                headers=admin,
                json=dados_atualizados,
            ).status_code,
            400,
        )
        self.validar_status(
            self.client.patch(
                f"/entregas/{id_entrega}/entregue",
                headers=admin,
            ),
            200,
        )

        historico = self.validar_status(
            self.client.get(
                f"/entregas/{id_entrega}/historico",
                headers=funcionario,
            ),
            200,
        )
        edicoes = [evento for evento in historico if evento["acao"] == "EDICAO"]
        self.assertEqual(len(edicoes), 2)
        self.assertIn("cliente", edicoes[0]["descricao"])
        self.assertIn("entregador", edicoes[0]["descricao"])
        self.assertIn("data agendada", edicoes[0]["descricao"])
        self.assertIn("observ", edicoes[0]["descricao"])
        self.assertIn("CADASTRADA para AGENDADA", edicoes[0]["descricao"])

    def test_rejeicao_exige_motivo_e_notifica_solicitante(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        produto = self.criar_produto(admin, "PROD-E2E-REJEICAO")

        solicitacao = self.validar_status(
            self.client.post(
                "/solicitacoes/",
                headers=funcionario,
                json={
                    "prioridade": "BAIXA",
                    "motivo": "Validar rejeição",
                    "itens": [
                        {
                            "id_produto": produto["id_produto"],
                            "quantidade": 1,
                        }
                    ],
                },
            ),
            201,
        )
        id_solicitacao = solicitacao["id_solicitacao"]

        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/iniciar-analise",
                headers=admin,
            ),
            200,
        )

        sem_motivo = self.client.patch(
            f"/solicitacoes/{id_solicitacao}/rejeitar",
            headers=admin,
            json={"motivo_rejeicao": "   "},
        )
        self.assertEqual(sem_motivo.status_code, 422)

        rejeitada = self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/rejeitar",
                headers=admin,
                json={"motivo_rejeicao": "Compra não necessária neste momento."},
            ),
            200,
        )
        self.assertEqual(rejeitada["status"], "REJEITADA")
        self.assertEqual(
            rejeitada["motivo_rejeicao"],
            "Compra não necessária neste momento.",
        )

        notificacoes = self.validar_status(
            self.client.get("/notificacoes/", headers=funcionario),
            200,
        )
        self.assertIn(
            "Solicitação rejeitada",
            {notificacao["titulo"] for notificacao in notificacoes},
        )

    def test_relatorio_aceita_data_final_maxima(self):
        admin = self.autenticar("admin_teste")

        resposta = self.client.get(
            "/relatorios/resumo?data_fim=9999-12-31",
            headers=admin,
        )

        self.assertEqual(resposta.status_code, 200, resposta.text)

    def test_solicitacao_pode_ser_cancelada_sem_apagar_o_historico(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        estoque = self.autenticar("estoque_teste")
        produto = self.criar_produto(admin, "PROD-E2E-CANCEL-SOL")

        def criar_solicitacao(motivo):
            return self.validar_status(
                self.client.post(
                    "/solicitacoes/",
                    headers=funcionario,
                    json={
                        "prioridade": "BAIXA",
                        "motivo": motivo,
                        "itens": [
                            {
                                "id_produto": produto["id_produto"],
                                "quantidade": 1,
                            }
                        ],
                    },
                ),
                201,
            )

        propria = criar_solicitacao("Cancelar pelo solicitante")
        id_propria = propria["id_solicitacao"]

        self.assertEqual(
            self.client.patch(
                f"/solicitacoes/{id_propria}/cancelar",
                headers=estoque,
                json={"motivo": "Solicitação incorreta."},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/solicitacoes/{id_propria}/cancelar",
                headers=funcionario,
                json={"motivo": "  "},
            ).status_code,
            422,
        )

        cancelada = self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_propria}/cancelar",
                headers=funcionario,
                json={"motivo": "Solicitação criada em duplicidade."},
            ),
            200,
        )
        self.assertEqual(cancelada["status"], "CANCELADA")
        self.assertEqual(
            cancelada["motivo_cancelamento"],
            "Solicitação criada em duplicidade.",
        )
        self.assertIsNotNone(cancelada["data_cancelamento"])
        self.assertIsNotNone(cancelada["id_usuario_cancelamento"])
        self.assertEqual(
            self.client.patch(
                f"/solicitacoes/{id_propria}/cancelar",
                headers=admin,
                json={"motivo": "Cancelar novamente."},
            ).status_code,
            400,
        )

        para_admin = criar_solicitacao("Cancelar durante a análise")
        id_para_admin = para_admin["id_solicitacao"]
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_para_admin}/iniciar-analise",
                headers=admin,
            ),
            200,
        )
        cancelada_admin = self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_para_admin}/cancelar",
                headers=admin,
                json={"motivo": "Necessidade de compra removida."},
            ),
            200,
        )
        self.assertEqual(cancelada_admin["status"], "CANCELADA")

        com_pedido = criar_solicitacao("Bloquear cancelamento com pedido")
        id_com_pedido = com_pedido["id_solicitacao"]
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_com_pedido}/iniciar-analise",
                headers=admin,
            ),
            200,
        )
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_com_pedido}/aprovar",
                headers=admin,
            ),
            200,
        )

        db = self.session_factory()
        try:
            fornecedor = Fornecedor(
                razao_social="Fornecedor para bloqueio de cancelamento",
                ativo=True,
            )
            db.add(fornecedor)
            db.flush()
            db.add(
                PedidoCompra(
                    id_solicitacao=id_com_pedido,
                    id_fornecedor=fornecedor.id_fornecedor,
                    numero_pedido="PED-BLOQUEIO-CANCEL-SOL",
                    data_pedido=date.today(),
                    status="CRIADO",
                )
            )
            db.commit()
        finally:
            db.close()

        self.assertEqual(
            self.client.patch(
                f"/solicitacoes/{id_com_pedido}/cancelar",
                headers=admin,
                json={"motivo": "Tentativa com pedido ativo."},
            ).status_code,
            400,
        )

        db = self.session_factory()
        try:
            eventos = db.query(Historico).filter(
                Historico.tipo_registro == "SOLICITACAO",
                Historico.id_registro.in_([id_propria, id_para_admin]),
                Historico.acao == "CANCELAMENTO",
            ).all()
            self.assertEqual(len(eventos), 2)
        finally:
            db.close()

        notificacoes = self.validar_status(
            self.client.get("/notificacoes/", headers=funcionario),
            200,
        )
        self.assertIn(
            "Solicitação cancelada",
            {notificacao["titulo"] for notificacao in notificacoes},
        )

    def test_solicitacao_solicitada_pode_ser_editada_pelo_solicitante(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        estoque = self.autenticar("estoque_teste")
        produto_um = self.criar_produto(admin, "PROD-E2E-EDIT-SOL-1")
        produto_dois = self.criar_produto(admin, "PROD-E2E-EDIT-SOL-2")

        solicitacao = self.validar_status(
            self.client.post(
                "/solicitacoes/",
                headers=funcionario,
                json={
                    "prioridade": "BAIXA",
                    "motivo": "Dados antes da edição",
                    "itens": [
                        {
                            "id_produto": produto_um["id_produto"],
                            "quantidade": 1,
                        }
                    ],
                },
            ),
            201,
        )
        id_solicitacao = solicitacao["id_solicitacao"]
        dados_atualizados = {
            "prioridade": "ALTA",
            "motivo": "Dados corrigidos pelo solicitante",
            "observacao": "Quantidade e produtos revisados.",
            "itens": [
                {
                    "id_produto": produto_um["id_produto"],
                    "quantidade": 2,
                },
                {
                    "id_produto": produto_dois["id_produto"],
                    "quantidade": 3,
                },
            ],
        }

        self.assertEqual(
            self.client.put(
                f"/solicitacoes/{id_solicitacao}",
                headers=estoque,
                json=dados_atualizados,
            ).status_code,
            403,
        )

        atualizada = self.validar_status(
            self.client.put(
                f"/solicitacoes/{id_solicitacao}",
                headers=funcionario,
                json=dados_atualizados,
            ),
            200,
        )
        self.assertEqual(atualizada["status"], "SOLICITADA")
        self.assertEqual(atualizada["prioridade"], "ALTA")
        self.assertEqual(atualizada["motivo"], dados_atualizados["motivo"])
        self.assertEqual(len(atualizada["itens"]), 2)
        quantidades = {
            item["id_produto"]: float(item["quantidade"])
            for item in atualizada["itens"]
        }
        self.assertEqual(quantidades[produto_um["id_produto"]], 2)
        self.assertEqual(quantidades[produto_dois["id_produto"]], 3)

        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/iniciar-analise",
                headers=admin,
            ),
            200,
        )

        historico = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}/historico",
                headers=funcionario,
            ),
            200,
        )
        self.assertEqual(
            [evento["acao"] for evento in historico],
            ["CADASTRO", "EDICAO", "ALTERACAO_STATUS"],
        )
        self.assertEqual(
            self.client.put(
                f"/solicitacoes/{id_solicitacao}",
                headers=funcionario,
                json=dados_atualizados,
            ).status_code,
            400,
        )

        db = self.session_factory()
        try:
            evento = db.query(Historico).filter(
                Historico.tipo_registro == "SOLICITACAO",
                Historico.id_registro == id_solicitacao,
                Historico.acao == "EDICAO",
            ).one()
            self.assertIn("Prioridade: BAIXA para ALTA", evento.descricao)
        finally:
            db.close()

    def test_gestao_administrativa_de_usuarios(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")

        usuarios = self.validar_status(
            self.client.get("/usuarios/", headers=admin),
            200,
        )
        self.assertGreaterEqual(len(usuarios), 5)

        sem_permissao = self.client.get("/usuarios/", headers=funcionario)
        self.assertEqual(sem_permissao.status_code, 403)

        novo_usuario = self.validar_status(
            self.client.post(
                "/usuarios/",
                headers=admin,
                json={
                    "nome": "Usuário Gerenciado",
                    "login": "usuario_gerenciado",
                    "senha": "senha123",
                    "perfil": "FUNCIONARIO",
                },
            ),
            201,
        )
        id_usuario = novo_usuario["id_usuario"]
        login_antes_redefinicao = self.validar_status(
            self.client.post(
                "/login",
                json={"login": "usuario_gerenciado", "senha": "senha123"},
            ),
            200,
        )
        sessao_antes_redefinicao = {
            "Authorization": (
                f"Bearer {login_antes_redefinicao['access_token']}"
            )
        }

        duplicado = self.client.post(
            "/usuarios/",
            headers=admin,
            json={
                "nome": "Login Duplicado",
                "login": "usuario_gerenciado",
                "senha": "senha123",
                "perfil": "ESTOQUE",
            },
        )
        self.assertEqual(duplicado.status_code, 400)

        atualizado = self.validar_status(
            self.client.put(
                f"/usuarios/{id_usuario}",
                headers=admin,
                json={
                    "nome": "Usuário Atualizado",
                    "perfil": "ESTOQUE",
                    "senha": "novaSenha123",
                },
            ),
            200,
        )
        self.assertEqual(atualizado["perfil"], "ESTOQUE")
        self.assertEqual(
            self.client.get(
                "/me",
                headers=sessao_antes_redefinicao,
            ).status_code,
            401,
        )

        desativado = self.validar_status(
            self.client.patch(
                f"/usuarios/{id_usuario}/desativar",
                headers=admin,
            ),
            200,
        )
        self.assertFalse(desativado["ativo"])

        login_desativado = self.client.post(
            "/login",
            json={"login": "usuario_gerenciado", "senha": "novaSenha123"},
        )
        self.assertEqual(login_desativado.status_code, 403)

        reativado = self.validar_status(
            self.client.put(
                f"/usuarios/{id_usuario}",
                headers=admin,
                json={"ativo": True},
            ),
            200,
        )
        self.assertTrue(reativado["ativo"])

        login_reativado = self.client.post(
            "/login",
            json={"login": "usuario_gerenciado", "senha": "novaSenha123"},
        )
        self.assertEqual(login_reativado.status_code, 200)

        usuario_atual = self.validar_status(
            self.client.get("/me", headers=admin),
            200,
        )
        id_usuario_atual = usuario_atual["id_usuario"]

        autodesativacao = self.client.patch(
            f"/usuarios/{id_usuario_atual}/desativar",
            headers=admin,
        )
        self.assertEqual(autodesativacao.status_code, 400)

        alterar_proprio_perfil = self.client.put(
            f"/usuarios/{id_usuario_atual}",
            headers=admin,
            json={"perfil": "FUNCIONARIO"},
        )
        self.assertEqual(alterar_proprio_perfil.status_code, 400)

        db = self.session_factory()
        try:
            eventos = db.query(Historico).filter(
                Historico.tipo_registro == "USUARIO",
                Historico.id_registro == id_usuario,
            ).all()
            acoes = {evento.acao for evento in eventos}
            descricoes = " ".join(evento.descricao for evento in eventos)

            self.assertTrue(
                {"CADASTRO", "EDICAO", "DESATIVACAO", "ATIVACAO"}
                .issubset(acoes)
            )
            self.assertNotIn("novaSenha123", descricoes)
        finally:
            db.close()

    def test_marcar_todas_notificacoes_como_lidas_respeita_o_usuario(self):
        db = self.session_factory()
        try:
            funcionario = db.query(Usuario).filter(
                Usuario.login == "funcionario_teste"
            ).first()
            administrador = db.query(Usuario).filter(
                Usuario.login == "admin_teste"
            ).first()
            notificacoes_funcionario = [
                Notificacao(
                    id_usuario=funcionario.id_usuario,
                    titulo="Notificacao em lote 1",
                    mensagem="Primeira notificacao do teste.",
                    lida=False,
                    data_hora=datetime.now(),
                ),
                Notificacao(
                    id_usuario=funcionario.id_usuario,
                    titulo="Notificacao em lote 2",
                    mensagem="Segunda notificacao do teste.",
                    lida=False,
                    data_hora=datetime.now(),
                ),
            ]
            notificacao_administrador = Notificacao(
                id_usuario=administrador.id_usuario,
                titulo="Notificacao de outra conta",
                mensagem="Nao deve ser alterada pelo funcionario.",
                lida=False,
                data_hora=datetime.now(),
            )
            db.add_all([*notificacoes_funcionario, notificacao_administrador])
            db.commit()
            ids_funcionario = [
                notificacao.id_notificacao
                for notificacao in notificacoes_funcionario
            ]
            id_notificacao_administrador = notificacao_administrador.id_notificacao
        finally:
            db.close()

        headers = self.autenticar("funcionario_teste")
        resposta = self.validar_status(
            self.client.patch("/notificacoes/todas/lidas", headers=headers),
            200,
        )
        self.assertGreaterEqual(resposta["quantidade_atualizada"], 2)

        segunda_tentativa = self.validar_status(
            self.client.patch("/notificacoes/todas/lidas", headers=headers),
            200,
        )
        self.assertEqual(segunda_tentativa["quantidade_atualizada"], 0)

        db = self.session_factory()
        try:
            atualizadas = db.query(Notificacao).filter(
                Notificacao.id_notificacao.in_(ids_funcionario)
            ).all()
            outra_conta = db.query(Notificacao).filter(
                Notificacao.id_notificacao == id_notificacao_administrador
            ).first()

            self.assertTrue(all(notificacao.lida for notificacao in atualizadas))
            self.assertFalse(outra_conta.lida)
        finally:
            db.close()

    def test_solicitacao_pode_gerar_pedidos_para_fornecedores_diferentes(self):
        admin = self.autenticar("admin_teste")
        funcionario = self.autenticar("funcionario_teste")
        produto_um = self.criar_produto(admin, "PROD-E2E-DIVISAO-1")
        produto_dois = self.criar_produto(admin, "PROD-E2E-DIVISAO-2")

        fornecedores = []
        for indice, cnpj in enumerate(
            ("12345678000195", "98765432000198"),
            start=1,
        ):
            fornecedores.append(
                self.validar_status(
                    self.client.post(
                        "/fornecedores/",
                        headers=admin,
                        json={
                            "razao_social": f"Fornecedor Divisão {indice}",
                            "nome_fantasia": f"Fornecedor Divisão {indice}",
                            "cnpj": cnpj,
                        },
                    ),
                    201,
                )
            )

        solicitacao = self.validar_status(
            self.client.post(
                "/solicitacoes/",
                headers=funcionario,
                json={
                    "prioridade": "MEDIA",
                    "motivo": "Compra dividida entre fornecedores",
                    "itens": [
                        {
                            "id_produto": produto_um["id_produto"],
                            "quantidade": 3,
                        },
                        {
                            "id_produto": produto_dois["id_produto"],
                            "quantidade": 4,
                        },
                    ],
                },
            ),
            201,
        )
        id_solicitacao = solicitacao["id_solicitacao"]
        itens = solicitacao["itens"]

        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/iniciar-analise",
                headers=admin,
            ),
            200,
        )
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/aprovar",
                headers=admin,
            ),
            200,
        )

        primeiro_pedido = self.validar_status(
            self.client.post(
                "/pedidos/",
                headers=admin,
                json={
                    "id_solicitacao": id_solicitacao,
                    "id_fornecedor": fornecedores[0]["id_fornecedor"],
                    "numero_pedido": "PED-E2E-DIVISAO-1",
                    "data_pedido": date.today().isoformat(),
                    "itens": [
                        {
                            "id_item_solicitacao": itens[0]["id_item_solicitacao"],
                            "quantidade": 2,
                        }
                    ],
                },
            ),
            201,
        )
        solicitacao_parcial = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(solicitacao_parcial["status"], "APROVADA")

        segundo_pedido = self.validar_status(
            self.client.post(
                "/pedidos/",
                headers=admin,
                json={
                    "id_solicitacao": id_solicitacao,
                    "id_fornecedor": fornecedores[1]["id_fornecedor"],
                    "numero_pedido": "PED-E2E-DIVISAO-2",
                    "data_pedido": date.today().isoformat(),
                    "itens": [
                        {
                            "id_item_solicitacao": itens[0]["id_item_solicitacao"],
                            "quantidade": 1,
                        },
                        {
                            "id_item_solicitacao": itens[1]["id_item_solicitacao"],
                            "quantidade": 4,
                        },
                    ],
                },
            ),
            201,
        )
        solicitacao_completa = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(
            solicitacao_completa["status"],
            "PEDIDO_REALIZADO",
        )

        pedidos = self.validar_status(
            self.client.get("/pedidos/", headers=admin),
            200,
        )
        pedidos_divididos = {
            pedido["id_pedido_compra"]: pedido
            for pedido in pedidos
            if pedido["id_pedido_compra"] in {
                primeiro_pedido["id_pedido_compra"],
                segundo_pedido["id_pedido_compra"],
            }
        }
        self.assertEqual(
            len(pedidos_divididos[primeiro_pedido["id_pedido_compra"]]["itens"]),
            1,
        )
        self.assertEqual(
            len(pedidos_divididos[segundo_pedido["id_pedido_compra"]]["itens"]),
            2,
        )

        self.assertEqual(
            self.client.patch(
                f"/pedidos/{primeiro_pedido['id_pedido_compra']}/cancelar",
                headers=admin,
                json={"motivo": "  "},
            ).status_code,
            422,
        )
        cancelado = self.validar_status(
            self.client.patch(
                f"/pedidos/{primeiro_pedido['id_pedido_compra']}/cancelar",
                headers=admin,
                json={"motivo": "Fornecedor não atenderá este item."},
            ),
            200,
        )
        self.assertEqual(cancelado["status"], "CANCELADO")
        self.assertEqual(
            cancelado["motivo_cancelamento"],
            "Fornecedor não atenderá este item.",
        )
        self.assertIsNotNone(cancelado["data_cancelamento"])
        self.assertIsNotNone(cancelado["id_usuario_cancelamento"])
        historico_primeiro_pedido = self.validar_status(
            self.client.get(
                f"/pedidos/{primeiro_pedido['id_pedido_compra']}/historico",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(
            [evento["acao"] for evento in historico_primeiro_pedido],
            ["CADASTRO", "CANCELAMENTO"],
        )
        self.assertIn(
            "Fornecedor não atenderá este item.",
            historico_primeiro_pedido[-1]["descricao"],
        )
        solicitacao_reaberta = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(solicitacao_reaberta["status"], "APROVADA")

        acima_do_saldo = self.client.post(
            "/pedidos/",
            headers=admin,
            json={
                "id_solicitacao": id_solicitacao,
                "id_fornecedor": fornecedores[0]["id_fornecedor"],
                "numero_pedido": "PED-E2E-DIVISAO-3",
                "data_pedido": date.today().isoformat(),
                "itens": [
                    {
                        "id_item_solicitacao": itens[0]["id_item_solicitacao"],
                        "quantidade": 3,
                    }
                ],
            },
        )
        self.assertEqual(acima_do_saldo.status_code, 400)

        reposicao = self.validar_status(
            self.client.post(
                "/pedidos/",
                headers=admin,
                json={
                    "id_solicitacao": id_solicitacao,
                    "id_fornecedor": fornecedores[0]["id_fornecedor"],
                    "numero_pedido": "PED-E2E-DIVISAO-REPOSICAO",
                    "data_pedido": date.today().isoformat(),
                    "itens": [
                        {
                            "id_item_solicitacao": itens[0]["id_item_solicitacao"],
                            "quantidade": 2,
                        }
                    ],
                },
            ),
            201,
        )
        self.assertIsNotNone(reposicao["id_pedido_compra"])
        solicitacao_concluida_novamente = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(
            solicitacao_concluida_novamente["status"],
            "PEDIDO_REALIZADO",
        )

        db = self.session_factory()
        try:
            evento_cancelamento = db.query(Historico).filter(
                Historico.tipo_registro == "PEDIDO",
                Historico.id_registro == primeiro_pedido["id_pedido_compra"],
                Historico.acao == "CANCELAMENTO",
            ).first()
            self.assertIsNotNone(evento_cancelamento)
        finally:
            db.close()

    def test_pedido_criado_pode_ser_editado_com_recalculo_de_saldo(self):
        admin = self.autenticar("admin_teste")
        estoque = self.autenticar("estoque_teste")
        funcionario = self.autenticar("funcionario_teste")
        produto = self.criar_produto(admin, "PROD-E2E-EDICAO-PEDIDO")

        fornecedores = []
        for indice, cnpj in enumerate(
            ("22333444000181", "33444555000181"),
            start=1,
        ):
            fornecedores.append(
                self.validar_status(
                    self.client.post(
                        "/fornecedores/",
                        headers=admin,
                        json={
                            "razao_social": f"Fornecedor Edição {indice}",
                            "nome_fantasia": f"Fornecedor Edição {indice}",
                            "cnpj": cnpj,
                        },
                    ),
                    201,
                )
            )

        solicitacao = self.validar_status(
            self.client.post(
                "/solicitacoes/",
                headers=funcionario,
                json={
                    "prioridade": "MEDIA",
                    "motivo": "Validar edição do pedido",
                    "itens": [
                        {
                            "id_produto": produto["id_produto"],
                            "quantidade": 5,
                        }
                    ],
                },
            ),
            201,
        )
        id_solicitacao = solicitacao["id_solicitacao"]
        id_item_solicitacao = solicitacao["itens"][0]["id_item_solicitacao"]
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/iniciar-analise",
                headers=admin,
            ),
            200,
        )
        self.validar_status(
            self.client.patch(
                f"/solicitacoes/{id_solicitacao}/aprovar",
                headers=admin,
            ),
            200,
        )

        pedido = self.validar_status(
            self.client.post(
                "/pedidos/",
                headers=admin,
                json={
                    "id_solicitacao": id_solicitacao,
                    "id_fornecedor": fornecedores[0]["id_fornecedor"],
                    "numero_pedido": "PED-E2E-ANTES-EDICAO",
                    "data_pedido": date.today().isoformat(),
                    "itens": [
                        {
                            "id_item_solicitacao": id_item_solicitacao,
                            "quantidade": 3,
                        }
                    ],
                },
            ),
            201,
        )
        id_pedido = pedido["id_pedido_compra"]
        dados_edicao = {
            "id_fornecedor": fornecedores[1]["id_fornecedor"],
            "numero_pedido": "PED-E2E-DEPOIS-EDICAO",
            "data_pedido": date.today().isoformat(),
            "observacao": "Pedido corrigido antes do recebimento.",
            "itens": [
                {
                    "id_item_solicitacao": id_item_solicitacao,
                    "quantidade": 4,
                }
            ],
        }
        self.assertEqual(
            self.client.put(
                f"/pedidos/{id_pedido}",
                headers=estoque,
                json=dados_edicao,
            ).status_code,
            403,
        )

        editado = self.validar_status(
            self.client.put(
                f"/pedidos/{id_pedido}",
                headers=admin,
                json=dados_edicao,
            ),
            200,
        )
        self.assertEqual(editado["numero_pedido"], "PED-E2E-DEPOIS-EDICAO")
        self.assertEqual(
            editado["id_fornecedor"],
            fornecedores[1]["id_fornecedor"],
        )
        self.assertEqual(float(editado["itens"][0]["quantidade"]), 4)
        solicitacao_recalculada = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(solicitacao_recalculada["status"], "APROVADA")

        acima_do_saldo = {
            **dados_edicao,
            "itens": [
                {
                    "id_item_solicitacao": id_item_solicitacao,
                    "quantidade": 6,
                }
            ],
        }
        self.assertEqual(
            self.client.put(
                f"/pedidos/{id_pedido}",
                headers=admin,
                json=acima_do_saldo,
            ).status_code,
            400,
        )

        self.validar_status(
            self.client.patch(
                f"/pedidos/{id_pedido}/aguardando-recebimento",
                headers=admin,
            ),
            200,
        )
        self.assertEqual(
            self.client.put(
                f"/pedidos/{id_pedido}",
                headers=admin,
                json=dados_edicao,
            ).status_code,
            400,
        )

        historico_pedido = self.validar_status(
            self.client.get(f"/pedidos/{id_pedido}/historico", headers=admin),
            200,
        )
        self.assertEqual(
            [evento["acao"] for evento in historico_pedido],
            ["CADASTRO", "EDICAO", "ENVIO_RECEBIMENTO"],
        )
        historico_solicitacao = self.validar_status(
            self.client.get(
                f"/solicitacoes/{id_solicitacao}/historico",
                headers=funcionario,
            ),
            200,
        )
        self.assertIn(
            "PEDIDO_EDITADO",
            [evento["acao"] for evento in historico_solicitacao],
        )

    def test_usuario_pode_alterar_a_propria_senha(self):
        headers = self.autenticar("funcionario_teste")

        senha_incorreta = self.client.patch(
            "/usuarios/minha-conta/senha",
            headers=headers,
            json={
                "senha_atual": "senha-errada",
                "nova_senha": "novaSenha123",
                "confirmar_nova_senha": "novaSenha123",
            },
        )
        self.assertEqual(senha_incorreta.status_code, 400)

        confirmacao_incorreta = self.client.patch(
            "/usuarios/minha-conta/senha",
            headers=headers,
            json={
                "senha_atual": "senha123",
                "nova_senha": "novaSenha123",
                "confirmar_nova_senha": "outraSenha123",
            },
        )
        self.assertEqual(confirmacao_incorreta.status_code, 400)

        senha_repetida = self.client.patch(
            "/usuarios/minha-conta/senha",
            headers=headers,
            json={
                "senha_atual": "senha123",
                "nova_senha": "senha123",
                "confirmar_nova_senha": "senha123",
            },
        )
        self.assertEqual(senha_repetida.status_code, 400)

        alterada = self.client.patch(
            "/usuarios/minha-conta/senha",
            headers=headers,
            json={
                "senha_atual": "senha123",
                "nova_senha": "novaSenha123",
                "confirmar_nova_senha": "novaSenha123",
            },
        )
        self.assertEqual(alterada.status_code, 200, alterada.text)
        token_renovado = alterada.json()["access_token"]
        headers_renovados = {"Authorization": f"Bearer {token_renovado}"}

        sessao_anterior = self.client.get("/me", headers=headers)
        self.assertEqual(sessao_anterior.status_code, 401)

        sessao_atual = self.client.get("/me", headers=headers_renovados)
        self.assertEqual(sessao_atual.status_code, 200)

        login_antigo = self.client.post(
            "/login",
            json={"login": "funcionario_teste", "senha": "senha123"},
        )
        self.assertEqual(login_antigo.status_code, 401)

        login_novo = self.client.post(
            "/login",
            json={"login": "funcionario_teste", "senha": "novaSenha123"},
        )
        self.assertEqual(login_novo.status_code, 200)

        db = self.session_factory()
        try:
            historico = db.query(Historico).filter(
                Historico.tipo_registro == "USUARIO",
                Historico.acao == "ALTERACAO_SENHA",
            ).first()
            self.assertIsNotNone(historico)
        finally:
            db.close()

    def test_busca_global_e_resumo_respeitam_o_entregador_atual(self):
        db = self.session_factory()
        try:
            entregador = db.query(Usuario).filter(
                Usuario.login == "entregador_teste"
            ).one()
            outro_entregador = db.query(Usuario).filter(
                Usuario.login == "entregador_dois_teste"
            ).one()
            administrador = db.query(Usuario).filter(
                Usuario.login == "admin_teste"
            ).one()
            cliente_alfa = Cliente(
                nome="Rota Privada Alfa",
                endereco="Rua Alfa",
                numero="10",
                bairro="Centro",
                cidade="Itapeva",
                uf="SP",
                ativo=True,
            )
            cliente_beta = Cliente(
                nome="Rota Privada Beta",
                endereco="Rua Beta",
                numero="20",
                bairro="Centro",
                cidade="Itapeva",
                uf="SP",
                ativo=True,
            )
            db.add_all([cliente_alfa, cliente_beta])
            db.flush()
            entrega_propria = Entrega(
                id_cliente=cliente_alfa.id_cliente,
                id_usuario_cadastro=administrador.id_usuario,
                id_entregador=entregador.id_usuario,
                data_cadastro=datetime.now(),
                data_agendada=date.today(),
                status="ENTREGUE",
            )
            entrega_alheia = Entrega(
                id_cliente=cliente_beta.id_cliente,
                id_usuario_cadastro=administrador.id_usuario,
                id_entregador=outro_entregador.id_usuario,
                data_cadastro=datetime.now(),
                data_agendada=date.today(),
                status="ENTREGUE",
            )
            db.add_all([entrega_propria, entrega_alheia])
            db.flush()
            db.add(Historico(
                id_usuario=entregador.id_usuario,
                tipo_registro="ENTREGA",
                id_registro=entrega_propria.id_entrega,
                acao="ALTERACAO_STATUS",
                descricao="Status alterado de EM_ROTA para ENTREGUE.",
                data_hora=datetime.now(),
            ))
            ids = (entrega_propria.id_entrega, entrega_alheia.id_entrega)
            ids_clientes = (cliente_alfa.id_cliente, cliente_beta.id_cliente)
            db.commit()
        finally:
            db.close()

        headers_entregador = self.autenticar("entregador_teste")
        busca_entregador = self.client.get(
            "/busca-global",
            params={"q": "Rota Privada"},
            headers=headers_entregador,
        )
        self.assertEqual(busca_entregador.status_code, 200, busca_entregador.text)
        grupo_entregas = next(
            grupo for grupo in busca_entregador.json()["grupos"]
            if grupo["tipo"] == "entrega"
        )
        self.assertEqual(
            [item["id"] for item in grupo_entregas["resultados"]],
            [ids[0]],
        )

        resumo = self.client.get(
            "/entregas/minhas-resumo",
            headers=headers_entregador,
        )
        self.assertEqual(resumo.status_code, 200, resumo.text)
        self.assertGreaterEqual(resumo.json()["concluidas_hoje"], 1)

        busca_admin = self.client.get(
            "/busca-global",
            params={"q": "Rota Privada"},
            headers=self.autenticar("admin_teste"),
        )
        grupo_admin = next(
            grupo for grupo in busca_admin.json()["grupos"]
            if grupo["tipo"] == "entrega"
        )
        self.assertEqual(
            {item["id"] for item in grupo_admin["resultados"]},
            set(ids),
        )

        db = self.session_factory()
        try:
            db.query(Historico).filter(
                Historico.tipo_registro == "ENTREGA",
                Historico.id_registro.in_(ids),
            ).delete(synchronize_session=False)
            db.query(Entrega).filter(
                Entrega.id_entrega.in_(ids)
            ).delete(synchronize_session=False)
            db.query(Cliente).filter(
                Cliente.id_cliente.in_(ids_clientes)
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
