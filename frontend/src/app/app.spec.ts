import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { SistemaComponent as App } from './sistema.component';

describe('SistemaComponent', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ],
    })
      .compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should expose friendly visual labels for statuses and profiles', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.formatarStatus('AGUARDANDO_RECEBIMENTO'))
      .toBe('Aguardando recebimento');
    expect(app.formatarStatus('NAO_ENTREGUE')).toBe('Não entregue');
    expect(app.formatarPerfil('ADMINISTRADOR')).toBe('Administrador');
    expect(app.classeStatus('CRIADO')).toBe('status-informativo');
    expect(app.classePrioridade('ALTA')).toBe('status-erro');
  });

  it('should control the responsive menu without changing navigation rules', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.alternarMenuMobile();
    expect(app.menuMobileAberto).toBe(true);

    app.abrirTela('minha-conta');
    expect(app.telaAtual).toBe('minha-conta');
    expect(app.menuMobileAberto).toBe(false);
    expect(app.tituloTelaAtual()).toBe('Minha conta');
  });

  it('should calculate the visual delivery timeline without changing status', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.etapaEntregaConcluida('EM_ROTA', 'AGENDADA')).toBe(true);
    expect(app.etapaEntregaConcluida('EM_ROTA', 'ENTREGUE')).toBe(false);
    expect(app.etapaEntregaConcluida('CANCELADA', 'CADASTRADA')).toBe(false);
  });

  it('should render the dashboard title for an authenticated user', () => {
    const fixture = TestBed.createComponent(App);
    fixture.componentInstance.logado = true;
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Bem-vindo');
  });

  it('should open and cancel the inline rejection form', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.abrirRejeicaoSolicitacao(12);
    expect(app.solicitacaoEmRejeicao).toBe(12);

    app.motivoRejeicao = 'Motivo de teste';
    app.cancelarRejeicaoSolicitacao();

    expect(app.solicitacaoEmRejeicao).toBeNull();
    expect(app.motivoRejeicao).toBe('');
  });

  it('should restrict management reports to administrators', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.perfilUsuario = 'FUNCIONARIO';
    expect(app.podeAcessarRelatorios()).toBe(false);

    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeAcessarRelatorios()).toBe(true);
  });

  it('should load the role-based operational dashboard summary', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-dashboard');

    app.carregarResumoDashboard();
    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/dashboard/resumo'
    );
    expect(requisicao.request.method).toBe('GET');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-dashboard');
    requisicao.flush({
      solicitacoes_em_andamento: 3,
      pedidos_aguardando_recebimento: 2,
      entregas_em_aberto: 4,
      gerado_em: '2026-09-13T15:00:00'
    });

    expect(app.resumoDashboard.solicitacoes_em_andamento).toBe(3);
    expect(app.resumoDashboard.entregas_em_aberto).toBe(4);
    expect(app.carregandoResumoDashboard).toBe(false);
  });

  it('should restrict the general audit to administrators', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.perfilUsuario = 'ESTOQUE';
    expect(app.podeAcessarAuditoria()).toBe(false);

    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeAcessarAuditoria()).toBe(true);
  });

  it('should load and filter general audit events', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-auditoria');

    app.carregarAuditoria();
    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/auditoria/'
    );
    expect(requisicao.request.method).toBe('GET');
    requisicao.flush([
      {
        id_historico: 2,
        id_usuario: 1,
        usuario_nome: 'Administrador',
        usuario_login: 'admin',
        tipo_registro: 'ENTREGA',
        id_registro: 10,
        acao: 'ALTERACAO_STATUS',
        descricao: 'Entrega atualizada.',
        data_hora: '2026-09-13T12:00:00'
      },
      {
        id_historico: 1,
        id_usuario: 2,
        usuario_nome: 'Funcionário',
        usuario_login: 'funcionario',
        tipo_registro: 'SOLICITACAO',
        id_registro: 20,
        acao: 'CADASTRO',
        descricao: 'Solicitação cadastrada.',
        data_hora: '2026-09-13T11:00:00'
      }
    ]);

    app.filtroAuditoria.busca = 'administrador';
    app.filtroAuditoria.tipo = 'ENTREGA';

    expect(app.obterEventosAuditoriaFiltrados().map(evento => evento.id_historico))
      .toEqual([2]);

    app.filtroAuditoria.busca = '';
    app.filtroAuditoria.tipo = '';
    app.filtroAuditoria.usuario = '2';
    expect(app.obterEventosAuditoriaFiltrados().map(evento => evento.id_historico))
      .toEqual([1]);
    expect(app.carregandoAuditoria).toBe(false);
  });

  it('should list each audit user only once and in alphabetical order', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.eventosAuditoria = [
      { id_usuario: 2, usuario_nome: 'Carlos', usuario_login: 'carlos' },
      { id_usuario: 1, usuario_nome: 'Ana', usuario_login: 'ana' },
      { id_usuario: 2, usuario_nome: 'Carlos', usuario_login: 'carlos' }
    ];

    expect(app.obterUsuariosAuditoria()).toEqual([
      { id_usuario: '1', nome: 'Ana', login: 'ana' },
      { id_usuario: '2', nome: 'Carlos', login: 'carlos' }
    ]);
  });

  it('should format administrative audit types and actions', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.formatarTipoAuditoria('CLIENTE')).toBe('Cliente');
    expect(app.formatarTipoAuditoria('FORNECEDOR')).toBe('Fornecedor');
    expect(app.formatarTipoAuditoria('PRODUTO')).toBe('Produto');
    expect(app.formatarAcaoAuditoria('EDICAO')).toBe('Edição');
    expect(app.formatarAcaoAuditoria('DESATIVACAO')).toBe('Desativação');
    expect(app.formatarAcaoAuditoria('ATIVACAO')).toBe('Ativação');
  });

  it('should generate a safe CSV containing the filtered audit data', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    const csv = app.gerarConteudoAuditoriaCsv([{
      id_historico: 15,
      data_hora: '2026-09-13T12:00:00',
      tipo_registro: 'PRODUTO',
      id_registro: 7,
      acao: 'EDICAO',
      usuario_nome: 'Administrador',
      usuario_login: 'admin',
      descricao: '=FORMULA "não executar"'
    }]);

    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"Tipo de registro"');
    expect(csv).toContain('"Produto"');
    expect(csv).toContain('"Edição"');
    expect(csv).toContain('"\'=FORMULA ""não executar"""');
  });

  it('should not export an empty audit result', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.eventosAuditoria = [];
    app.exportarAuditoriaCsv();

    expect(app.erroAuditoria).toContain('Não há eventos');
    expect(app.exportandoAuditoria).toBe(false);
  });

  it('should filter audit events by an inclusive date range', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.eventosAuditoria = [
      {
        id_historico: 1,
        data_hora: '2026-09-12T23:59:59',
        tipo_registro: 'CLIENTE',
        acao: 'CADASTRO'
      },
      {
        id_historico: 2,
        data_hora: '2026-09-13T00:00:00',
        tipo_registro: 'PRODUTO',
        acao: 'EDICAO'
      },
      {
        id_historico: 3,
        data_hora: '2026-09-13T23:59:59',
        tipo_registro: 'FORNECEDOR',
        acao: 'ATIVACAO'
      }
    ];
    app.filtroAuditoria.data_inicio = '2026-09-13';
    app.filtroAuditoria.data_fim = '2026-09-13';

    expect(app.obterEventosAuditoriaFiltrados().map(evento => evento.id_historico))
      .toEqual([3, 2]);
  });

  it('should validate and clear the audit date range', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.filtroAuditoria.busca = 'produto';
    app.filtroAuditoria.data_inicio = '2026-09-14';
    app.filtroAuditoria.data_fim = '2026-09-13';

    expect(app.periodoAuditoriaInvalido()).toBe(true);
    app.exportarAuditoriaCsv();
    expect(app.erroAuditoria).toContain('data inicial');

    app.limparFiltrosAuditoria();
    expect(app.periodoAuditoriaInvalido()).toBe(false);
    expect(app.filtroAuditoria.busca).toBe('');
    expect(app.filtroAuditoria.usuario).toBe('');
  });

  it('should reject an invalid period before exporting a report', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.filtroRelatorio = {
      data_inicio: '2026-02-02',
      data_fim: '2026-02-01'
    };
    app.exportarRelatorioCsv();

    expect(app.erroRelatorio).toContain('data inicial');
    expect(app.exportandoRelatorio).toBe(false);
  });

  it('should mark all notifications as read and update the menu counter', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-notificacoes');
    app.notificacoes = [
      { id_notificacao: 1, lida: false },
      { id_notificacao: 2, lida: false },
      { id_notificacao: 3, lida: true }
    ];
    app.logado = true;
    app.atualizarTituloNotificacoes();
    expect(document.title).toBe('(2) Sistema FCL');

    app.marcarTodasNotificacoesComoLidas();

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/notificacoes/todas/lidas'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-notificacoes');
    requisicao.flush({ quantidade_atualizada: 2 });

    expect(app.contarNotificacoesNaoLidas()).toBe(0);
    expect(document.title).toBe('Sistema FCL');
    expect(app.mensagemNotificacoes).toContain('2 notificações');
    expect(app.marcandoTodasNotificacoes).toBe(false);
  });

  it('should clear the notification count from the title on logout', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    app.logado = true;
    app.notificacoes = [{ id_notificacao: 1, lida: false }];
    app.atualizarTituloNotificacoes();

    expect(document.title).toBe('(1) Sistema FCL');
    app.encerrarSessao();
    expect(document.title).toBe('Sistema FCL');
  });

  it('should alert only notifications received after the initial load', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-novas-notificacoes');
    app.logado = true;

    app.carregarNotificacoes(true);
    httpTesting.expectOne('http://127.0.0.1:8000/notificacoes/').flush([
      { id_notificacao: 1, lida: false }
    ]);
    expect(app.avisoNovaNotificacao).toBe('');

    app.carregarNotificacoes(true);
    httpTesting.expectOne('http://127.0.0.1:8000/notificacoes/').flush([
      { id_notificacao: 2, lida: false },
      { id_notificacao: 1, lida: false }
    ]);

    expect(app.avisoNovaNotificacao).toContain('uma nova notificação');
    expect(document.title).toBe('(2) Sistema FCL');

    app.dispensarAvisoNovaNotificacao();
    expect(app.avisoNovaNotificacao).toBe('');
  });

  it('should refresh notifications automatically while logged in', () => {
    vi.useFakeTimers();

    try {
      const fixture = TestBed.createComponent(App);
      const app = fixture.componentInstance;
      app.logado = true;
      const carregarNotificacoes = vi
        .spyOn(app, 'carregarNotificacoes')
        .mockImplementation(() => undefined);

      app.iniciarAtualizacaoAutomaticaNotificacoes();
      vi.advanceTimersByTime(59_999);
      expect(carregarNotificacoes).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1);
      expect(carregarNotificacoes).toHaveBeenCalledTimes(1);
      expect(carregarNotificacoes).toHaveBeenCalledWith(true);

      app.pararAtualizacaoAutomaticaNotificacoes();
      vi.advanceTimersByTime(60_000);
      expect(carregarNotificacoes).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it('should stop automatic notification refresh when logging out', () => {
    vi.useFakeTimers();

    try {
      const fixture = TestBed.createComponent(App);
      const app = fixture.componentInstance;
      app.logado = true;
      const carregarNotificacoes = vi
        .spyOn(app, 'carregarNotificacoes')
        .mockImplementation(() => undefined);

      app.iniciarAtualizacaoAutomaticaNotificacoes();
      app.encerrarSessao();
      vi.advanceTimersByTime(60_000);

      expect(carregarNotificacoes).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it('should restrict user management to administrators', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.perfilUsuario = 'ESTOQUE';
    expect(app.podeGerenciarUsuarios()).toBe(false);

    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeGerenciarUsuarios()).toBe(true);
  });

  it('should validate the password of a new user', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.formularioUsuario = {
      nome: 'Usuário Teste',
      login: 'usuario_teste',
      senha: '123',
      perfil: 'FUNCIONARIO'
    };
    app.salvarUsuario();

    expect(app.erroFormularioUsuario).toContain('pelo menos 6 caracteres');
    expect(app.salvandoUsuario).toBe(false);
  });

  it('should validate confirmation before changing the own password', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.formularioMinhaSenha = {
      senha_atual: 'senha123',
      nova_senha: 'novaSenha123',
      confirmar_nova_senha: 'outraSenha123'
    };
    app.alterarPropriaSenha();

    expect(app.erroMinhaConta).toContain('não confere');
    expect(app.salvandoMinhaSenha).toBe(false);
  });

  it('should calculate the remaining request quantity for a new order', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.pedidos = [
      {
        status: 'CRIADO',
        itens: [
          { id_item_solicitacao: 101, quantidade: 2 }
        ]
      },
      {
        status: 'CANCELADO',
        itens: [
          { id_item_solicitacao: 101, quantidade: 5 }
        ]
      }
    ];
    app.solicitacoes = [
      {
        id_solicitacao: 10,
        status: 'APROVADA',
        itens: [
          {
            id_item_solicitacao: 101,
            id_produto: 7,
            quantidade: 5
          }
        ]
      }
    ];
    app.novoPedido.id_solicitacao = 10;

    app.prepararItensNovoPedido();

    expect(app.itensNovoPedido).toEqual([
      {
        id_item_solicitacao: 101,
        id_produto: 7,
        saldo: 3,
        quantidade: 3
      }
    ]);
  });

  it('should filter and generate the detailed orders CSV', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    app.fornecedores = [
      {
        id_fornecedor: 20,
        nome_fantasia: 'Fornecedor Luz',
        razao_social: 'Fornecedor Luz Ltda',
        ativo: true
      },
      {
        id_fornecedor: 21,
        nome_fantasia: 'Fornecedor Antigo',
        razao_social: 'Fornecedor Antigo Ltda',
        ativo: false
      }
    ];
    app.produtos = [
      { id_produto: 7, nome: 'Painel LED' },
      { id_produto: 8, nome: 'Cabo flexível' }
    ];
    app.pedidos = [
      {
        id_pedido_compra: 50,
        id_solicitacao: 12,
        id_fornecedor: 20,
        numero_pedido: 'PED-0050',
        data_pedido: '2026-09-15',
        status: 'RECEBIDO_PARCIAL',
        observacao: '=NAO_EXECUTAR()',
        motivo_cancelamento: null,
        itens: [{
          id_produto: 7,
          quantidade: 5,
          quantidade_recebida: 2,
          saldo_pendente: 3
        }]
      },
      {
        id_pedido_compra: 49,
        id_solicitacao: 11,
        id_fornecedor: 21,
        numero_pedido: 'PED-0049',
        data_pedido: '2026-09-10',
        status: 'CANCELADO',
        observacao: null,
        motivo_cancelamento: 'Compra duplicada',
        itens: [{
          id_produto: 8,
          quantidade: 1,
          quantidade_recebida: 0,
          saldo_pendente: 1
        }]
      }
    ];

    expect(app.obterFornecedoresParaFiltro().map(item => item.id_fornecedor))
      .toEqual([21, 20]);

    app.filtroPedidos.busca = 'painel';
    app.filtroPedidos.fornecedor = '20';
    app.filtroPedidos.data_inicio = '2026-09-15';
    app.filtroPedidos.data_fim = '2026-09-15';
    const filtrados = app.obterPedidosFiltrados();
    expect(filtrados.map(item => item.id_pedido_compra)).toEqual([50]);

    const csv = app.gerarConteudoPedidosCsv(filtrados);
    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"PED-0050"');
    expect(csv).toContain('"Fornecedor Luz"');
    expect(csv).toContain('"Painel LED"');
    expect(csv).toContain('"2";"3"');
    expect(csv).toContain('"\'=NAO_EXECUTAR()"');

    app.filtroPedidos.data_inicio = '2026-09-16';
    expect(app.periodoPedidosInvalido()).toBe(true);
    expect(app.obterPedidosFiltrados()).toEqual([]);

    app.paginacao.pedidos.pagina = 2;
    app.limparFiltrosPedidos();
    expect(app.temFiltrosPedidos()).toBe(false);
    expect(app.paginacao.pedidos.pagina).toBe(1);
  });

  it('should send only items with quantity in a split order', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-pedido');
    app.novoPedido = {
      id_solicitacao: 10,
      id_fornecedor: 20,
      numero_pedido: 'PED-TESTE-2',
      data_pedido: app.formatarDataHoje(),
      observacao: ''
    };
    app.itensNovoPedido = [
      {
        id_item_solicitacao: 101,
        id_produto: 7,
        saldo: 3,
        quantidade: 2
      },
      {
        id_item_solicitacao: 102,
        id_produto: 8,
        saldo: 4,
        quantidade: 0
      }
    ];

    app.criarPedido();

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/pedidos/'
    );
    expect(requisicao.request.method).toBe('POST');
    expect(requisicao.request.body.itens).toEqual([
      { id_item_solicitacao: 101, quantidade: 2 }
    ]);
    requisicao.flush({ numero_pedido: 'PED-TESTE-2' });

    httpTesting.expectOne('http://127.0.0.1:8000/pedidos/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/fornecedores/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/solicitacoes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/produtos/').flush([]);

    expect(app.itensNovoPedido).toEqual([]);
    expect(app.mensagemPedidos).toContain('sucesso');
  });

  it('should edit only a created order using the balance excluding itself', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-edicao-pedido');
    app.perfilUsuario = 'ADMINISTRADOR';
    app.fornecedores = [
      { id_fornecedor: 20, nome_fantasia: 'Fornecedor Um', ativo: true },
      { id_fornecedor: 21, nome_fantasia: 'Fornecedor Dois', ativo: true }
    ];
    app.solicitacoes = [
      {
        id_solicitacao: 10,
        status: 'PEDIDO_REALIZADO',
        itens: [
          {
            id_item_solicitacao: 101,
            id_produto: 7,
            quantidade: 5
          }
        ]
      }
    ];
    const pedido = {
      id_pedido_compra: 44,
      id_solicitacao: 10,
      id_fornecedor: 20,
      numero_pedido: 'PED-ANTES',
      data_pedido: app.formatarDataHoje(),
      observacao: '',
      status: 'CRIADO',
      itens: [
        { id_item_solicitacao: 101, id_produto: 7, quantidade: 2 }
      ]
    };
    app.pedidos = [
      pedido,
      {
        id_pedido_compra: 45,
        status: 'CRIADO',
        itens: [{ id_item_solicitacao: 101, quantidade: 1 }]
      }
    ];

    expect(app.podeEditarPedido(pedido)).toBe(true);
    expect(app.podeEditarPedido({ ...pedido, status: 'AGUARDANDO_RECEBIMENTO' }))
      .toBe(false);
    app.abrirEdicaoPedido(pedido);
    expect(app.formularioEdicaoPedido.itens[0].saldo).toBe(4);
    expect(app.formularioEdicaoPedido.itens[0].quantidade).toBe(2);

    app.formularioEdicaoPedido.id_fornecedor = 21;
    app.formularioEdicaoPedido.numero_pedido = 'PED-DEPOIS';
    app.formularioEdicaoPedido.observacao = 'Fornecedor corrigido';
    app.formularioEdicaoPedido.itens[0].quantidade = 3;
    app.salvarEdicaoPedido(pedido);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/pedidos/44'
    );
    expect(requisicao.request.method).toBe('PUT');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-edicao-pedido');
    expect(requisicao.request.body).toEqual({
      id_fornecedor: 21,
      numero_pedido: 'PED-DEPOIS',
      data_pedido: app.formatarDataHoje(),
      observacao: 'Fornecedor corrigido',
      itens: [{ id_item_solicitacao: 101, quantidade: 3 }]
    });
    requisicao.flush({ ...pedido, numero_pedido: 'PED-DEPOIS' });

    httpTesting.expectOne('http://127.0.0.1:8000/pedidos/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/fornecedores/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/solicitacoes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/produtos/').flush([]);

    expect(app.pedidoEmEdicaoId).toBeNull();
    expect(app.mensagemPedidos).toContain('atualizado com sucesso');
  });

  it('should cancel an order and reload the available balances', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const pedido = {
      id_pedido_compra: 44,
      numero_pedido: 'PED-CANCELAR',
      status: 'CRIADO'
    };
    localStorage.setItem('token', 'token-cancelamento');

    app.solicitarCancelamentoPedido(pedido.id_pedido_compra);
    expect(app.pedidoEmCancelamento).toBe(44);
    app.confirmarCancelamentoPedido(pedido);
    httpTesting.expectNone(
      'http://127.0.0.1:8000/pedidos/44/cancelar'
    );
    expect(app.erroAcaoPedidos).toContain('pelo menos 3 caracteres');

    app.motivoCancelamentoPedido = 'Pedido cadastrado em duplicidade';
    app.confirmarCancelamentoPedido(pedido);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/pedidos/44/cancelar'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({
      motivo: 'Pedido cadastrado em duplicidade'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-cancelamento');
    requisicao.flush({ ...pedido, status: 'CANCELADO' });

    httpTesting.expectOne('http://127.0.0.1:8000/pedidos/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/fornecedores/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/solicitacoes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/produtos/').flush([]);

    expect(app.pedidoEmCancelamento).toBeNull();
    expect(app.motivoCancelamentoPedido).toBe('');
    expect(app.mensagemPedidos).toContain('cancelado com sucesso');
  });

  it('should reverse a receipt with a required reason', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const recebimento = {
      id_recebimento: 55,
      id_pedido_compra: 44,
      status: 'REGISTRADO'
    };
    localStorage.setItem('token', 'token-estorno');
    app.perfilUsuario = 'ADMINISTRADOR';

    app.abrirEstornoRecebimento(recebimento.id_recebimento);
    app.motivoEstornoRecebimento = 'Nota fiscal lançada incorretamente';
    app.confirmarEstornoRecebimento(recebimento);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/recebimentos/55/estornar'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({
      motivo: 'Nota fiscal lançada incorretamente'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-estorno');
    requisicao.flush({ ...recebimento, status: 'ESTORNADO' });

    httpTesting.expectOne('http://127.0.0.1:8000/pedidos/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/recebimentos/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/fornecedores/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/produtos/').flush([]);

    expect(app.recebimentoEmEstorno).toBeNull();
    expect(app.mensagemRecebimentos).toContain('estornado com sucesso');
  });

  it('should filter and generate the receipt history CSV', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    app.pedidos = [
      { id_pedido_compra: 44, numero_pedido: 'PED-0044' },
      { id_pedido_compra: 45, numero_pedido: 'PED-0045' }
    ];
    app.produtos = [
      { id_produto: 2, nome: 'Lâmpada LED' },
      { id_produto: 3, nome: 'Cabo flexível' }
    ];
    app.recebimentos = [
      {
        id_recebimento: 10,
        id_pedido_compra: 44,
        data_recebimento: '2026-09-15T10:00:00',
        numero_nota_fiscal: 'NF-100',
        observacao: '=NAO_EXECUTAR()',
        status: 'REGISTRADO',
        motivo_estorno: null,
        itens: [
          { id_produto: 2, quantidade_recebida: 3 },
          { id_produto: 3, quantidade_recebida: 5 }
        ]
      },
      {
        id_recebimento: 9,
        id_pedido_compra: 45,
        data_recebimento: '2026-09-14T09:00:00',
        numero_nota_fiscal: 'NF-099',
        observacao: null,
        status: 'ESTORNADO',
        motivo_estorno: 'Documento incorreto',
        itens: [{ id_produto: 3, quantidade_recebida: 1 }]
      }
    ];

    app.filtroHistoricoRecebimentos.busca = 'lâmpada';
    app.filtroHistoricoRecebimentos.status = 'REGISTRADO';
    app.filtroHistoricoRecebimentos.data_inicio = '2026-09-15';
    app.filtroHistoricoRecebimentos.data_fim = '2026-09-15';
    const filtrados = app.obterHistoricoRecebimentosFiltrado();
    expect(filtrados.map(item => item.id_recebimento)).toEqual([10]);

    const csv = app.gerarConteudoHistoricoRecebimentosCsv(filtrados);
    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"PED-0044"');
    expect(csv).toContain('"NF-100"');
    expect(csv).toContain('"Lâmpada LED"');
    expect(csv).toContain('"Cabo flexível"');
    expect(csv).toContain('"\'=NAO_EXECUTAR()"');

    app.filtroHistoricoRecebimentos.data_inicio = '2026-09-16';
    expect(app.periodoHistoricoRecebimentosInvalido()).toBe(true);
    expect(app.obterHistoricoRecebimentosFiltrado()).toEqual([]);

    app.paginacao.historico_recebimentos.pagina = 2;
    app.limparFiltrosHistoricoRecebimentos();
    expect(app.temFiltrosHistoricoRecebimentos()).toBe(false);
    expect(app.paginacao.historico_recebimentos.pagina).toBe(1);
  });

  it('should change the own password through the authenticated API', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-teste');

    app.formularioMinhaSenha = {
      senha_atual: 'senha123',
      nova_senha: 'novaSenha123',
      confirmar_nova_senha: 'novaSenha123'
    };
    app.alterarPropriaSenha();

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/usuarios/minha-conta/senha'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-teste');
    requisicao.flush({
      access_token: 'token-renovado',
      token_type: 'bearer',
      usuario: 'Funcionário Teste',
      perfil: 'FUNCIONARIO'
    });

    expect(app.mensagemMinhaConta).toContain('sucesso');
    expect(app.formularioMinhaSenha.senha_atual).toBe('');
    expect(app.salvandoMinhaSenha).toBe(false);
    expect(localStorage.getItem('token')).toBe('token-renovado');
  });

  it('should cancel the own request with a required reason', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const solicitacao = {
      id_solicitacao: 31,
      id_usuario_solicitante: 7,
      status: 'SOLICITADA'
    };
    localStorage.setItem('token', 'token-cancelar-solicitacao');
    app.perfilUsuario = 'FUNCIONARIO';
    app.idUsuarioAtual = 7;

    expect(app.podeCancelarSolicitacao(solicitacao)).toBe(true);
    app.abrirCancelamentoSolicitacao(solicitacao.id_solicitacao);
    app.motivoCancelamentoSolicitacao = 'Solicitação criada em duplicidade';
    app.confirmarCancelamentoSolicitacao(solicitacao);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/solicitacoes/31/cancelar'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({
      motivo: 'Solicitação criada em duplicidade'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-cancelar-solicitacao');
    requisicao.flush({ ...solicitacao, status: 'CANCELADA' });

    httpTesting.expectOne('http://127.0.0.1:8000/solicitacoes/').flush([]);

    expect(app.solicitacaoEmCancelamento).toBeNull();
    expect(app.mensagemSolicitacoes).toContain('cancelada com sucesso');

    app.idUsuarioAtual = 8;
    expect(app.podeCancelarSolicitacao(solicitacao)).toBe(false);
    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeCancelarSolicitacao({ ...solicitacao, status: 'APROVADA' }))
      .toBe(true);
    expect(app.podeCancelarSolicitacao({ ...solicitacao, status: 'PEDIDO_REALIZADO' }))
      .toBe(false);
  });

  it('should edit the own request while it is still requested', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const solicitacao = {
      id_solicitacao: 32,
      id_usuario_solicitante: 7,
      status: 'SOLICITADA',
      prioridade: 'BAIXA',
      motivo: 'Comprar material',
      observacao: '',
      itens: [{ id_produto: 3, quantidade: 1 }]
    };
    localStorage.setItem('token', 'token-editar-solicitacao');
    app.perfilUsuario = 'FUNCIONARIO';
    app.idUsuarioAtual = 7;

    expect(app.podeEditarSolicitacao(solicitacao)).toBe(true);
    app.abrirEdicaoSolicitacao(solicitacao);
    app.formularioEdicaoSolicitacao.prioridade = 'ALTA';
    app.formularioEdicaoSolicitacao.motivo = 'Comprar material corrigido';
    app.formularioEdicaoSolicitacao.itens[0].quantidade = 4;
    app.salvarEdicaoSolicitacao(solicitacao);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/solicitacoes/32'
    );
    expect(requisicao.request.method).toBe('PUT');
    expect(requisicao.request.body).toEqual({
      prioridade: 'ALTA',
      motivo: 'Comprar material corrigido',
      observacao: null,
      itens: [{ id_produto: 3, quantidade: 4 }]
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-editar-solicitacao');
    requisicao.flush({
      ...solicitacao,
      prioridade: 'ALTA',
      motivo: 'Comprar material corrigido'
    });

    httpTesting.expectOne('http://127.0.0.1:8000/solicitacoes/').flush([]);

    expect(app.solicitacaoEmEdicaoId).toBeNull();
    expect(app.mensagemSolicitacoes).toContain('atualizada com sucesso');

    app.idUsuarioAtual = 8;
    expect(app.podeEditarSolicitacao(solicitacao)).toBe(false);
    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeEditarSolicitacao(solicitacao)).toBe(true);
    expect(app.podeEditarSolicitacao({ ...solicitacao, status: 'EM_ANALISE' }))
      .toBe(false);
  });

  it('should load the order history on demand', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-historico-pedido');

    app.alternarHistoricoPedido(44);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/pedidos/44/historico'
    );
    expect(requisicao.request.method).toBe('GET');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-historico-pedido');
    requisicao.flush([
      {
        id_historico: 1,
        id_usuario: 1,
        tipo_registro: 'PEDIDO',
        id_registro: 44,
        acao: 'CADASTRO',
        descricao: 'Pedido criado.',
        data_hora: '2026-09-15T10:00:00'
      },
      {
        id_historico: 2,
        id_usuario: 2,
        tipo_registro: 'PEDIDO',
        id_registro: 44,
        acao: 'RECEBIMENTO_PARCIAL',
        descricao: 'Recebimento parcial registrado.',
        data_hora: '2026-09-15T11:00:00'
      }
    ]);

    expect(app.historicoPedido.length).toBe(2);
    expect(app.carregandoHistoricoPedido).toBe(false);
    expect(app.formatarAcaoHistoricoPedido('RECEBIMENTO_PARCIAL'))
      .toBe('Recebimento parcial');

    app.alternarHistoricoPedido(44);
    expect(app.pedidoHistoricoSelecionado).toBeNull();
    expect(app.historicoPedido).toEqual([]);
  });

  it('should load the request history on demand', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    localStorage.setItem('token', 'token-historico-solicitacao');

    app.alternarHistoricoSolicitacao(33);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/solicitacoes/33/historico'
    );
    expect(requisicao.request.method).toBe('GET');
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-historico-solicitacao');
    requisicao.flush([
      {
        id_historico: 1,
        id_usuario: 7,
        tipo_registro: 'SOLICITACAO',
        id_registro: 33,
        acao: 'CADASTRO',
        descricao: 'Solicitação cadastrada.',
        data_hora: '2026-09-14T10:00:00'
      },
      {
        id_historico: 2,
        id_usuario: 1,
        tipo_registro: 'SOLICITACAO',
        id_registro: 33,
        acao: 'APROVACAO',
        descricao: 'Solicitação aprovada.',
        data_hora: '2026-09-14T11:00:00'
      }
    ]);

    expect(app.historicoSolicitacao.length).toBe(2);
    expect(app.carregandoHistoricoSolicitacao).toBe(false);
    expect(app.formatarAcaoHistoricoSolicitacao('APROVACAO'))
      .toBe('Solicitação aprovada');

    app.alternarHistoricoSolicitacao(33);
    expect(app.solicitacaoHistoricoSelecionada).toBeNull();
    expect(app.historicoSolicitacao).toEqual([]);
  });

  it('should load the delivery history on demand', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.entregaHistoricoSelecionada = 15;
    app.carregarHistoricoEntrega(15);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/entregas/15/historico'
    );
    expect(requisicao.request.method).toBe('GET');

    requisicao.flush([
      {
        id_historico: 1,
        id_usuario: 2,
        tipo_registro: 'ENTREGA',
        id_registro: 15,
        acao: 'CADASTRO',
        descricao: 'Entrega cadastrada.',
        data_hora: '2026-09-12T10:00:00'
      }
    ]);

    expect(app.historicoEntrega.length).toBe(1);
    expect(app.carregandoHistoricoEntrega).toBe(false);
  });

  it('should classify, filter and order deliveries by deadline', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const formatarData = (data: Date) => {
      const ano = data.getFullYear();
      const mes = String(data.getMonth() + 1).padStart(2, '0');
      const dia = String(data.getDate()).padStart(2, '0');
      return `${ano}-${mes}-${dia}`;
    };
    const criarData = (dias: number) => {
      const data = new Date();
      data.setDate(data.getDate() + dias);
      return formatarData(data);
    };
    const ontem = criarData(-1);
    const hoje = criarData(0);
    const amanha = criarData(1);

    app.entregas = [
      { id_entrega: 1, status: 'AGENDADA', data_agendada: ontem },
      { id_entrega: 2, status: 'EM_ROTA', data_agendada: hoje },
      { id_entrega: 3, status: 'AGENDADA', data_agendada: amanha },
      { id_entrega: 4, status: 'CADASTRADA', data_agendada: null },
      { id_entrega: 5, status: 'ENTREGUE', data_agendada: ontem }
    ];

    expect(app.obterSituacaoPrazoEntrega(app.entregas[0])).toBe('ATRASADA');
    expect(app.obterSituacaoPrazoEntrega(app.entregas[1])).toBe('HOJE');
    expect(app.obterSituacaoPrazoEntrega(app.entregas[2])).toBe('FUTURA');
    expect(app.obterSituacaoPrazoEntrega(app.entregas[3])).toBe('SEM_DATA');
    expect(app.obterSituacaoPrazoEntrega(app.entregas[4])).toBe('ENCERRADA');
    expect(app.contarEntregasPorPrazo('ATRASADA')).toBe(1);

    app.filtroEntregas.prazo = 'ATRASADA';
    expect(app.obterEntregasFiltradas().map(item => item.id_entrega)).toEqual([1]);

    app.filtroEntregas.prazo = '';
    app.filtroEntregas.ordem = 'data_proxima';
    expect(app.obterEntregasFiltradas().map(item => item.id_entrega))
      .toEqual([5, 1, 2, 3, 4]);
  });

  it('should generate the filtered delivery CSV with destination data', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const ontem = new Date();
    ontem.setDate(ontem.getDate() - 1);
    const dataAgendada = [
      ontem.getFullYear(),
      String(ontem.getMonth() + 1).padStart(2, '0'),
      String(ontem.getDate()).padStart(2, '0')
    ].join('-');
    app.clientes = [{
      id_cliente: 7,
      nome: 'Cliente Rota',
      telefone: '11988887777',
      endereco: 'Rua das Lâmpadas',
      numero: '120',
      bairro: 'Centro',
      cidade: 'São Paulo',
      uf: 'SP'
    }];
    app.usuariosResumo = [{
      id_usuario: 8,
      nome: 'Entregador Rota'
    }];
    const entrega = {
      id_entrega: 31,
      id_cliente: 7,
      id_entregador: 8,
      data_agendada: dataAgendada,
      status: 'AGENDADA',
      observacao: '=NAO_EXECUTAR()'
    };

    const csv = app.gerarConteudoEntregasCsv([entrega]);

    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"Endereço"');
    expect(csv).toContain('"Cliente Rota"');
    expect(csv).toContain('"Rua das Lâmpadas, 120 - Centro - São Paulo/SP"');
    expect(csv).toContain('"Entregador Rota"');
    expect(csv).toContain('"Atrasada"');
    expect(csv).toContain('"\'=NAO_EXECUTAR()"');
  });

  it('should provide customer phone and map shortcuts for a delivery', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    app.clientes = [{
      id_cliente: 7,
      telefone: '11988887777',
      endereco: 'Rua das Lâmpadas',
      numero: '120',
      bairro: 'Centro',
      cidade: 'São Paulo',
      uf: 'SP'
    }];

    expect(app.obterTelefoneCliente(7)).toBe('(11) 98888-7777');
    expect(app.obterLinkTelefoneCliente(7)).toBe('tel:11988887777');

    const linkMapa = app.obterLinkMapaCliente(7);
    expect(linkMapa).toContain('https://www.google.com/maps/search/?api=1&query=');
    expect(decodeURIComponent(linkMapa!.split('query=')[1]))
      .toBe('Rua das Lâmpadas, 120 - Centro - São Paulo/SP');

    expect(app.obterTelefoneCliente(999)).toBeNull();
    expect(app.obterLinkTelefoneCliente(999)).toBeNull();
    expect(app.obterLinkMapaCliente(999)).toBeNull();
  });

  it('should plan a route by driver and scheduled date', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const hoje = app.formatarDataHoje();
    app.usuariosResumo = [
      { id_usuario: 9, nome: 'Zeca', perfil: 'ENTREGADOR', ativo: false },
      { id_usuario: 8, nome: 'Ana', perfil: 'ENTREGADOR', ativo: true },
      { id_usuario: 7, nome: 'Carlos', perfil: 'FUNCIONARIO', ativo: true }
    ];
    app.entregas = [
      { id_entrega: 1, id_entregador: 8, data_agendada: hoje, status: 'AGENDADA' },
      { id_entrega: 2, id_entregador: 8, data_agendada: '2099-01-01', status: 'AGENDADA' },
      { id_entrega: 3, id_entregador: 9, data_agendada: hoje, status: 'EM_ROTA' },
      { id_entrega: 4, id_entregador: null, data_agendada: hoje, status: 'CADASTRADA' }
    ];

    expect(app.obterEntregadoresParaFiltro().map(item => item.nome))
      .toEqual(['Ana', 'Zeca']);

    app.filtroEntregas.entregador = '8';
    app.filtroEntregas.data_agendada = hoje;
    expect(app.obterEntregasFiltradas().map(item => item.id_entrega)).toEqual([1]);

    app.filtroEntregas.entregador = 'SEM_ENTREGADOR';
    expect(app.obterEntregasFiltradas().map(item => item.id_entrega)).toEqual([4]);
    expect(app.temFiltrosEntrega()).toBe(true);

    app.paginacao.entregas.pagina = 3;
    app.limparFiltrosEntrega();
    expect(app.filtroEntregas).toEqual({
      busca: '',
      status: '',
      prazo: '',
      entregador: '',
      data_agendada: '',
      ordem: 'recentes'
    });
    expect(app.paginacao.entregas.pagina).toBe(1);
  });

  it('should edit a delivery before it enters the route', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const dataAgendada = app.formatarDataHoje();
    const entrega = {
      id_entrega: 24,
      id_cliente: 1,
      id_entregador: 8,
      data_agendada: null,
      observacao: 'Antes',
      status: 'CADASTRADA'
    };
    localStorage.setItem('token', 'token-editar-entrega');
    app.perfilUsuario = 'FUNCIONARIO';
    app.clientes = [
      { id_cliente: 1, nome: 'Cliente 1', ativo: true },
      { id_cliente: 2, nome: 'Cliente 2', ativo: true }
    ];
    app.usuariosResumo = [
      { id_usuario: 8, nome: 'Entregador 1', perfil: 'ENTREGADOR', ativo: true },
      { id_usuario: 9, nome: 'Entregador 2', perfil: 'ENTREGADOR', ativo: true }
    ];

    expect(app.podeEditarEntrega(entrega)).toBe(true);
    expect(app.podeEditarEntrega({ ...entrega, status: 'EM_ROTA' })).toBe(false);
    app.abrirEdicaoEntrega(entrega);
    app.formularioEdicaoEntrega = {
      id_cliente: 2,
      id_entregador: 9,
      data_agendada: dataAgendada,
      observacao: 'Corrigida'
    };
    app.salvarEdicaoEntrega(entrega);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/entregas/24'
    );
    expect(requisicao.request.method).toBe('PUT');
    expect(requisicao.request.body).toEqual({
      id_cliente: 2,
      id_entregador: 9,
      data_agendada: dataAgendada,
      observacao: 'Corrigida'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-editar-entrega');
    requisicao.flush({
      ...entrega,
      id_cliente: 2,
      id_entregador: 9,
      data_agendada: dataAgendada,
      observacao: 'Corrigida',
      status: 'AGENDADA'
    });

    httpTesting.expectOne('http://127.0.0.1:8000/entregas/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/clientes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/usuarios/resumo/').flush([]);

    expect(app.entregaEmEdicaoId).toBeNull();
    expect(app.mensagemEntregas).toContain('atualizada com sucesso');
  });

  it('should cancel a delivery with a required reason', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const entrega = {
      id_entrega: 21,
      status: 'AGENDADA'
    };
    localStorage.setItem('token', 'token-cancelar-entrega');
    app.perfilUsuario = 'ADMINISTRADOR';

    expect(app.podeCancelarEntrega(entrega)).toBe(true);
    app.abrirCancelamentoEntrega(entrega.id_entrega);
    app.motivoCancelamentoEntrega = 'Entrega cadastrada em duplicidade';
    app.confirmarCancelamentoEntrega(entrega);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/entregas/21/cancelar'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({
      motivo: 'Entrega cadastrada em duplicidade'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-cancelar-entrega');
    requisicao.flush({ ...entrega, status: 'CANCELADA' });

    httpTesting.expectOne('http://127.0.0.1:8000/entregas/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/clientes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/usuarios/resumo/').flush([]);

    expect(app.entregaEmCancelamento).toBeNull();
    expect(app.mensagemEntregas).toContain('cancelada com sucesso');

    app.perfilUsuario = 'FUNCIONARIO';
    expect(app.podeCancelarEntrega(entrega)).toBe(false);
    app.perfilUsuario = 'ADMINISTRADOR';
    expect(app.podeCancelarEntrega({ ...entrega, status: 'EM_ROTA' })).toBe(false);
  });

  it('should schedule a delivery with the selected date', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const entrega = {
      id_entrega: 22,
      status: 'CADASTRADA',
      data_agendada: null
    };
    const dataAgendada = app.formatarDataHoje();
    localStorage.setItem('token', 'token-agendamento');
    app.perfilUsuario = 'FUNCIONARIO';
    app.datasAgendamentoSelecionadas[entrega.id_entrega] = dataAgendada;

    expect(app.podeAlterarAgendamentoEntrega(entrega)).toBe(true);
    app.salvarAgendamentoEntrega(entrega);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/entregas/22/agendamento'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({ data_agendada: dataAgendada });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-agendamento');
    requisicao.flush({
      ...entrega,
      status: 'AGENDADA',
      data_agendada: dataAgendada
    });

    httpTesting.expectOne('http://127.0.0.1:8000/entregas/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/clientes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/usuarios/resumo/').flush([]);

    expect(app.mensagemEntregas).toContain('agendada');
    expect(app.entregaEmAtualizacao).toBeNull();
    expect(app.podeAlterarAgendamentoEntrega({ ...entrega, status: 'EM_ROTA' }))
      .toBe(false);
  });

  it('should record a failed delivery attempt with a reason', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const entrega = {
      id_entrega: 23,
      id_entregador: 8,
      status: 'EM_ROTA'
    };
    localStorage.setItem('token', 'token-nao-entrega');
    app.perfilUsuario = 'ENTREGADOR';
    app.idUsuarioAtual = 8;

    expect(app.podeRegistrarNaoEntrega(entrega)).toBe(true);
    app.abrirRegistroNaoEntrega(entrega.id_entrega);
    app.motivoNaoEntrega = 'Cliente ausente no endereço';
    app.confirmarNaoEntrega(entrega);

    const requisicao = httpTesting.expectOne(
      'http://127.0.0.1:8000/entregas/23/nao-entregue'
    );
    expect(requisicao.request.method).toBe('PATCH');
    expect(requisicao.request.body).toEqual({
      motivo: 'Cliente ausente no endereço'
    });
    expect(requisicao.request.headers.get('Authorization'))
      .toBe('Bearer token-nao-entrega');
    requisicao.flush({ ...entrega, status: 'NAO_ENTREGUE' });

    httpTesting.expectOne('http://127.0.0.1:8000/entregas/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/clientes/').flush([]);
    httpTesting.expectOne('http://127.0.0.1:8000/usuarios/resumo/').flush([]);

    expect(app.entregaEmNaoEntrega).toBeNull();
    expect(app.mensagemEntregas).toContain('registrada');

    app.idUsuarioAtual = 9;
    expect(app.podeRegistrarNaoEntrega(entrega)).toBe(false);
    expect(app.podeAlterarAgendamentoEntrega({ ...entrega, status: 'NAO_ENTREGUE' }))
      .toBe(false);
    app.perfilUsuario = 'FUNCIONARIO';
    expect(app.podeAlterarAgendamentoEntrega({ ...entrega, status: 'NAO_ENTREGUE' }))
      .toBe(true);
  });

  it('should reject an unsupported delivery attachment', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const arquivo = new File(['conteudo'], 'arquivo.exe');

    expect(app.validarArquivoEntrega(arquivo)).toContain('Formato inválido');
  });

  it('should allow only the assigned driver or an administrator to attach proof', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const entrega = {
      id_entregador: 8,
      status: 'EM_ROTA'
    };

    app.idUsuarioAtual = 7;
    app.perfilUsuario = 'ENTREGADOR';
    expect(app.podeAnexarComprovante(entrega)).toBe(false);

    app.idUsuarioAtual = 8;
    expect(app.podeAnexarComprovante(entrega)).toBe(true);

    app.perfilUsuario = 'ADMINISTRADOR';
    app.idUsuarioAtual = 1;
    expect(app.podeAnexarComprovante(entrega)).toBe(true);
  });

  it('should search without accents and filter clients by status', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.clientes = [
      {
        id_cliente: 1,
        nome: 'Árvore Comercial',
        cpf_cnpj: '111',
        telefone: '11999999999',
        cidade: 'São Paulo',
        uf: 'SP',
        ativo: true
      },
      {
        id_cliente: 2,
        nome: 'Beta Serviços',
        cpf_cnpj: '222',
        telefone: '11888888888',
        cidade: 'Campinas',
        uf: 'SP',
        ativo: false
      }
    ];
    app.filtroClientes = {
      busca: 'arvore',
      status: 'ATIVO',
      ordem: 'az'
    };

    expect(app.obterClientesFiltrados().map(cliente => cliente.id_cliente))
      .toEqual([1]);
  });

  it('should filter users by profile and order them by name', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.usuarios = [
      { id_usuario: 1, nome: 'Zeca', login: 'zeca', perfil: 'ENTREGADOR', ativo: true },
      { id_usuario: 2, nome: 'Ana', login: 'ana', perfil: 'ENTREGADOR', ativo: true },
      { id_usuario: 3, nome: 'Bruno', login: 'bruno', perfil: 'ESTOQUE', ativo: true }
    ];
    app.filtroUsuarios = {
      busca: '',
      status: 'ATIVO',
      perfil: 'ENTREGADOR',
      ordem: 'az'
    };

    expect(app.obterUsuariosFiltrados().map(usuario => usuario.nome))
      .toEqual(['Ana', 'Zeca']);
  });

  it('should paginate a filtered list using the selected page size', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const registros = Array.from({ length: 12 }, (_, indice) => indice + 1);

    app.paginacao.produtos.porPagina = 5;
    app.alterarPagina('produtos', 2, registros.length);

    expect(app.paginarLista(registros, 'produtos')).toEqual([6, 7, 8, 9, 10]);
    expect(app.obterTotalPaginas(registros.length, 'produtos')).toBe(3);
  });

  it('should automatically adjust an out-of-range page after filtering', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    app.paginacao.clientes.pagina = 4;
    app.paginacao.clientes.porPagina = 5;

    expect(app.obterPaginaAtual(3, 'clientes')).toBe(1);
    expect(app.paginarLista(['A', 'B', 'C'], 'clientes')).toEqual(['A', 'B', 'C']);
  });

  it('should format Brazilian documents and phone numbers', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.formatarCpfCnpj('52998224725')).toBe('529.982.247-25');
    expect(app.formatarCnpj('11222333000181')).toBe('11.222.333/0001-81');
    expect(app.formatarTelefone('11987654321')).toBe('(11) 98765-4321');
  });

  it('should expose database-compatible length limits in maintenance forms', () => {
    const renderForm = (tela: any): HTMLElement => {
      const fixture = TestBed.createComponent(App);
      fixture.componentInstance.logado = true;
      fixture.componentInstance.telaAtual = tela;
      fixture.detectChanges();
      return fixture.nativeElement as HTMLElement;
    };

    const usuario = renderForm('formulario-usuario');
    expect((usuario.querySelector('#nome-usuario') as HTMLInputElement).maxLength).toBe(100);
    expect((usuario.querySelector('#login-usuario') as HTMLInputElement).maxLength).toBe(50);
    expect((usuario.querySelector('#senha-usuario') as HTMLInputElement).maxLength).toBe(128);

    const cliente = renderForm('formulario-cliente');
    expect((cliente.querySelector('#nome-cliente') as HTMLInputElement).maxLength).toBe(120);
    expect((cliente.querySelector('#numero-endereco-cliente') as HTMLInputElement).maxLength)
      .toBe(20);
    expect((cliente.querySelector('#bairro-cliente') as HTMLInputElement).maxLength).toBe(60);

    const fornecedor = renderForm('formulario-fornecedor');
    expect((fornecedor.querySelector('#razao-social-fornecedor') as HTMLInputElement).maxLength)
      .toBe(120);
    expect((fornecedor.querySelector('#email-fornecedor') as HTMLInputElement).maxLength)
      .toBe(100);

    const produto = renderForm('formulario-produto');
    expect((produto.querySelector('#codigo-produto') as HTMLInputElement).maxLength).toBe(30);
    expect((produto.querySelector('#unidade-produto') as HTMLInputElement).maxLength).toBe(20);
  });

  it('should validate CPF, CNPJ and ISO dates', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.validarCpf('529.982.247-25')).toBe(true);
    expect(app.validarCpf('123.456.789-01')).toBe(false);
    expect(app.validarCnpj('11.222.333/0001-81')).toBe(true);
    expect(app.validarCnpj('12.345.678/0001-99')).toBe(false);
    expect(app.dataIsoValida('2026-02-28')).toBe(true);
    expect(app.dataIsoValida('2026-02-30')).toBe(false);
  });

  it('should build API URLs from the active environment', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;

    expect(app.urlApi('/clientes/')).toBe('http://127.0.0.1:8000/clientes/');
    expect(app.urlApi('pedidos/')).toBe('http://127.0.0.1:8000/pedidos/');
  });
});
