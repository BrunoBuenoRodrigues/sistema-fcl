import { Component, ChangeDetectorRef, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Router } from '@angular/router';
import { Subject, Subscription, catchError, debounceTime, distinctUntilChanged, finalize, forkJoin, of, switchMap } from 'rxjs';
import { environment } from '../environments/environment';

type ChavePaginacao =
  | 'solicitacoes'
  | 'pedidos'
  | 'recebimentos'
  | 'historico_recebimentos'
  | 'entregas'
  | 'clientes'
  | 'usuarios'
  | 'fornecedores'
  | 'produtos'
  | 'notificacoes'
  | 'auditoria';

type ModuloOperacional = 'solicitacoes' | 'pedidos' | 'entregas';
type TipoPainelDetalhes = 'solicitacao' | 'pedido' | 'entrega';
type FormularioAuxiliarEntrega = 'agendamento' | 'entregador' | 'comprovante';
type TipoRascunho = 'solicitacao' | 'pedido' | 'entrega';
type AbaMinhasEntregas = 'hoje' | 'proximas' | 'andamento' | 'concluidas';

@Component({
  selector: 'app-sistema',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html'
})
export class SistemaComponent implements OnInit, OnDestroy {

  private readonly apiUrl = environment.apiUrl.replace(/\/+$/, '');
  private readonly tituloBase = 'Sistema FCL';
  private readonly intervaloAtualizacaoNotificacoesMs = 60_000;
  private atualizacaoNotificacoesId: ReturnType<typeof setInterval> | null = null;
  private atualizandoNotificacoesEmSegundoPlano = false;
  private notificacoesInicializadas = false;
  private readonly buscaGlobal$ = new Subject<string>();
  private buscaGlobalSubscription: Subscription | null = null;
  private restaurandoNavegacao = false;
  private readonly versaoEstadoNavegacao = 1;
  private readonly versaoRascunho = 1;
  private readonly validadeRascunhoMs = 24 * 60 * 60 * 1000;
  private resultadoBuscaPendente: { tipo: string; id: number } | null = null;
  readonly etapasEntregaVisual = [
    { status: 'CADASTRADA', rotulo: 'Cadastrada' },
    { status: 'AGENDADA', rotulo: 'Agendada' },
    { status: 'EM_SEPARACAO', rotulo: 'Separação' },
    { status: 'PRONTA_PARA_ENTREGA', rotulo: 'Pronta' },
    { status: 'EM_ROTA', rotulo: 'Em rota' },
    { status: 'ENTREGUE', rotulo: 'Entregue' }
  ];
  readonly etapasSolicitacoes = [
    { status: '', rotulo: 'Todas' },
    { status: 'SOLICITADA', rotulo: 'Solicitadas' },
    { status: 'EM_ANALISE', rotulo: 'Em análise' },
    { status: 'APROVADA', rotulo: 'Aprovadas' },
    { status: 'PEDIDO_REALIZADO', rotulo: 'Pedido realizado' },
    { status: 'REJEITADA', rotulo: 'Rejeitadas' },
    { status: 'CANCELADA', rotulo: 'Canceladas' }
  ];
  readonly etapasPedidos = [
    { status: '', rotulo: 'Todos' },
    { status: 'CRIADO', rotulo: 'Criados' },
    { status: 'AGUARDANDO_RECEBIMENTO', rotulo: 'Aguardando recebimento' },
    { status: 'RECEBIDO_PARCIAL', rotulo: 'Recebidos parcialmente' },
    { status: 'RECEBIDO_TOTAL', rotulo: 'Recebidos totalmente' },
    { status: 'CANCELADO', rotulo: 'Cancelados' }
  ];
  readonly etapasEntregas = [
    { status: '', rotulo: 'Todas' },
    { status: 'CADASTRADA', rotulo: 'Cadastradas' },
    { status: 'AGENDADA', rotulo: 'Agendadas' },
    { status: 'EM_SEPARACAO', rotulo: 'Em separação' },
    { status: 'PRONTA_PARA_ENTREGA', rotulo: 'Prontas para entrega' },
    { status: 'EM_ROTA', rotulo: 'Em rota' },
    { status: 'ENTREGUE', rotulo: 'Entregues' },
    { status: 'NAO_ENTREGUE', rotulo: 'Não entregues' },
    { status: 'CANCELADA', rotulo: 'Canceladas' }
  ];

  login = '';
  logado = false;
  menuMobileAberto = false;
  perfilUsuario = '';
  idUsuarioAtual: number | null = null;
  nomeUsuarioAtual = '';
  telaAtual = 'dashboard';
  consultaBuscaGlobal = '';
  buscaGlobalAberta = false;
  buscandoGlobalmente = false;
  erroBuscaGlobal = '';
  gruposBuscaGlobal: any[] = [];
  abaMinhasEntregas: AbaMinhasEntregas = 'hoje';
  resumoMinhasEntregas = {
    hoje: 0,
    em_rota: 0,
    pendentes: 0,
    concluidas_hoje: 0
  };
  rascunhoDisponivel: { tipo: TipoRascunho; dados: any } | null = null;
  salvandoMinhaSenha = false;
  erroMinhaConta = '';
  mensagemMinhaConta = '';
  formularioMinhaSenha = {
    senha_atual: '',
    nova_senha: '',
    confirmar_nova_senha: ''
  };
  solicitacoes: any[] = [];
  carregandoSolicitacoes = false;
  solicitacaoEmAtualizacao: number | null = null;
  solicitacaoEmRejeicao: number | null = null;
  motivoRejeicao = '';
  solicitacaoEmCancelamento: number | null = null;
  motivoCancelamentoSolicitacao = '';
  solicitacaoEmEdicaoId: number | null = null;
  salvandoEdicaoSolicitacao = false;
  erroEdicaoSolicitacao = '';
  formularioEdicaoSolicitacao = {
    prioridade: 'MEDIA',
    motivo: '',
    observacao: '',
    itens: [] as any[]
  };
  solicitacaoHistoricoSelecionada: number | null = null;
  historicoSolicitacao: any[] = [];
  carregandoHistoricoSolicitacao = false;
  erroHistoricoSolicitacao = '';
  erroSolicitacoes = '';
  erroNovaSolicitacao = '';
  mensagemSolicitacoes = '';
  criandoSolicitacao = false;
  filtroSolicitacoes = { busca: '', status: '', ordem: 'recentes' };
  produtos: any[] = [];
  pedidos: any[] = [];
  fornecedores: any[] = [];
  carregandoPedidos = false;
  erroPedidos = '';
  mensagemPedidos = '';
  exportandoPedidos = false;
  erroAcaoPedidos = '';
  pedidoEmAtualizacao: number | null = null;
  pedidoEmCancelamento: number | null = null;
  motivoCancelamentoPedido = '';
  pedidoEmEdicaoId: number | null = null;
  salvandoEdicaoPedido = false;
  erroEdicaoPedido = '';
  formularioEdicaoPedido = {
    id_fornecedor: null as number | null,
    numero_pedido: '',
    data_pedido: '',
    observacao: '',
    itens: [] as any[]
  };
  pedidoHistoricoSelecionado: number | null = null;
  historicoPedido: any[] = [];
  carregandoHistoricoPedido = false;
  erroHistoricoPedido = '';
  criandoPedido = false;
  erroNovoPedido = '';
  itensNovoPedido: any[] = [];
  filtroPedidos = {
    busca: '',
    status: '',
    fornecedor: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  carregandoRecebimentos = false;
  carregandoItensRecebimento = false;
  registrandoRecebimento = false;
  erroRecebimentos = '';
  mensagemRecebimentos = '';
  avisoItensRecebimento = '';
  pedidoRecebimentoSelecionado: number | null = null;
  detalhePedidoRecebimento: any | null = null;
  itensNovoRecebimento: any[] = [];
  recebimentos: any[] = [];
  recebimentoEmEstorno: number | null = null;
  recebimentoEmAtualizacao: number | null = null;
  motivoEstornoRecebimento = '';
  exportandoHistoricoRecebimentos = false;
  abaRecebimentos: 'pendentes' | 'historico' = 'pendentes';
  recebimentoHistoricoExpandido: number | null = null;
  novoRecebimento = {
    numero_nota_fiscal: '',
    observacao: ''
  };
  filtroRecebimentos = { busca: '', status: '', ordem: 'recentes' };
  filtroHistoricoRecebimentos = {
    busca: '',
    status: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  entregas: any[] = [];
  clientes: any[] = [];
  usuariosResumo: any[] = [];
  carregandoEntregas = false;
  criandoEntrega = false;
  entregaEmAtualizacao: number | null = null;
  entregaEmEdicaoId: number | null = null;
  salvandoEdicaoEntrega = false;
  erroEdicaoEntrega = '';
  formularioEdicaoEntrega = {
    id_cliente: null as number | null,
    id_entregador: null as number | null,
    data_agendada: '',
    observacao: ''
  };
  entregaEmCancelamento: number | null = null;
  motivoCancelamentoEntrega = '';
  entregaEmNaoEntrega: number | null = null;
  motivoNaoEntrega = '';
  entregaHistoricoSelecionada: number | null = null;
  historicoEntrega: any[] = [];
  carregandoHistoricoEntrega = false;
  erroHistoricoEntrega = '';
  arquivoNovaEntrega: File | null = null;
  enviandoArquivoEntrega = false;
  comprovantesSelecionados: Record<number, File | null> = {};
  entregaComprovanteEmAtualizacao: number | null = null;
  arquivoEntregaEmDownload: number | null = null;
  erroEntregas = '';
  erroNovaEntrega = '';
  mensagemEntregas = '';
  exportandoEntregas = false;
  filtroEntregas = {
    busca: '',
    status: '',
    prazo: '',
    entregador: '',
    data_agendada: '',
    ordem: 'recentes'
  };
  entregadoresSelecionados: Record<number, number | null> = {};
  datasAgendamentoSelecionadas: Record<number, string> = {};
  visualizacaoEntregas: 'estagios' | 'agenda' = 'estagios';
  inicioSemanaAgenda = this.obterInicioSemanaAgenda(this.formatarDataHoje());
  dataAgendaSelecionada = this.formatarDataHoje();
  formularioAuxiliarEntrega: {
    idEntrega: number;
    tipo: FormularioAuxiliarEntrega;
  } | null = null;
  painelDetalhes: { tipo: TipoPainelDetalhes; registro: any } | null = null;
  modoCompacto: Record<ModuloOperacional, boolean> = {
    solicitacoes: false,
    pedidos: false,
    entregas: false
  };
  anexoPreVisualizacaoUrl: string | null = null;
  anexoPreVisualizacaoNome = '';
  anexoPreVisualizacaoCarregando: number | null = null;
  zoomPreVisualizacao = 1;
  novaEntrega = {
    id_cliente: null as number | null,
    id_entregador: null as number | null,
    data_agendada: '',
    anexo_pedido: '',
    observacao: ''
  };
  carregandoClientes = false;
  salvandoCliente = false;
  clienteEmAtualizacao: number | null = null;
  clienteEmEdicaoId: number | null = null;
  erroClientes = '';
  erroFormularioCliente = '';
  mensagemClientes = '';
  formularioCliente = {
    nome: '',
    cpf_cnpj: '',
    telefone: '',
    endereco: '',
    numero: '',
    bairro: '',
    cidade: '',
    uf: '',
    observacao: ''
  };
  filtroClientes = { busca: '', status: '', ordem: 'az' };
  usuarios: any[] = [];
  carregandoUsuarios = false;
  salvandoUsuario = false;
  usuarioEmAtualizacao: number | null = null;
  usuarioEmEdicaoId: number | null = null;
  erroUsuarios = '';
  erroFormularioUsuario = '';
  mensagemUsuarios = '';
  perfisUsuario = [
    'ADMINISTRADOR',
    'FUNCIONARIO',
    'ESTOQUE',
    'ENTREGADOR'
  ];
  formularioUsuario = {
    nome: '',
    login: '',
    senha: '',
    perfil: 'FUNCIONARIO'
  };
  filtroUsuarios = { busca: '', status: '', perfil: '', ordem: 'az' };
  carregandoFornecedores = false;
  salvandoFornecedor = false;
  fornecedorEmAtualizacao: number | null = null;
  fornecedorEmEdicaoId: number | null = null;
  erroFornecedores = '';
  erroFormularioFornecedor = '';
  mensagemFornecedores = '';
  formularioFornecedor = {
    razao_social: '',
    nome_fantasia: '',
    cnpj: '',
    telefone: '',
    email: ''
  };
  filtroFornecedores = { busca: '', status: '', ordem: 'az' };
  carregandoProdutosTela = false;
  salvandoProduto = false;
  produtoEmAtualizacao: number | null = null;
  produtoEmEdicaoId: number | null = null;
  erroProdutos = '';
  erroFormularioProduto = '';
  mensagemProdutos = '';
  formularioProduto = {
    codigo: '',
    nome: '',
    categoria: '',
    marca: '',
    unidade: '',
    descricao: ''
  };
  filtroProdutos = { busca: '', status: '', ordem: 'az' };
  notificacoes: any[] = [];
  carregandoNotificacoes = false;
  marcandoTodasNotificacoes = false;
  notificacaoEmAtualizacao: number | null = null;
  erroNotificacoes = '';
  mensagemNotificacoes = '';
  avisoNovaNotificacao = '';
  ultimaAtualizacaoNotificacoes: Date | null = null;
  filtroNotificacoes = { busca: '', status: '', ordem: 'recentes' };
  eventosAuditoria: any[] = [];
  carregandoAuditoria = false;
  exportandoAuditoria = false;
  erroAuditoria = '';
  mensagemAuditoria = '';
  filtroAuditoria = {
    busca: '',
    usuario: '',
    tipo: '',
    acao: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  resumoDashboard: any | null = null;
  carregandoResumoDashboard = false;
  erroResumoDashboard = '';
  readonly opcoesItensPorPagina = [5, 10, 20];
  paginacao: Record<ChavePaginacao, { pagina: number; porPagina: number }> = {
    solicitacoes: { pagina: 1, porPagina: 5 },
    pedidos: { pagina: 1, porPagina: 5 },
    recebimentos: { pagina: 1, porPagina: 5 },
    historico_recebimentos: { pagina: 1, porPagina: 5 },
    entregas: { pagina: 1, porPagina: 5 },
    clientes: { pagina: 1, porPagina: 5 },
    usuarios: { pagina: 1, porPagina: 5 },
    fornecedores: { pagina: 1, porPagina: 5 },
    produtos: { pagina: 1, porPagina: 5 },
    notificacoes: { pagina: 1, porPagina: 5 },
    auditoria: { pagina: 1, porPagina: 10 }
  };
  relatorioResumo: any | null = null;
  carregandoRelatorio = false;
  exportandoRelatorio = false;
  erroRelatorio = '';
  mensagemRelatorio = '';
  filtroRelatorio = {
    data_inicio: '',
    data_fim: ''
  };
  dataHoje = this.formatarDataHoje();
  novoPedido = {
    id_solicitacao: null as number | null,
    id_fornecedor: null as number | null,
    numero_pedido: '',
    data_pedido: this.formatarDataHoje(),
    observacao: ''
  };
  novaSolicitacao = {
  prioridade: 'MEDIA',
  motivo: '',
  observacao: '',
  itens: [
    {
      id_produto: null as number | null,
      quantidade: 1
    }
  ]
};

private readonly tratarSessaoExpirada = () => {
  this.encerrarSessao('Sua sessão expirou. Faça login novamente.');
};

private readonly tratarNavegacaoHistorico = () => {
  if (!this.logado) return;
  const tela = new URLSearchParams(window.location.search).get('tela') || this.telaInicialPerfil();
  if (this.telaPermitida(tela)) this.abrirTela(tela, false);
};

private readonly salvarAntesDeSair = () => this.salvarEstadoNavegacao();
private posicoesRolagem: Record<string, number> = {};

urlApi(caminho: string): string {
  const rota = caminho.startsWith('/') ? caminho : `/${caminho}`;
  return `${this.apiUrl}${rota}`;
}

  constructor(
  private http: HttpClient,
  private cdr: ChangeDetectorRef,
  private router: Router
) {}

ngOnInit() {
  document.title = this.tituloBase;
  window.addEventListener('sessao-expirada', this.tratarSessaoExpirada);
  window.addEventListener('popstate', this.tratarNavegacaoHistorico);
  window.addEventListener('beforeunload', this.salvarAntesDeSair);
  this.configurarBuscaGlobal();

  const token = localStorage.getItem('token');

  if (token) {
    this.validarSessaoExistente(token);
  } else {
    void this.router.navigateByUrl('/', { replaceUrl: true });
  }
}

ngOnDestroy() {
  window.removeEventListener('sessao-expirada', this.tratarSessaoExpirada);
  window.removeEventListener('popstate', this.tratarNavegacaoHistorico);
  window.removeEventListener('beforeunload', this.salvarAntesDeSair);
  this.buscaGlobalSubscription?.unsubscribe();
  this.pararAtualizacaoAutomaticaNotificacoes();
  document.title = this.tituloBase;
  this.liberarUrlPreVisualizacao();
}

private chaveEstadoNavegacao(): string | null {
  return this.idUsuarioAtual === null
    ? null
    : `fcl-estado-navegacao-v${this.versaoEstadoNavegacao}:${this.idUsuarioAtual}`;
}

salvarEstadoNavegacao(): void {
  const chave = this.chaveEstadoNavegacao();
  if (!chave || this.restaurandoNavegacao) return;
  this.posicoesRolagem[this.telaAtual] = window.scrollY;
  sessionStorage.setItem(chave, JSON.stringify({
    versao: this.versaoEstadoNavegacao,
    tela: this.telaAtual,
    filtros: {
      solicitacoes: this.filtroSolicitacoes,
      pedidos: this.filtroPedidos,
      recebimentos: this.filtroRecebimentos,
      historicoRecebimentos: this.filtroHistoricoRecebimentos,
      entregas: this.filtroEntregas,
      clientes: this.filtroClientes,
      fornecedores: this.filtroFornecedores,
      produtos: this.filtroProdutos,
      usuarios: this.filtroUsuarios
    },
    paginacao: this.paginacao,
    abaRecebimentos: this.abaRecebimentos,
    abaMinhasEntregas: this.abaMinhasEntregas,
    visualizacaoEntregas: this.visualizacaoEntregas,
    modoCompacto: this.modoCompacto,
    inicioSemanaAgenda: this.inicioSemanaAgenda,
    dataAgendaSelecionada: this.dataAgendaSelecionada,
    posicoesRolagem: this.posicoesRolagem
  }));
}

restaurarEstadoNavegacao(): void {
  const chave = this.chaveEstadoNavegacao();
  if (!chave) return;
  this.restaurandoNavegacao = true;
  try {
    const bruto = sessionStorage.getItem(chave);
    if (!bruto) return;
    const estado = JSON.parse(bruto);
    if (estado?.versao !== this.versaoEstadoNavegacao) {
      sessionStorage.removeItem(chave);
      return;
    }
    this.telaAtual = String(estado.tela || this.telaInicialPerfil());
    this.filtroSolicitacoes = { ...this.filtroSolicitacoes, ...estado.filtros?.solicitacoes };
    this.filtroPedidos = { ...this.filtroPedidos, ...estado.filtros?.pedidos };
    this.filtroRecebimentos = { ...this.filtroRecebimentos, ...estado.filtros?.recebimentos };
    this.filtroHistoricoRecebimentos = { ...this.filtroHistoricoRecebimentos, ...estado.filtros?.historicoRecebimentos };
    this.filtroEntregas = { ...this.filtroEntregas, ...estado.filtros?.entregas };
    this.filtroClientes = { ...this.filtroClientes, ...estado.filtros?.clientes };
    this.filtroFornecedores = { ...this.filtroFornecedores, ...estado.filtros?.fornecedores };
    this.filtroProdutos = { ...this.filtroProdutos, ...estado.filtros?.produtos };
    this.filtroUsuarios = { ...this.filtroUsuarios, ...estado.filtros?.usuarios };
    for (const item of Object.keys(this.paginacao) as ChavePaginacao[]) {
      const paginaSalva = estado.paginacao?.[item];
      if (paginaSalva) {
        this.paginacao[item] = {
          pagina: Math.max(1, Number(paginaSalva.pagina) || 1),
          porPagina: this.opcoesItensPorPagina.includes(Number(paginaSalva.porPagina))
            ? Number(paginaSalva.porPagina)
            : this.paginacao[item].porPagina
        };
      }
    }
    if (['pendentes', 'historico'].includes(estado.abaRecebimentos)) this.abaRecebimentos = estado.abaRecebimentos;
    if (['hoje', 'proximas', 'andamento', 'concluidas'].includes(estado.abaMinhasEntregas)) this.abaMinhasEntregas = estado.abaMinhasEntregas;
    if (['estagios', 'agenda'].includes(estado.visualizacaoEntregas)) this.visualizacaoEntregas = estado.visualizacaoEntregas;
    for (const modulo of ['solicitacoes', 'pedidos', 'entregas'] as ModuloOperacional[]) {
      this.modoCompacto[modulo] = estado.modoCompacto?.[modulo] === true;
    }
    if (this.dataIsoValida(estado.inicioSemanaAgenda || '')) this.inicioSemanaAgenda = estado.inicioSemanaAgenda;
    if (this.dataIsoValida(estado.dataAgendaSelecionada || '')) this.dataAgendaSelecionada = estado.dataAgendaSelecionada;
    this.posicoesRolagem = estado.posicoesRolagem || {};
  } catch {
    sessionStorage.removeItem(chave);
  } finally {
    this.restaurandoNavegacao = false;
  }
}

telaInicialPerfil(): string {
  return this.perfilUsuario === 'ENTREGADOR' ? 'minhas-entregas' : 'dashboard';
}

telaPermitida(tela: string): boolean {
  const restricoes: Record<string, boolean> = {
    solicitacoes: this.podeAcessarSolicitacoes(),
    'nova-solicitacao': this.podeAcessarSolicitacoes(),
    pedidos: this.podeAcessarPedidos(),
    'novo-pedido': this.podeAcessarPedidos(),
    recebimentos: this.podeAcessarRecebimentos(),
    entregas: this.perfilUsuario !== 'ENTREGADOR',
    'nova-entrega': this.podeCadastrarEntrega(),
    'minhas-entregas': this.perfilUsuario === 'ENTREGADOR',
    usuarios: this.podeGerenciarUsuarios(),
    relatorios: this.podeAcessarRelatorios(),
    auditoria: this.podeAcessarAuditoria(),
    fornecedores: this.podeAcessarCadastrosDeCompras(),
    produtos: this.podeAcessarCadastrosDeCompras()
  };
  return restricoes[tela] ?? true;
}

private configurarBuscaGlobal(): void {
  this.buscaGlobalSubscription = this.buscaGlobal$.pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap(consulta => {
      const termo = consulta.trim();
      if (termo.length < 2) {
        this.buscandoGlobalmente = false;
        return of({ grupos: [] });
      }
      this.buscandoGlobalmente = true;
      this.erroBuscaGlobal = '';
      const token = localStorage.getItem('token');
      return this.http.get<any>(this.urlApi('/busca-global'), {
        params: new HttpParams().set('q', termo).set('limite', 5),
        headers: { Authorization: `Bearer ${token}` }
      }).pipe(
        catchError(() => {
          this.erroBuscaGlobal = 'Não foi possível realizar a busca.';
          return of({ grupos: [] });
        }),
        finalize(() => { this.buscandoGlobalmente = false; })
      );
    })
  ).subscribe(resposta => {
    this.gruposBuscaGlobal = resposta.grupos || [];
    this.cdr.detectChanges();
  });
}

atualizarBuscaGlobal(valor: string): void {
  this.consultaBuscaGlobal = valor;
  this.buscaGlobalAberta = true;
  this.buscaGlobal$.next(valor);
}

fecharBuscaGlobal(): void {
  this.buscaGlobalAberta = false;
  this.consultaBuscaGlobal = '';
  this.gruposBuscaGlobal = [];
  this.erroBuscaGlobal = '';
}

abrirResultadoBusca(resultado: any, tipo: string): void {
  const destinos: Record<string, { tela: string; filtro: any }> = {
    solicitacao: { tela: 'solicitacoes', filtro: this.filtroSolicitacoes },
    pedido: { tela: 'pedidos', filtro: this.filtroPedidos },
    entrega: { tela: this.perfilUsuario === 'ENTREGADOR' ? 'minhas-entregas' : 'entregas', filtro: this.filtroEntregas },
    cliente: { tela: 'clientes', filtro: this.filtroClientes },
    fornecedor: { tela: 'fornecedores', filtro: this.filtroFornecedores },
    produto: { tela: 'produtos', filtro: this.filtroProdutos },
    usuario: { tela: 'usuarios', filtro: this.filtroUsuarios }
  };
  const destino = destinos[tipo];
  if (!destino || !this.telaPermitida(destino.tela)) return;
  destino.filtro.busca = tipo === 'produto'
    ? String(resultado.subtitulo || resultado.titulo)
    : ['cliente', 'fornecedor', 'usuario'].includes(tipo)
      ? String(resultado.titulo)
      : String(resultado.id);
  if ('status' in destino.filtro) destino.filtro.status = '';
  if (tipo === 'entrega') {
    this.resultadoBuscaPendente = { tipo, id: Number(resultado.id) };
  }
  this.fecharBuscaGlobal();
  this.abrirTela(destino.tela);
}

private chaveRascunho(tipo: TipoRascunho): string | null {
  return this.idUsuarioAtual === null
    ? null
    : `fcl-rascunho-v${this.versaoRascunho}:${this.idUsuarioAtual}:${tipo}`;
}

salvarRascunhoFormulario(tipo: TipoRascunho): void {
  const chave = this.chaveRascunho(tipo);
  if (!chave) return;
  let dados: any;
  let preenchido = false;
  if (tipo === 'solicitacao') {
    dados = JSON.parse(JSON.stringify(this.novaSolicitacao));
    preenchido = Boolean(dados.motivo.trim() || dados.observacao.trim() ||
      dados.prioridade !== 'MEDIA' || dados.itens.some((item: any) => item.id_produto));
  } else if (tipo === 'pedido') {
    dados = {
      formulario: JSON.parse(JSON.stringify(this.novoPedido)),
      itens: JSON.parse(JSON.stringify(this.itensNovoPedido))
    };
    preenchido = Boolean(dados.formulario.id_solicitacao || dados.formulario.id_fornecedor ||
      dados.formulario.numero_pedido.trim() || dados.formulario.observacao.trim() || dados.itens.length);
  } else {
    dados = {
      id_cliente: this.novaEntrega.id_cliente,
      id_entregador: this.novaEntrega.id_entregador,
      data_agendada: this.novaEntrega.data_agendada,
      observacao: this.novaEntrega.observacao
    };
    preenchido = Boolean(dados.id_cliente || dados.id_entregador || dados.data_agendada || dados.observacao.trim());
  }
  if (!preenchido) {
    localStorage.removeItem(chave);
    return;
  }
  localStorage.setItem(chave, JSON.stringify({
    versao: this.versaoRascunho,
    expiraEm: Date.now() + this.validadeRascunhoMs,
    dados
  }));
}

verificarRascunho(tipo: TipoRascunho): void {
  this.rascunhoDisponivel = null;
  const chave = this.chaveRascunho(tipo);
  if (!chave) return;
  try {
    const bruto = localStorage.getItem(chave);
    if (!bruto) return;
    const rascunho = JSON.parse(bruto);
    if (rascunho?.versao !== this.versaoRascunho || Number(rascunho.expiraEm) <= Date.now()) {
      localStorage.removeItem(chave);
      return;
    }
    this.rascunhoDisponivel = { tipo, dados: rascunho.dados };
  } catch {
    localStorage.removeItem(chave);
  }
}

recuperarRascunho(): void {
  const rascunho = this.rascunhoDisponivel;
  if (!rascunho) return;
  const dados = rascunho.dados;
  if (rascunho.tipo === 'solicitacao') {
    this.novaSolicitacao = {
      prioridade: dados.prioridade || 'MEDIA',
      motivo: dados.motivo || '',
      observacao: dados.observacao || '',
      itens: Array.isArray(dados.itens) && dados.itens.length
        ? dados.itens.map((item: any) => ({
            id_produto: Number(item.id_produto) || null,
            quantidade: Math.max(1, Number(item.quantidade) || 1)
          }))
        : [{ id_produto: null, quantidade: 1 }]
    };
  } else if (rascunho.tipo === 'pedido') {
    this.novoPedido = { ...this.novoPedido, ...(dados.formulario || {}) };
    this.itensNovoPedido = Array.isArray(dados.itens) ? dados.itens : [];
  } else {
    this.novaEntrega = {
      ...this.novaEntrega,
      id_cliente: Number(dados.id_cliente) || null,
      id_entregador: Number(dados.id_entregador) || null,
      data_agendada: dados.data_agendada || '',
      anexo_pedido: '',
      observacao: dados.observacao || ''
    };
    this.arquivoNovaEntrega = null;
  }
  this.rascunhoDisponivel = null;
}

descartarRascunho(tipo?: TipoRascunho): void {
  const tipoEfetivo = tipo || this.rascunhoDisponivel?.tipo;
  if (!tipoEfetivo) return;
  const chave = this.chaveRascunho(tipoEfetivo);
  if (chave) localStorage.removeItem(chave);
  this.rascunhoDisponivel = null;
}

validarSessaoExistente(token: string) {
  this.http.get<any>(this.urlApi('/me'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (usuario) => {
      this.logado = true;
      this.idUsuarioAtual = usuario.id_usuario;
      this.nomeUsuarioAtual = usuario.nome;
      this.login = usuario.login;
      this.perfilUsuario = usuario.perfil;
      this.restaurarPreferenciaVisualizacao();
      this.restaurarEstadoNavegacao();
      const telaUrl = new URLSearchParams(window.location.search).get('tela');
      const telaInicial = telaUrl && this.telaPermitida(telaUrl)
        ? telaUrl
        : (this.telaPermitida(this.telaAtual) ? this.telaAtual : this.telaInicialPerfil());
      this.abrirTela(telaInicial, false);
      this.carregarNotificacoes(true);
      this.iniciarAtualizacaoAutomaticaNotificacoes();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      if (erro.status !== 401) {
        this.encerrarSessao('Não foi possível validar a sessão salva.');
      }
    }
  });
}

sair() {
  this.encerrarSessao();
}

encerrarSessao(mensagem = '') {
  this.salvarEstadoNavegacao();
  this.pararAtualizacaoAutomaticaNotificacoes();
  localStorage.removeItem('token');
  this.logado = false;
  this.idUsuarioAtual = null;
  this.nomeUsuarioAtual = '';
  this.perfilUsuario = '';
  this.telaAtual = 'dashboard';
  this.fecharBuscaGlobal();
  if (mensagem) {
    sessionStorage.setItem('mensagem_login', mensagem);
  } else {
    sessionStorage.removeItem('mensagem_login');
  }
  this.solicitacoes = [];
  this.solicitacaoEmAtualizacao = null;
  this.solicitacaoEmRejeicao = null;
  this.motivoRejeicao = '';
  this.solicitacaoEmCancelamento = null;
  this.motivoCancelamentoSolicitacao = '';
  this.solicitacaoEmEdicaoId = null;
  this.salvandoEdicaoSolicitacao = false;
  this.erroEdicaoSolicitacao = '';
  this.formularioEdicaoSolicitacao = {
    prioridade: 'MEDIA',
    motivo: '',
    observacao: '',
    itens: []
  };
  this.solicitacaoHistoricoSelecionada = null;
  this.historicoSolicitacao = [];
  this.carregandoHistoricoSolicitacao = false;
  this.erroHistoricoSolicitacao = '';
  this.pedidos = [];
  this.pedidoEmCancelamento = null;
  this.motivoCancelamentoPedido = '';
  this.pedidoEmEdicaoId = null;
  this.salvandoEdicaoPedido = false;
  this.erroEdicaoPedido = '';
  this.formularioEdicaoPedido = {
    id_fornecedor: null,
    numero_pedido: '',
    data_pedido: '',
    observacao: '',
    itens: []
  };
  this.pedidoHistoricoSelecionado = null;
  this.historicoPedido = [];
  this.carregandoHistoricoPedido = false;
  this.erroHistoricoPedido = '';
  this.fornecedores = [];
  this.produtos = [];
  this.entregas = [];
  this.entregaEmAtualizacao = null;
  this.entregaEmEdicaoId = null;
  this.salvandoEdicaoEntrega = false;
  this.erroEdicaoEntrega = '';
  this.formularioEdicaoEntrega = {
    id_cliente: null,
    id_entregador: null,
    data_agendada: '',
    observacao: ''
  };
  this.entregaEmCancelamento = null;
  this.motivoCancelamentoEntrega = '';
  this.entregaEmNaoEntrega = null;
  this.motivoNaoEntrega = '';
  this.entregaHistoricoSelecionada = null;
  this.historicoEntrega = [];
  this.arquivoNovaEntrega = null;
  this.comprovantesSelecionados = {};
  this.datasAgendamentoSelecionadas = {};
  this.clientes = [];
  this.usuarios = [];
  this.usuariosResumo = [];
  this.notificacoes = [];
  this.atualizarTituloNotificacoes();
  this.notificacoesInicializadas = false;
  this.avisoNovaNotificacao = '';
  this.marcandoTodasNotificacoes = false;
  this.mensagemNotificacoes = '';
  this.ultimaAtualizacaoNotificacoes = null;
  this.eventosAuditoria = [];
  this.exportandoAuditoria = false;
  this.erroAuditoria = '';
  this.mensagemAuditoria = '';
  this.resumoDashboard = null;
  this.carregandoResumoDashboard = false;
  this.erroResumoDashboard = '';
  this.relatorioResumo = null;
  this.detalhePedidoRecebimento = null;
  this.itensNovoRecebimento = [];
  this.recebimentos = [];
  this.recebimentoEmEstorno = null;
  this.recebimentoEmAtualizacao = null;
  this.motivoEstornoRecebimento = '';
  this.salvandoMinhaSenha = false;
  this.erroMinhaConta = '';
  this.mensagemMinhaConta = '';
  this.formularioMinhaSenha = {
    senha_atual: '',
    nova_senha: '',
    confirmar_nova_senha: ''
  };
  this.cdr.detectChanges();
  void this.router.navigateByUrl('/', { replaceUrl: true });
}

alterarPropriaSenha() {
  this.erroMinhaConta = '';
  this.mensagemMinhaConta = '';

  const dados = this.formularioMinhaSenha;

  if (!dados.senha_atual || !dados.nova_senha || !dados.confirmar_nova_senha) {
    this.erroMinhaConta = 'Preencha todos os campos de senha.';
    return;
  }

  if (dados.nova_senha.length < 6) {
    this.erroMinhaConta = 'A nova senha deve possuir pelo menos 6 caracteres.';
    return;
  }

  if (dados.nova_senha !== dados.confirmar_nova_senha) {
    this.erroMinhaConta = 'A confirmação da nova senha não confere.';
    return;
  }

  if (dados.nova_senha === dados.senha_atual) {
    this.erroMinhaConta = 'A nova senha deve ser diferente da senha atual.';
    return;
  }

  const token = localStorage.getItem('token');
  this.salvandoMinhaSenha = true;

  this.http.patch<any>(
    this.urlApi('/usuarios/minha-conta/senha'),
    dados,
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (resposta) => {
      localStorage.setItem('token', resposta.access_token);
      this.salvandoMinhaSenha = false;
      this.mensagemMinhaConta = 'Senha alterada com sucesso.';
      this.formularioMinhaSenha = {
        senha_atual: '',
        nova_senha: '',
        confirmar_nova_senha: ''
      };
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.salvandoMinhaSenha = false;
      this.erroMinhaConta = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível alterar a senha.';
      this.cdr.detectChanges();
    }
  });
}

carregarSolicitacoes() {
  const token = localStorage.getItem('token');

  this.carregandoSolicitacoes = true;
  this.erroSolicitacoes = '';

  this.http.get<any[]>(this.urlApi('/solicitacoes/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (resposta) => {
      this.solicitacoes = resposta;
      this.carregandoSolicitacoes = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar solicitações:', erro);
      this.carregandoSolicitacoes = false;
      this.erroSolicitacoes = 'Não foi possível carregar as solicitações.';
      this.cdr.detectChanges();
    }
  });
}

iniciarAnalise(idSolicitacao: number) {
  const token = localStorage.getItem('token');

  this.solicitacaoEmAtualizacao = idSolicitacao;
  this.erroSolicitacoes = '';
  this.mensagemSolicitacoes = '';

  this.http.patch(
    this.urlApi(`/solicitacoes/${idSolicitacao}/iniciar-analise`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.solicitacaoEmAtualizacao = null;
      this.mensagemSolicitacoes = `Solicitação #${idSolicitacao} enviada para análise.`;
      this.carregarSolicitacoes();
    },

    error: (erro) => {
      console.error('Erro ao iniciar análise:', erro);
      const detalhe = erro.error?.detail;

      this.solicitacaoEmAtualizacao = null;
      this.erroSolicitacoes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível iniciar a análise.';
      this.cdr.detectChanges();
    }
  });
}

aprovarSolicitacao(idSolicitacao: number) {
  const token = localStorage.getItem('token');

  this.solicitacaoEmAtualizacao = idSolicitacao;
  this.erroSolicitacoes = '';
  this.mensagemSolicitacoes = '';

  this.http.patch(
    this.urlApi(`/solicitacoes/${idSolicitacao}/aprovar`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.solicitacaoEmAtualizacao = null;
      this.mensagemSolicitacoes = `Solicitação #${idSolicitacao} aprovada com sucesso!`;
      this.carregarSolicitacoes();
    },

    error: (erro) => {
      console.error('Erro ao aprovar solicitação:', erro);
      const detalhe = erro.error?.detail;

      this.solicitacaoEmAtualizacao = null;
      this.erroSolicitacoes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível aprovar a solicitação.';
      this.cdr.detectChanges();
    }
  });
}

abrirRejeicaoSolicitacao(idSolicitacao: number) {
  this.solicitacaoEmRejeicao = idSolicitacao;
  this.motivoRejeicao = '';
  this.erroSolicitacoes = '';
}

cancelarRejeicaoSolicitacao() {
  this.solicitacaoEmRejeicao = null;
  this.motivoRejeicao = '';
}

confirmarRejeicaoSolicitacao(idSolicitacao: number) {
  if (!this.motivoRejeicao.trim()) {
    this.erroSolicitacoes = 'Informe o motivo da rejeição.';
    return;
  }

  const token = localStorage.getItem('token');

  this.solicitacaoEmAtualizacao = idSolicitacao;
  this.erroSolicitacoes = '';
  this.mensagemSolicitacoes = '';

  this.http.patch(
    this.urlApi(`/solicitacoes/${idSolicitacao}/rejeitar`),
    {
      motivo_rejeicao: this.motivoRejeicao.trim()
    },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.solicitacaoEmAtualizacao = null;
      this.cancelarRejeicaoSolicitacao();
      this.mensagemSolicitacoes = `Solicitação #${idSolicitacao} rejeitada.`;
      this.carregarSolicitacoes();
    },

    error: (erro) => {
      console.error('Erro ao rejeitar solicitação:', erro);
      const detalhe = erro.error?.detail;

      this.solicitacaoEmAtualizacao = null;
      this.erroSolicitacoes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível rejeitar a solicitação.';
      this.cdr.detectChanges();
    }
  });
}

podeCancelarSolicitacao(solicitacao: any): boolean {
  if (this.perfilUsuario === 'ADMINISTRADOR') {
    return ['SOLICITADA', 'EM_ANALISE', 'APROVADA'].includes(solicitacao.status);
  }

  return solicitacao.status === 'SOLICITADA' &&
    solicitacao.id_usuario_solicitante === this.idUsuarioAtual;
}

abrirCancelamentoSolicitacao(idSolicitacao: number) {
  this.solicitacaoEmCancelamento = idSolicitacao;
  this.motivoCancelamentoSolicitacao = '';
  this.solicitacaoEmRejeicao = null;
  this.motivoRejeicao = '';
  this.erroSolicitacoes = '';
  this.mensagemSolicitacoes = '';
}

desistirCancelamentoSolicitacao() {
  this.solicitacaoEmCancelamento = null;
  this.motivoCancelamentoSolicitacao = '';
}

confirmarCancelamentoSolicitacao(solicitacao: any) {
  const motivo = this.motivoCancelamentoSolicitacao.trim();
  if (motivo.length < 3) {
    this.erroSolicitacoes = 'Informe o motivo do cancelamento.';
    return;
  }

  const token = localStorage.getItem('token');
  this.solicitacaoEmAtualizacao = solicitacao.id_solicitacao;
  this.erroSolicitacoes = '';
  this.mensagemSolicitacoes = '';

  this.http.patch<any>(
    this.urlApi(`/solicitacoes/${solicitacao.id_solicitacao}/cancelar`),
    { motivo },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.solicitacaoEmAtualizacao = null;
      this.solicitacaoEmCancelamento = null;
      this.motivoCancelamentoSolicitacao = '';
      this.mensagemSolicitacoes = `Solicitação #${solicitacao.id_solicitacao} cancelada com sucesso.`;
      this.carregarSolicitacoes();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.solicitacaoEmAtualizacao = null;
      this.erroSolicitacoes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível cancelar a solicitação.';
      this.cdr.detectChanges();
    }
  });
}

podeEditarSolicitacao(solicitacao: any): boolean {
  return solicitacao.status === 'SOLICITADA' && (
    this.perfilUsuario === 'ADMINISTRADOR' ||
    solicitacao.id_usuario_solicitante === this.idUsuarioAtual
  );
}

abrirEdicaoSolicitacao(solicitacao: any) {
  this.solicitacaoEmEdicaoId = solicitacao.id_solicitacao;
  this.formularioEdicaoSolicitacao = {
    prioridade: solicitacao.prioridade,
    motivo: solicitacao.motivo,
    observacao: solicitacao.observacao || '',
    itens: (solicitacao.itens || []).map((item: any) => ({
      id_produto: item.id_produto,
      quantidade: Number(item.quantidade)
    }))
  };
  this.erroEdicaoSolicitacao = '';
  this.solicitacaoEmRejeicao = null;
  this.solicitacaoEmCancelamento = null;
}

desistirEdicaoSolicitacao() {
  this.solicitacaoEmEdicaoId = null;
  this.salvandoEdicaoSolicitacao = false;
  this.erroEdicaoSolicitacao = '';
}

adicionarItemEdicaoSolicitacao() {
  this.formularioEdicaoSolicitacao.itens.push({
    id_produto: null,
    quantidade: 1
  });
}

removerItemEdicaoSolicitacao(indice: number) {
  if (this.formularioEdicaoSolicitacao.itens.length > 1) {
    this.formularioEdicaoSolicitacao.itens.splice(indice, 1);
  }
}

salvarEdicaoSolicitacao(solicitacao: any) {
  const formulario = this.formularioEdicaoSolicitacao;
  const idsProdutos = formulario.itens.map(item => Number(item.id_produto));

  if (!formulario.motivo.trim()) {
    this.erroEdicaoSolicitacao = 'Informe o motivo da compra.';
    return;
  }

  if (
    !formulario.itens.length ||
    formulario.itens.some(
      item => !item.id_produto || Number(item.quantidade) < 1
    )
  ) {
    this.erroEdicaoSolicitacao = 'Selecione os produtos e informe quantidades válidas.';
    return;
  }

  if (new Set(idsProdutos).size !== idsProdutos.length) {
    this.erroEdicaoSolicitacao = 'Não repita o mesmo produto na solicitação.';
    return;
  }

  const token = localStorage.getItem('token');
  const dados = {
    prioridade: formulario.prioridade,
    motivo: formulario.motivo.trim(),
    observacao: formulario.observacao.trim() || null,
    itens: formulario.itens.map(item => ({
      id_produto: Number(item.id_produto),
      quantidade: Number(item.quantidade)
    }))
  };

  this.salvandoEdicaoSolicitacao = true;
  this.erroEdicaoSolicitacao = '';
  this.http.put<any>(
    this.urlApi(`/solicitacoes/${solicitacao.id_solicitacao}`),
    dados,
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.desistirEdicaoSolicitacao();
      this.mensagemSolicitacoes = `Solicitação #${solicitacao.id_solicitacao} atualizada com sucesso.`;
      this.carregarSolicitacoes();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.salvandoEdicaoSolicitacao = false;
      this.erroEdicaoSolicitacao = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível editar a solicitação.';
      this.cdr.detectChanges();
    }
  });
}

alternarHistoricoSolicitacao(idSolicitacao: number) {
  if (this.solicitacaoHistoricoSelecionada === idSolicitacao) {
    this.solicitacaoHistoricoSelecionada = null;
    this.historicoSolicitacao = [];
    this.erroHistoricoSolicitacao = '';
    return;
  }

  this.solicitacaoHistoricoSelecionada = idSolicitacao;
  this.historicoSolicitacao = [];
  this.carregarHistoricoSolicitacao(idSolicitacao);
}

carregarHistoricoSolicitacao(idSolicitacao: number) {
  const token = localStorage.getItem('token');
  this.carregandoHistoricoSolicitacao = true;
  this.erroHistoricoSolicitacao = '';

  this.http.get<any[]>(
    this.urlApi(`/solicitacoes/${idSolicitacao}/historico`),
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (historico) => {
      if (this.solicitacaoHistoricoSelecionada === idSolicitacao) {
        this.historicoSolicitacao = historico;
      }
      this.carregandoHistoricoSolicitacao = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.carregandoHistoricoSolicitacao = false;
      this.erroHistoricoSolicitacao = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar o histórico da solicitação.';
      this.cdr.detectChanges();
    }
  });
}

formatarAcaoHistoricoSolicitacao(acao: string): string {
  const nomes: Record<string, string> = {
    CADASTRO: 'Solicitação cadastrada',
    EDICAO: 'Solicitação editada',
    ALTERACAO_STATUS: 'Análise iniciada',
    APROVACAO: 'Solicitação aprovada',
    REJEICAO: 'Solicitação rejeitada',
    CANCELAMENTO: 'Solicitação cancelada',
    PEDIDO_CRIADO: 'Pedido criado',
    PEDIDO_REALIZADO: 'Itens distribuídos em pedidos',
    PEDIDO_CANCELADO: 'Pedido cancelado',
    PEDIDO_EDITADO: 'Pedido editado'
  };

  return nomes[acao] || acao.replaceAll('_', ' ');
}

  carregarProdutos() {
  const token = localStorage.getItem('token');

  this.http.get<any[]>(this.urlApi('/produtos/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (resposta) => {
      this.produtos = resposta;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar produtos:', erro);
    }
  });
}

adicionarItem() {
  this.novaSolicitacao.itens.push({
    id_produto: null,
    quantidade: 1
  });

  this.salvarRascunhoFormulario('solicitacao');
  this.cdr.detectChanges();
}

removerItem(index: number) {
  if (this.novaSolicitacao.itens.length > 1) {
    this.novaSolicitacao.itens.splice(index, 1);
    this.salvarRascunhoFormulario('solicitacao');
    this.cdr.detectChanges();
  }
}
carregarPedidos() {
  const token = localStorage.getItem('token');
  const opcoes = {
    headers: {
      Authorization: `Bearer ${token}`
    }
  };

  this.carregandoPedidos = true;
  this.erroPedidos = '';

  forkJoin({
    pedidos: this.http.get<any[]>(this.urlApi('/pedidos/'), opcoes),
    fornecedores: this.http.get<any[]>(this.urlApi('/fornecedores/'), opcoes),
    solicitacoes: this.http.get<any[]>(this.urlApi('/solicitacoes/'), opcoes),
    produtos: this.http.get<any[]>(this.urlApi('/produtos/'), opcoes)
  }).subscribe({
    next: (resposta) => {
      this.pedidos = resposta.pedidos;
      this.fornecedores = resposta.fornecedores;
      this.solicitacoes = resposta.solicitacoes;
      this.produtos = resposta.produtos;
      this.carregandoPedidos = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar pedidos:', erro);
      this.carregandoPedidos = false;
      this.erroPedidos = erro.status === 403
        ? 'Seu perfil não possui permissão para visualizar pedidos.'
        : 'Não foi possível carregar os pedidos.';
      this.cdr.detectChanges();
    }
  });
}

alternarHistoricoPedido(idPedidoCompra: number) {
  if (this.pedidoHistoricoSelecionado === idPedidoCompra) {
    this.pedidoHistoricoSelecionado = null;
    this.historicoPedido = [];
    this.erroHistoricoPedido = '';
    return;
  }

  this.pedidoHistoricoSelecionado = idPedidoCompra;
  this.historicoPedido = [];
  this.carregarHistoricoPedido(idPedidoCompra);
}

carregarHistoricoPedido(idPedidoCompra: number) {
  const token = localStorage.getItem('token');
  this.carregandoHistoricoPedido = true;
  this.erroHistoricoPedido = '';

  this.http.get<any[]>(
    this.urlApi(`/pedidos/${idPedidoCompra}/historico`),
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (historico) => {
      if (this.pedidoHistoricoSelecionado === idPedidoCompra) {
        this.historicoPedido = historico;
      }
      this.carregandoHistoricoPedido = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.carregandoHistoricoPedido = false;
      this.erroHistoricoPedido = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar o histórico do pedido.';
      this.cdr.detectChanges();
    }
  });
}

formatarAcaoHistoricoPedido(acao: string): string {
  const nomes: Record<string, string> = {
    CADASTRO: 'Pedido criado',
    EDICAO: 'Pedido editado',
    ENVIO_RECEBIMENTO: 'Enviado para recebimento',
    RECEBIMENTO_PARCIAL: 'Recebimento parcial',
    RECEBIMENTO_TOTAL: 'Recebimento total',
    ESTORNO_RECEBIMENTO: 'Recebimento estornado',
    CANCELAMENTO: 'Pedido cancelado'
  };

  return nomes[acao] || acao.replaceAll('_', ' ');
}

podeEditarPedido(pedido: any): boolean {
  return this.podeAdministrarPedidos() && pedido.status === 'CRIADO';
}

obterQuantidadePedidaPorOutrosPedidos(
  idItemSolicitacao: number,
  idPedidoIgnorado: number
): number {
  return this.pedidos
    .filter(pedido =>
      pedido.status !== 'CANCELADO' &&
      pedido.id_pedido_compra !== idPedidoIgnorado
    )
    .reduce((total, pedido) => {
      const quantidade = (pedido.itens || [])
        .filter((item: any) => item.id_item_solicitacao === idItemSolicitacao)
        .reduce(
          (subtotal: number, item: any) => subtotal + Number(item.quantidade),
          0
        );
      return total + quantidade;
    }, 0);
}

abrirEdicaoPedido(pedido: any) {
  const solicitacao = this.solicitacoes.find(
    item => item.id_solicitacao === pedido.id_solicitacao
  );
  if (!solicitacao) {
    this.erroAcaoPedidos = 'Não foi possível localizar a solicitação de origem.';
    return;
  }

  this.pedidoEmEdicaoId = pedido.id_pedido_compra;
  this.formularioEdicaoPedido = {
    id_fornecedor: pedido.id_fornecedor,
    numero_pedido: pedido.numero_pedido || '',
    data_pedido: pedido.data_pedido,
    observacao: pedido.observacao || '',
    itens: (solicitacao.itens || []).map((item: any) => {
      const itemAtual = (pedido.itens || []).find(
        (itemPedido: any) =>
          itemPedido.id_item_solicitacao === item.id_item_solicitacao
      );
      const saldo = Math.max(
        0,
        Number(item.quantidade) - this.obterQuantidadePedidaPorOutrosPedidos(
          item.id_item_solicitacao,
          pedido.id_pedido_compra
        )
      );
      return {
        id_item_solicitacao: item.id_item_solicitacao,
        id_produto: item.id_produto,
        saldo,
        quantidade: itemAtual ? Number(itemAtual.quantidade) : 0
      };
    })
  };
  this.erroEdicaoPedido = '';
  this.erroAcaoPedidos = '';
  this.pedidoEmCancelamento = null;
}

desistirEdicaoPedido() {
  this.pedidoEmEdicaoId = null;
  this.salvandoEdicaoPedido = false;
  this.erroEdicaoPedido = '';
}

salvarEdicaoPedido(pedido: any) {
  const formulario = this.formularioEdicaoPedido;
  if (
    formulario.id_fornecedor === null ||
    !formulario.numero_pedido.trim() ||
    !formulario.data_pedido
  ) {
    this.erroEdicaoPedido = 'Preencha todos os campos obrigatórios.';
    return;
  }
  if (formulario.numero_pedido.trim().length > 30) {
    this.erroEdicaoPedido = 'O número do pedido deve ter no máximo 30 caracteres.';
    return;
  }
  if (
    !this.dataIsoValida(formulario.data_pedido) ||
    formulario.data_pedido > this.formatarDataHoje()
  ) {
    this.erroEdicaoPedido = 'Informe uma data válida que não seja futura.';
    return;
  }

  const itensSelecionados = formulario.itens.filter(
    item => Number(item.quantidade) > 0
  );
  if (!itensSelecionados.length) {
    this.erroEdicaoPedido = 'Informe a quantidade de pelo menos um produto.';
    return;
  }
  if (itensSelecionados.some(item =>
    !Number.isFinite(Number(item.quantidade)) ||
    Number(item.quantidade) > Number(item.saldo)
  )) {
    this.erroEdicaoPedido = 'A quantidade informada ultrapassa o saldo disponível.';
    return;
  }

  const token = localStorage.getItem('token');
  const dados = {
    id_fornecedor: formulario.id_fornecedor,
    numero_pedido: formulario.numero_pedido.trim(),
    data_pedido: formulario.data_pedido,
    observacao: formulario.observacao.trim() || null,
    itens: itensSelecionados.map(item => ({
      id_item_solicitacao: item.id_item_solicitacao,
      quantidade: Number(item.quantidade)
    }))
  };

  this.salvandoEdicaoPedido = true;
  this.erroEdicaoPedido = '';
  this.http.put<any>(
    this.urlApi(`/pedidos/${pedido.id_pedido_compra}`),
    dados,
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (pedidoAtualizado) => {
      this.desistirEdicaoPedido();
      this.mensagemPedidos = `Pedido ${pedidoAtualizado.numero_pedido} atualizado com sucesso.`;
      this.carregarPedidos();
      if (this.pedidoHistoricoSelecionado === pedido.id_pedido_compra) {
        this.carregarHistoricoPedido(pedido.id_pedido_compra);
      }
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.salvandoEdicaoPedido = false;
      this.erroEdicaoPedido = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível editar o pedido.';
      this.cdr.detectChanges();
    }
  });
}

formatarDataHoje(): string {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = String(hoje.getMonth() + 1).padStart(2, '0');
  const dia = String(hoje.getDate()).padStart(2, '0');

  return `${ano}-${mes}-${dia}`;
}

formatarDataBrasileira(valor: string): string {
  if (!this.dataIsoValida(valor)) {
    return valor;
  }

  const [ano, mes, dia] = valor.split('-');
  return `${dia}/${mes}/${ano}`;
}

obterSomenteDigitos(valor: string, limite = 15): string {
  return (valor || '').replace(/\D/g, '').slice(0, limite);
}

formatarCpfCnpj(valor: string): string {
  const digitos = this.obterSomenteDigitos(valor, 14);

  if (digitos.length <= 11) {
    return digitos
      .replace(/^(\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1-$2');
  }

  return digitos
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2');
}

formatarCnpj(valor: string): string {
  const digitos = this.obterSomenteDigitos(valor, 14);

  return digitos
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2');
}

formatarTelefone(valor: string): string {
  const digitos = this.obterSomenteDigitos(valor, 15);
  const quantidadeCodigoPais = Math.max(0, digitos.length - 11);
  const codigoPais = digitos.slice(0, quantidadeCodigoPais);
  const numeroNacional = digitos.slice(quantidadeCodigoPais);
  const prefixo = codigoPais ? `+${codigoPais} ` : '';

  if (numeroNacional.length <= 2) {
    return prefixo + numeroNacional;
  }

  const ddd = numeroNacional.slice(0, 2);
  const numero = numeroNacional.slice(2);
  const tamanhoPrimeiraParte = numero.length > 8 ? 5 : 4;

  if (numero.length <= tamanhoPrimeiraParte) {
    return `${prefixo}(${ddd}) ${numero}`;
  }

  return `${prefixo}(${ddd}) ${numero.slice(0, tamanhoPrimeiraParte)}-${numero.slice(tamanhoPrimeiraParte)}`;
}

aplicarMascaraCpfCnpjCliente(): void {
  this.formularioCliente.cpf_cnpj = this.formatarCpfCnpj(
    this.formularioCliente.cpf_cnpj
  );
}

aplicarMascaraTelefoneCliente(): void {
  this.formularioCliente.telefone = this.formatarTelefone(
    this.formularioCliente.telefone
  );
}

aplicarMascaraCnpjFornecedor(): void {
  this.formularioFornecedor.cnpj = this.formatarCnpj(
    this.formularioFornecedor.cnpj
  );
}

aplicarMascaraTelefoneFornecedor(): void {
  this.formularioFornecedor.telefone = this.formatarTelefone(
    this.formularioFornecedor.telefone
  );
}

validarCpf(valor: string): boolean {
  const cpf = (valor || '').replace(/\D/g, '');

  if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) {
    return false;
  }

  const calcularDigito = (quantidade: number): number => {
    let soma = 0;

    for (let indice = 0; indice < quantidade; indice += 1) {
      soma += Number(cpf[indice]) * (quantidade + 1 - indice);
    }

    const digito = (soma * 10) % 11;
    return digito === 10 ? 0 : digito;
  };

  return calcularDigito(9) === Number(cpf[9]) &&
    calcularDigito(10) === Number(cpf[10]);
}

validarCnpj(valor: string): boolean {
  const cnpj = (valor || '').replace(/\D/g, '');

  if (cnpj.length !== 14 || /^(\d)\1+$/.test(cnpj)) {
    return false;
  }

  const calcularDigito = (quantidade: number): number => {
    const pesos = quantidade === 12
      ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
      : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const soma = pesos.reduce(
      (total, peso, indice) => total + Number(cnpj[indice]) * peso,
      0
    );
    const resto = soma % 11;

    return resto < 2 ? 0 : 11 - resto;
  };

  return calcularDigito(12) === Number(cnpj[12]) &&
    calcularDigito(13) === Number(cnpj[13]);
}

validarCpfCnpj(valor: string): boolean {
  const digitos = (valor || '').replace(/\D/g, '');
  return digitos.length === 11
    ? this.validarCpf(digitos)
    : this.validarCnpj(digitos);
}

dataIsoValida(valor: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    return false;
  }

  const [ano, mes, dia] = valor.split('-').map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));

  return data.getUTCFullYear() === ano &&
    data.getUTCMonth() === mes - 1 &&
    data.getUTCDate() === dia;
}

restaurarPreferenciaVisualizacao(): void {
  if (this.idUsuarioAtual === null) return;
  const chave = `fcl-modo-compacto:${this.idUsuarioAtual}`;
  try {
    const preferencia = sessionStorage.getItem(chave);
    if (!preferencia) {
      return;
    }

    const valores = JSON.parse(preferencia);
    for (const modulo of ['solicitacoes', 'pedidos', 'entregas'] as ModuloOperacional[]) {
      this.modoCompacto[modulo] = valores?.[modulo] === true;
    }
  } catch {
    sessionStorage.removeItem(chave);
  }
}

alternarModoCompacto(modulo: ModuloOperacional): void {
  this.modoCompacto[modulo] = !this.modoCompacto[modulo];
  if (this.idUsuarioAtual !== null) {
    sessionStorage.setItem(
      `fcl-modo-compacto:${this.idUsuarioAtual}`,
      JSON.stringify(this.modoCompacto)
    );
  }
  this.salvarEstadoNavegacao();
}

selecionarVisualizacaoEntregas(visualizacao: 'estagios' | 'agenda'): void {
  this.visualizacaoEntregas = visualizacao;
  this.salvarEstadoNavegacao();
}

alternarFormularioAuxiliarEntrega(
  entrega: any,
  tipo: FormularioAuxiliarEntrega
): void {
  if (
    this.formularioAuxiliarEntrega?.idEntrega === entrega.id_entrega &&
    this.formularioAuxiliarEntrega?.tipo === tipo
  ) {
    this.fecharFormularioAuxiliarEntrega();
    return;
  }

  this.formularioAuxiliarEntrega = { idEntrega: entrega.id_entrega, tipo };
  this.erroEntregas = '';

  if (tipo === 'agendamento' && !this.datasAgendamentoSelecionadas[entrega.id_entrega]) {
    this.datasAgendamentoSelecionadas[entrega.id_entrega] = entrega.data_agendada || '';
  }
  if (tipo === 'entregador' && this.entregadoresSelecionados[entrega.id_entrega] === undefined) {
    this.entregadoresSelecionados[entrega.id_entrega] = entrega.id_entregador;
  }
}

formularioAuxiliarEntregaAberto(
  idEntrega: number,
  tipo: FormularioAuxiliarEntrega
): boolean {
  return this.formularioAuxiliarEntrega?.idEntrega === idEntrega &&
    this.formularioAuxiliarEntrega?.tipo === tipo;
}

fecharFormularioAuxiliarEntrega(): void {
  this.formularioAuxiliarEntrega = null;
}

abrirPainelDetalhes(tipo: TipoPainelDetalhes, registro: any): void {
  this.painelDetalhes = { tipo, registro };

  if (tipo === 'solicitacao') {
    this.solicitacaoHistoricoSelecionada = registro.id_solicitacao;
    this.historicoSolicitacao = [];
    this.carregarHistoricoSolicitacao(registro.id_solicitacao);
  } else if (tipo === 'pedido') {
    this.pedidoHistoricoSelecionado = registro.id_pedido_compra;
    this.historicoPedido = [];
    this.carregarHistoricoPedido(registro.id_pedido_compra);
  } else {
    this.entregaHistoricoSelecionada = registro.id_entrega;
    this.historicoEntrega = [];
    this.carregarHistoricoEntrega(registro.id_entrega);
  }
}

fecharPainelDetalhes(): void {
  const tipo = this.painelDetalhes?.tipo;
  this.painelDetalhes = null;

  if (tipo === 'solicitacao') {
    this.solicitacaoHistoricoSelecionada = null;
    this.historicoSolicitacao = [];
  } else if (tipo === 'pedido') {
    this.pedidoHistoricoSelecionado = null;
    this.historicoPedido = [];
  } else if (tipo === 'entrega') {
    this.entregaHistoricoSelecionada = null;
    this.historicoEntrega = [];
  }
}

obterInicioSemanaAgenda(dataIso: string): string {
  const data = this.dataIsoValida(dataIso)
    ? new Date(`${dataIso}T12:00:00Z`)
    : new Date();
  const diaSemana = data.getUTCDay();
  const deslocamento = diaSemana === 0 ? -6 : 1 - diaSemana;
  data.setUTCDate(data.getUTCDate() + deslocamento);
  return data.toISOString().slice(0, 10);
}

adicionarDiasDataIso(dataIso: string, quantidade: number): string {
  const data = new Date(`${dataIso}T12:00:00Z`);
  data.setUTCDate(data.getUTCDate() + quantidade);
  return data.toISOString().slice(0, 10);
}

obterDiasSemanaAgenda(): Array<{
  data: string;
  diaSemana: string;
  diaMes: string;
  total: number;
  hoje: boolean;
}> {
  const rotulos = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM'];
  const entregasFiltradas = this.obterEntregasFiltradas();
  return rotulos.map((diaSemana, indice) => {
    const data = this.adicionarDiasDataIso(this.inicioSemanaAgenda, indice);
    return {
      data,
      diaSemana,
      diaMes: this.formatarDataBrasileira(data).slice(0, 5),
      total: entregasFiltradas.filter(entrega => entrega.data_agendada === data).length,
      hoje: data === this.formatarDataHoje()
    };
  });
}

obterEntregasAgendaDia(data: string): any[] {
  return this.obterEntregasFiltradas().filter(
    entrega => entrega.data_agendada === data
  );
}

selecionarDataAgenda(data: string): void {
  this.dataAgendaSelecionada = data;
  this.salvarEstadoNavegacao();
}

alterarSemanaAgenda(quantidadeSemanas: number): void {
  this.inicioSemanaAgenda = this.adicionarDiasDataIso(
    this.inicioSemanaAgenda,
    quantidadeSemanas * 7
  );
  this.dataAgendaSelecionada = this.inicioSemanaAgenda;
  this.salvarEstadoNavegacao();
}

voltarSemanaAtual(): void {
  const hoje = this.formatarDataHoje();
  this.inicioSemanaAgenda = this.obterInicioSemanaAgenda(hoje);
  this.dataAgendaSelecionada = hoje;
  this.salvarEstadoNavegacao();
}

obterDataAmanha(): string {
  return this.adicionarDiasDataIso(this.formatarDataHoje(), 1);
}

contarIndicadorEntrega(tipo: 'ATRASADA' | 'HOJE' | 'AMANHA' | 'EM_ROTA' | 'NAO_ENTREGUE'): number {
  if (tipo === 'AMANHA') {
    const amanha = this.obterDataAmanha();
    return this.entregas.filter(
      entrega => entrega.data_agendada === amanha &&
        !['ENTREGUE', 'CANCELADA'].includes(entrega.status)
    ).length;
  }

  if (['EM_ROTA', 'NAO_ENTREGUE'].includes(tipo)) {
    return this.entregas.filter(entrega => entrega.status === tipo).length;
  }

  return this.contarEntregasPorPrazo(tipo);
}

aplicarIndicadorEntrega(tipo: 'ATRASADA' | 'HOJE' | 'AMANHA' | 'EM_ROTA' | 'NAO_ENTREGUE'): void {
  this.filtroEntregas.status = '';
  this.filtroEntregas.prazo = '';
  this.filtroEntregas.data_agendada = '';

  if (tipo === 'AMANHA') {
    this.filtroEntregas.data_agendada = this.obterDataAmanha();
  } else if (tipo === 'EM_ROTA' || tipo === 'NAO_ENTREGUE') {
    this.filtroEntregas.status = tipo;
  } else {
    this.filtroEntregas.prazo = tipo;
  }

  this.reiniciarPagina('entregas');
}

obterSolicitacoesAprovadas(): any[] {
  return this.solicitacoes.filter(
    solicitacao => solicitacao.status === 'APROVADA' &&
      solicitacao.itens?.some(
        (item: any) => this.obterSaldoItemSolicitacao(item) > 0
      )
  );
}

obterQuantidadeJaPedida(idItemSolicitacao: number): number {
  return this.pedidos
    .filter(pedido => pedido.status !== 'CANCELADO')
    .reduce((total, pedido) => {
    const itens = Array.isArray(pedido.itens) ? pedido.itens : [];
    const quantidadePedido = itens
      .filter((item: any) => item.id_item_solicitacao === idItemSolicitacao)
      .reduce(
        (subtotal: number, item: any) => subtotal + Number(item.quantidade),
        0
      );

    return total + quantidadePedido;
    }, 0);
}

obterSaldoItemSolicitacao(item: any): number {
  return Math.max(
    0,
    Number(item.quantidade) -
      this.obterQuantidadeJaPedida(item.id_item_solicitacao)
  );
}

prepararItensNovoPedido() {
  const solicitacao = this.obterSolicitacaoSelecionada();
  this.itensNovoPedido = (solicitacao?.itens || [])
    .map((item: any) => {
      const saldo = this.obterSaldoItemSolicitacao(item);
      return {
        id_item_solicitacao: item.id_item_solicitacao,
        id_produto: item.id_produto,
        saldo,
        quantidade: saldo
      };
    })
    .filter((item: any) => item.saldo > 0);
}

obterFornecedoresAtivos(): any[] {
  return this.fornecedores.filter(
    fornecedor => fornecedor.ativo
  );
}

obterFornecedoresParaFiltro(): any[] {
  return [...this.fornecedores].sort((a, b) =>
    this.obterNomeFornecedor(a.id_fornecedor).localeCompare(
      this.obterNomeFornecedor(b.id_fornecedor),
      'pt-BR'
    )
  );
}

obterSolicitacaoSelecionada(): any | undefined {
  return this.solicitacoes.find(
    solicitacao => solicitacao.id_solicitacao === this.novoPedido.id_solicitacao
  );
}

criarPedido() {
  this.erroNovoPedido = '';

  if (
    this.novoPedido.id_solicitacao === null ||
    this.novoPedido.id_fornecedor === null ||
    !this.novoPedido.numero_pedido.trim() ||
    !this.novoPedido.data_pedido
  ) {
    this.erroNovoPedido = 'Preencha todos os campos obrigatórios.';
    return;
  }

  if (this.novoPedido.numero_pedido.trim().length > 30) {
    this.erroNovoPedido = 'O número do pedido deve ter no máximo 30 caracteres.';
    return;
  }

  if (!this.dataIsoValida(this.novoPedido.data_pedido)) {
    this.erroNovoPedido = 'Informe uma data válida para o pedido.';
    return;
  }

  if (this.novoPedido.data_pedido > this.formatarDataHoje()) {
    this.erroNovoPedido = 'A data do pedido não pode ser futura.';
    return;
  }

  const itensSelecionados = this.itensNovoPedido.filter(
    item => Number(item.quantidade) > 0
  );

  if (!itensSelecionados.length) {
    this.erroNovoPedido = 'Informe a quantidade de pelo menos um produto.';
    return;
  }

  const itemInvalido = itensSelecionados.find(
    item => !Number.isFinite(Number(item.quantidade)) ||
      Number(item.quantidade) > Number(item.saldo)
  );

  if (itemInvalido) {
    this.erroNovoPedido = 'A quantidade informada ultrapassa o saldo da solicitação.';
    return;
  }

  const token = localStorage.getItem('token');
  const dados = {
    id_solicitacao: this.novoPedido.id_solicitacao,
    id_fornecedor: this.novoPedido.id_fornecedor,
    numero_pedido: this.novoPedido.numero_pedido.trim(),
    data_pedido: this.novoPedido.data_pedido,
    observacao: this.novoPedido.observacao.trim() || null,
    itens: itensSelecionados.map(item => ({
      id_item_solicitacao: item.id_item_solicitacao,
      quantidade: Number(item.quantidade)
    }))
  };

  this.criandoPedido = true;

  this.http.post<any>(this.urlApi('/pedidos/'), dados, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (resposta) => {
      this.descartarRascunho('pedido');
      this.novoPedido = {
        id_solicitacao: null,
        id_fornecedor: null,
        numero_pedido: '',
        data_pedido: this.formatarDataHoje(),
        observacao: ''
      };
      this.itensNovoPedido = [];
      this.criandoPedido = false;
      this.telaAtual = 'pedidos';
      window.history.pushState({ tela: 'pedidos' }, '', '/sistema?tela=pedidos');
      this.mensagemPedidos = `Pedido ${resposta.numero_pedido} criado com sucesso!`;
      this.carregarPedidos();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao criar pedido:', erro);
      const detalhe = erro.error?.detail;

      this.criandoPedido = false;
      this.erroNovoPedido = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível criar o pedido.';
      this.cdr.detectChanges();
    }
  });
}

enviarPedidoParaRecebimento(idPedidoCompra: number) {
  const token = localStorage.getItem('token');

  this.erroAcaoPedidos = '';
  this.mensagemPedidos = '';
  this.pedidoEmAtualizacao = idPedidoCompra;

  this.http.patch<any>(
    this.urlApi(`/pedidos/${idPedidoCompra}/aguardando-recebimento`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (pedido) => {
      this.pedidoEmAtualizacao = null;
      this.mensagemPedidos = `Pedido ${pedido.numero_pedido} enviado para recebimento.`;
      this.carregarPedidos();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao enviar pedido para recebimento:', erro);
      const detalhe = erro.error?.detail;

      this.pedidoEmAtualizacao = null;
      this.erroAcaoPedidos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível enviar o pedido para recebimento.';
      this.cdr.detectChanges();
    }
  });
}

pedidoPodeSerCancelado(pedido: any): boolean {
  return ['CRIADO', 'AGUARDANDO_RECEBIMENTO'].includes(pedido.status);
}

solicitarCancelamentoPedido(idPedidoCompra: number) {
  this.desistirEdicaoPedido();
  this.pedidoEmCancelamento = idPedidoCompra;
  this.motivoCancelamentoPedido = '';
  this.erroAcaoPedidos = '';
  this.mensagemPedidos = '';
}

desistirCancelamentoPedido() {
  this.pedidoEmCancelamento = null;
  this.motivoCancelamentoPedido = '';
}

confirmarCancelamentoPedido(pedido: any) {
  const motivo = this.motivoCancelamentoPedido.trim();
  if (motivo.length < 3) {
    this.erroAcaoPedidos = 'Informe um motivo com pelo menos 3 caracteres.';
    return;
  }
  if (motivo.length > 500) {
    this.erroAcaoPedidos = 'O motivo deve possuir no máximo 500 caracteres.';
    return;
  }

  const token = localStorage.getItem('token');
  this.pedidoEmAtualizacao = pedido.id_pedido_compra;
  this.erroAcaoPedidos = '';

  this.http.patch<any>(
    this.urlApi(`/pedidos/${pedido.id_pedido_compra}/cancelar`),
    { motivo },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.pedidoEmAtualizacao = null;
      this.pedidoEmCancelamento = null;
      this.motivoCancelamentoPedido = '';
      this.mensagemPedidos = `Pedido ${pedido.numero_pedido} cancelado com sucesso.`;
      this.carregarPedidos();
      if (this.pedidoHistoricoSelecionado === pedido.id_pedido_compra) {
        this.carregarHistoricoPedido(pedido.id_pedido_compra);
      }
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.pedidoEmAtualizacao = null;
      this.erroAcaoPedidos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível cancelar o pedido.';
      this.cdr.detectChanges();
    }
  });
}

carregarRecebimentos() {
  const token = localStorage.getItem('token');
  const opcoes = {
    headers: {
      Authorization: `Bearer ${token}`
    }
  };

  this.carregandoRecebimentos = true;
  this.erroRecebimentos = '';
  this.pedidoRecebimentoSelecionado = null;
  this.detalhePedidoRecebimento = null;
  this.itensNovoRecebimento = [];
  this.avisoItensRecebimento = '';

  forkJoin({
    pedidos: this.http.get<any[]>(this.urlApi('/pedidos/'), opcoes),
    recebimentos: this.http.get<any[]>(this.urlApi('/recebimentos/'), opcoes),
    fornecedores: this.http.get<any[]>(this.urlApi('/fornecedores/'), opcoes),
    produtos: this.http.get<any[]>(this.urlApi('/produtos/'), opcoes)
  }).subscribe({
    next: (resposta) => {
      this.pedidos = resposta.pedidos;
      this.recebimentos = resposta.recebimentos;
      this.fornecedores = resposta.fornecedores;
      this.produtos = resposta.produtos;
      this.carregandoRecebimentos = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar recebimentos:', erro);
      this.carregandoRecebimentos = false;
      this.erroRecebimentos = erro.status === 403
        ? 'Seu perfil não possui permissão para registrar recebimentos.'
        : 'Não foi possível carregar os dados de recebimento.';
      this.cdr.detectChanges();
    }
  });
}

obterPedidosDisponiveisRecebimento(): any[] {
  return this.pedidos.filter(pedido =>
    ['AGUARDANDO_RECEBIMENTO', 'RECEBIDO_PARCIAL'].includes(pedido.status)
  );
}

obterPedidosComStatusRecebimento(): any[] {
  return this.pedidos.filter(pedido =>
    [
      'AGUARDANDO_RECEBIMENTO',
      'RECEBIDO_PARCIAL',
      'RECEBIDO_TOTAL'
    ].includes(pedido.status)
  );
}

selecionarAbaRecebimentos(aba: 'pendentes' | 'historico'): void {
  this.abaRecebimentos = aba;
  this.erroRecebimentos = '';
  if (aba === 'pendentes') this.desistirEstornoRecebimento();
  this.salvarEstadoNavegacao();
}

selecionarPedidoParaRecebimento(idPedidoCompra: number): void {
  const pedido = this.obterPedidosDisponiveisRecebimento().find(
    item => item.id_pedido_compra === idPedidoCompra
  );
  if (!pedido || !this.pedidoTemItensDisponiveisRecebimento(pedido)) {
    this.avisoItensRecebimento = 'Este pedido não possui itens disponíveis para recebimento.';
    return;
  }

  this.pedidoRecebimentoSelecionado = idPedidoCompra;
  this.carregarItensRecebimento();
}

cancelarPreparacaoRecebimento(): void {
  this.pedidoRecebimentoSelecionado = null;
  this.detalhePedidoRecebimento = null;
  this.itensNovoRecebimento = [];
  this.avisoItensRecebimento = '';
  this.erroRecebimentos = '';
  this.novoRecebimento = { numero_nota_fiscal: '', observacao: '' };
}

preencherSaldoItemRecebimento(item: any): void {
  const saldo = Number(item.saldo_pendente);
  item.quantidade_recebida_agora = saldo > 0 ? saldo : null;
}

preencherTodosSaldosRecebimento(): void {
  this.itensNovoRecebimento.forEach(item => this.preencherSaldoItemRecebimento(item));
}

limparQuantidadesRecebimento(): void {
  this.itensNovoRecebimento.forEach(item => item.quantidade_recebida_agora = null);
}

obterQuantidadeItensInformadosRecebimento(): number {
  return this.itensNovoRecebimento.filter(
    item => Number(item.quantidade_recebida_agora) > 0
  ).length;
}

obterTotalRecebimentoAgora(): number {
  return this.itensNovoRecebimento.reduce(
    (total, item) => total + Math.max(0, Number(item.quantidade_recebida_agora) || 0),
    0
  );
}

temQuantidadeRecebimentoInformada(): boolean {
  return this.obterQuantidadeItensInformadosRecebimento() > 0;
}

recebimentoSeraTotal(): boolean {
  const itensPendentes = this.itensNovoRecebimento.filter(
    item => Number(item.saldo_pendente) > 0
  );
  return itensPendentes.length > 0 && itensPendentes.every(
    item => Number(item.quantidade_recebida_agora) >= Number(item.saldo_pendente)
  );
}

obterQuantidadeItensPendentesPedido(pedido: any): number {
  const itens = Array.isArray(pedido?.itens) ? pedido.itens : [];
  return itens.filter((item: any) => Number(item.saldo_pendente) > 0).length;
}

obterSaldoTotalPedido(pedido: any): number {
  const itens = Array.isArray(pedido?.itens) ? pedido.itens : [];
  return itens.reduce(
    (total: number, item: any) => total + Math.max(0, Number(item.saldo_pendente) || 0),
    0
  );
}

pedidoTemItensDisponiveisRecebimento(pedido: any): boolean {
  return this.obterQuantidadeItensPendentesPedido(pedido) > 0 &&
    this.obterSaldoTotalPedido(pedido) > 0;
}

contarPedidosRecebimentoPorStatus(status: string): number {
  return this.obterPedidosDisponiveisRecebimento().filter(
    pedido => pedido.status === status
  ).length;
}

alternarDetalhesRecebimento(idRecebimento: number): void {
  this.recebimentoHistoricoExpandido = this.recebimentoHistoricoExpandido === idRecebimento
    ? null
    : idRecebimento;
}

carregarItensRecebimento() {
  this.erroRecebimentos = '';
  this.avisoItensRecebimento = '';
  this.detalhePedidoRecebimento = null;
  this.itensNovoRecebimento = [];

  if (this.pedidoRecebimentoSelecionado === null) {
    return;
  }

  const token = localStorage.getItem('token');
  this.carregandoItensRecebimento = true;

  this.http.get<any>(
    this.urlApi(`/pedidos/${this.pedidoRecebimentoSelecionado}`),
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (pedido) => {
      this.detalhePedidoRecebimento = pedido;
      const itensPedido = Array.isArray(pedido.itens) ? pedido.itens : [];

      this.itensNovoRecebimento = itensPedido.map((item: any) => ({
        ...item,
        quantidade: Number(item.quantidade),
        quantidade_recebida: Number(item.quantidade_recebida),
        saldo_pendente: Number(item.saldo_pendente),
        quantidade_recebida_agora: null as number | null
      }));

      if (!this.itensNovoRecebimento.length) {
        this.avisoItensRecebimento = `O pedido ${pedido.numero_pedido} não possui itens cadastrados e não pode receber quantidades. Crie um novo pedido a partir de uma solicitação que contenha produtos.`;
      }

      this.carregandoItensRecebimento = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar itens do pedido:', erro);
      const detalhe = erro.error?.detail;

      this.carregandoItensRecebimento = false;
      this.erroRecebimentos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar os itens do pedido.';
      this.cdr.detectChanges();
    }
  });
}

registrarRecebimento() {
  this.erroRecebimentos = '';

  if (this.pedidoRecebimentoSelecionado === null) {
    this.erroRecebimentos = 'Selecione um pedido.';
    return;
  }

  const itensInformados = this.itensNovoRecebimento.filter(
    item => Number(item.quantidade_recebida_agora) > 0
  );

  if (!itensInformados.length) {
    this.erroRecebimentos = 'Informe uma quantidade para pelo menos um item.';
    return;
  }

  const itemAcimaDoSaldo = itensInformados.find(
    item => Number(item.quantidade_recebida_agora) > Number(item.saldo_pendente)
  );

  if (itemAcimaDoSaldo) {
    this.erroRecebimentos = `A quantidade de ${this.obterNomeProduto(itemAcimaDoSaldo.id_produto)} ultrapassa o saldo pendente.`;
    return;
  }

  if (this.novoRecebimento.numero_nota_fiscal.trim().length > 30) {
    this.erroRecebimentos = 'O número da nota fiscal deve ter no máximo 30 caracteres.';
    return;
  }

  const token = localStorage.getItem('token');
  const dados = {
    id_pedido_compra: this.pedidoRecebimentoSelecionado,
    numero_nota_fiscal: this.novoRecebimento.numero_nota_fiscal.trim() || null,
    observacao: this.novoRecebimento.observacao.trim() || null,
    itens: itensInformados.map(item => ({
      id_item_pedido: item.id_item_pedido,
      quantidade_recebida: Number(item.quantidade_recebida_agora)
    }))
  };

  this.registrandoRecebimento = true;

  this.http.post<any>(this.urlApi('/recebimentos/'), dados, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (recebimento) => {
      this.registrandoRecebimento = false;
      this.novoRecebimento = {
        numero_nota_fiscal: '',
        observacao: ''
      };
      this.mensagemRecebimentos = `Recebimento #${recebimento.id_recebimento} registrado com sucesso!`;
      this.carregarRecebimentos();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao registrar recebimento:', erro);
      const detalhe = erro.error?.detail;

      this.registrandoRecebimento = false;
      this.erroRecebimentos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível registrar o recebimento.';
      this.cdr.detectChanges();
    }
  });
}

obterNumeroPedidoRecebimento(idPedidoCompra: number): string {
  const pedido = this.pedidos.find(
    item => item.id_pedido_compra === idPedidoCompra
  );
  return pedido?.numero_pedido || `#${idPedidoCompra}`;
}

podeEstornarRecebimento(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

abrirEstornoRecebimento(idRecebimento: number) {
  this.recebimentoHistoricoExpandido = idRecebimento;
  this.recebimentoEmEstorno = idRecebimento;
  this.motivoEstornoRecebimento = '';
  this.erroRecebimentos = '';
  this.mensagemRecebimentos = '';
}

desistirEstornoRecebimento() {
  this.recebimentoEmEstorno = null;
  this.motivoEstornoRecebimento = '';
}

confirmarEstornoRecebimento(recebimento: any) {
  const motivo = this.motivoEstornoRecebimento.trim();
  if (motivo.length < 3) {
    this.erroRecebimentos = 'Informe o motivo do estorno.';
    return;
  }

  const token = localStorage.getItem('token');
  this.recebimentoEmAtualizacao = recebimento.id_recebimento;
  this.erroRecebimentos = '';

  this.http.patch<any>(
    this.urlApi(`/recebimentos/${recebimento.id_recebimento}/estornar`),
    { motivo },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.recebimentoEmAtualizacao = null;
      this.recebimentoEmEstorno = null;
      this.motivoEstornoRecebimento = '';
      this.mensagemRecebimentos = `Recebimento #${recebimento.id_recebimento} estornado com sucesso.`;
      this.carregarRecebimentos();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.recebimentoEmAtualizacao = null;
      this.erroRecebimentos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível estornar o recebimento.';
      this.cdr.detectChanges();
    }
  });
}

carregarEntregas() {
  const token = localStorage.getItem('token');
  const opcoes = {
    headers: {
      Authorization: `Bearer ${token}`
    }
  };

  this.carregandoEntregas = true;
  this.erroEntregas = '';

  forkJoin({
    entregas: this.http.get<any[]>(this.urlApi('/entregas/'), opcoes),
    clientes: this.http.get<any[]>(this.urlApi('/clientes/'), opcoes),
    usuarios: this.http.get<any[]>(this.urlApi('/usuarios/resumo/'), opcoes)
  }).subscribe({
    next: (resposta) => {
      this.entregas = resposta.entregas;
      this.clientes = resposta.clientes;
      this.usuariosResumo = resposta.usuarios;
      this.entregadoresSelecionados = {};
      this.datasAgendamentoSelecionadas = {};

      for (const entrega of this.entregas) {
        this.entregadoresSelecionados[entrega.id_entrega] = entrega.id_entregador;
        this.datasAgendamentoSelecionadas[entrega.id_entrega] = entrega.data_agendada || '';
      }

      this.carregandoEntregas = false;
      if (this.resultadoBuscaPendente?.tipo === 'entrega') {
        const entrega = this.entregas.find(
          item => item.id_entrega === this.resultadoBuscaPendente?.id
        );
        this.resultadoBuscaPendente = null;
        if (entrega) this.abrirPainelDetalhes('entrega', entrega);
      }
      if (this.telaAtual === 'minhas-entregas') this.carregarResumoMinhasEntregas();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar entregas:', erro);
      this.carregandoEntregas = false;
      this.erroEntregas = 'Não foi possível carregar as entregas.';
      this.cdr.detectChanges();
    }
  });
}

obterClientesAtivos(): any[] {
  return this.clientes.filter(cliente => cliente.ativo);
}

obterEntregadoresAtivos(): any[] {
  return this.usuariosResumo.filter(
    usuario => usuario.perfil === 'ENTREGADOR' && usuario.ativo
  );
}

obterEntregadoresParaFiltro(): any[] {
  return this.usuariosResumo
    .filter(usuario => usuario.perfil === 'ENTREGADOR')
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

obterNomeCliente(idCliente: number): string {
  const cliente = this.clientes.find(item => item.id_cliente === idCliente);
  return cliente ? cliente.nome : `Cliente #${idCliente}`;
}

obterEnderecoCliente(idCliente: number): string {
  const cliente = this.clientes.find(item => item.id_cliente === idCliente);
  if (!cliente) {
    return 'Não informado';
  }

  const logradouro = [cliente.endereco, cliente.numero]
    .filter(Boolean)
    .join(', ');
  const cidade = [cliente.cidade, cliente.uf]
    .filter(Boolean)
    .join('/');

  return [logradouro, cliente.bairro, cidade]
    .filter(Boolean)
    .join(' - ') || 'Não informado';
}

obterTelefoneCliente(idCliente: number): string | null {
  const cliente = this.clientes.find(item => item.id_cliente === idCliente);
  return cliente?.telefone ? this.formatarTelefone(cliente.telefone) : null;
}

obterLinkTelefoneCliente(idCliente: number): string | null {
  const cliente = this.clientes.find(item => item.id_cliente === idCliente);
  const telefone = String(cliente?.telefone ?? '').replace(/\D/g, '');
  return telefone ? `tel:${telefone}` : null;
}

obterLinkMapaCliente(idCliente: number): string | null {
  const endereco = this.obterEnderecoCliente(idCliente);
  return endereco === 'Não informado'
    ? null
    : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`;
}

obterNomeUsuario(idUsuario: number | null): string {
  if (idUsuario === null) {
    return 'Não definido';
  }

  const usuario = this.usuariosResumo.find(
    item => item.id_usuario === idUsuario
  );

  return usuario ? usuario.nome : `Usuário #${idUsuario}`;
}

podeGerenciarPreparacaoEntrega(): boolean {
  return ['FUNCIONARIO', 'ESTOQUE', 'ADMINISTRADOR'].includes(this.perfilUsuario);
}

podeMovimentarEntregaEmRota(): boolean {
  return ['ENTREGADOR', 'ADMINISTRADOR'].includes(this.perfilUsuario);
}

podeCadastrarEntrega(): boolean {
  return this.podeGerenciarPreparacaoEntrega();
}

podeEditarEntrega(entrega: any): boolean {
  return this.podeGerenciarPreparacaoEntrega() && [
    'CADASTRADA',
    'AGENDADA',
    'EM_SEPARACAO',
    'PRONTA_PARA_ENTREGA'
  ].includes(entrega.status);
}

abrirEdicaoEntrega(entrega: any) {
  this.entregaEmEdicaoId = entrega.id_entrega;
  this.formularioEdicaoEntrega = {
    id_cliente: entrega.id_cliente,
    id_entregador: entrega.id_entregador,
    data_agendada: entrega.data_agendada || '',
    observacao: entrega.observacao || ''
  };
  this.erroEdicaoEntrega = '';
  this.erroEntregas = '';
  this.entregaEmCancelamento = null;
  this.entregaEmNaoEntrega = null;
}

desistirEdicaoEntrega() {
  this.entregaEmEdicaoId = null;
  this.salvandoEdicaoEntrega = false;
  this.erroEdicaoEntrega = '';
}

salvarEdicaoEntrega(entrega: any) {
  const formulario = this.formularioEdicaoEntrega;
  if (formulario.id_cliente === null) {
    this.erroEdicaoEntrega = 'Selecione um cliente.';
    return;
  }
  if (
    formulario.data_agendada &&
    (
      !this.dataIsoValida(formulario.data_agendada) ||
      formulario.data_agendada < this.formatarDataHoje()
    )
  ) {
    this.erroEdicaoEntrega = 'Informe uma data atual ou futura.';
    return;
  }
  if (entrega.status !== 'CADASTRADA' && !formulario.data_agendada) {
    this.erroEdicaoEntrega = 'A data agendada é obrigatória nesta etapa.';
    return;
  }

  const token = localStorage.getItem('token');
  this.salvandoEdicaoEntrega = true;
  this.erroEdicaoEntrega = '';
  this.http.put<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}`),
    {
      id_cliente: formulario.id_cliente,
      id_entregador: formulario.id_entregador,
      data_agendada: formulario.data_agendada || null,
      observacao: formulario.observacao.trim() || null
    },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.desistirEdicaoEntrega();
      this.mensagemEntregas = `Entrega #${entrega.id_entrega} atualizada com sucesso.`;
      this.carregarEntregas();
      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.salvandoEdicaoEntrega = false;
      this.erroEdicaoEntrega = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível editar a entrega.';
      this.cdr.detectChanges();
    }
  });
}

podeAlterarAgendamentoEntrega(entrega: any): boolean {
  return this.podeGerenciarPreparacaoEntrega() && [
    'CADASTRADA',
    'AGENDADA',
    'EM_SEPARACAO',
    'PRONTA_PARA_ENTREGA',
    'NAO_ENTREGUE'
  ].includes(entrega.status);
}

podeConfirmarAgendamentoEntrega(entrega: any): boolean {
  const dataAgendada = this.datasAgendamentoSelecionadas[entrega.id_entrega];

  if (
    this.entregaEmAtualizacao === entrega.id_entrega ||
    !this.podeAlterarAgendamentoEntrega(entrega) ||
    !dataAgendada ||
    !this.dataIsoValida(dataAgendada) ||
    dataAgendada < this.formatarDataHoje()
  ) {
    return false;
  }

  return ['CADASTRADA', 'NAO_ENTREGUE'].includes(entrega.status) ||
    dataAgendada !== entrega.data_agendada;
}

salvarAgendamentoEntrega(entrega: any) {
  if (!this.podeAlterarAgendamentoEntrega(entrega)) {
    this.erroEntregas = 'Não é possível alterar o agendamento nesta etapa da entrega.';
    return;
  }

  const dataAgendada = this.datasAgendamentoSelecionadas[entrega.id_entrega];
  if (!dataAgendada || !this.dataIsoValida(dataAgendada)) {
    this.erroEntregas = 'Informe uma data de agendamento válida.';
    return;
  }

  if (dataAgendada < this.formatarDataHoje()) {
    this.erroEntregas = 'A data agendada não pode ser anterior à data atual.';
    return;
  }

  if (
    !['CADASTRADA', 'NAO_ENTREGUE'].includes(entrega.status) &&
    dataAgendada === entrega.data_agendada
  ) {
    this.erroEntregas = 'Selecione uma nova data para reagendar a entrega.';
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.http.patch<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}/agendamento`),
    { data_agendada: dataAgendada },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (entregaAtualizada) => {
      this.entregaEmAtualizacao = null;
      this.fecharFormularioAuxiliarEntrega();
      const operacao = entrega.status === 'CADASTRADA' ? 'agendada' : 'reagendada';
      this.mensagemEntregas = `Entrega #${entrega.id_entrega} ${operacao} para ${this.formatarDataBrasileira(entregaAtualizada.data_agendada)}.`;
      this.carregarEntregas();

      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.entregaEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível atualizar o agendamento.';
      this.cdr.detectChanges();
    }
  });
}

podeCancelarEntrega(entrega: any): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR' && [
    'CADASTRADA',
    'AGENDADA',
    'EM_SEPARACAO',
    'PRONTA_PARA_ENTREGA',
    'NAO_ENTREGUE'
  ].includes(entrega.status);
}

abrirCancelamentoEntrega(idEntrega: number) {
  this.desistirEdicaoEntrega();
  this.entregaEmCancelamento = idEntrega;
  this.motivoCancelamentoEntrega = '';
  this.erroEntregas = '';
  this.mensagemEntregas = '';
}

desistirCancelamentoEntrega() {
  this.entregaEmCancelamento = null;
  this.motivoCancelamentoEntrega = '';
}

confirmarCancelamentoEntrega(entrega: any) {
  const motivo = this.motivoCancelamentoEntrega.trim();
  if (motivo.length < 3) {
    this.erroEntregas = 'Informe o motivo do cancelamento.';
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.http.patch<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}/cancelar`),
    { motivo },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.entregaEmAtualizacao = null;
      this.entregaEmCancelamento = null;
      this.motivoCancelamentoEntrega = '';
      this.mensagemEntregas = `Entrega #${entrega.id_entrega} cancelada com sucesso.`;
      this.carregarEntregas();

      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.entregaEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível cancelar a entrega.';
      this.cdr.detectChanges();
    }
  });
}

podeRegistrarNaoEntrega(entrega: any): boolean {
  if (entrega.status !== 'EM_ROTA') {
    return false;
  }

  return this.perfilUsuario === 'ADMINISTRADOR' || (
    this.perfilUsuario === 'ENTREGADOR' &&
    entrega.id_entregador === this.idUsuarioAtual
  );
}

abrirRegistroNaoEntrega(idEntrega: number) {
  this.entregaEmNaoEntrega = idEntrega;
  this.motivoNaoEntrega = '';
  this.erroEntregas = '';
  this.mensagemEntregas = '';
}

desistirRegistroNaoEntrega() {
  this.entregaEmNaoEntrega = null;
  this.motivoNaoEntrega = '';
}

confirmarNaoEntrega(entrega: any) {
  const motivo = this.motivoNaoEntrega.trim();
  if (motivo.length < 3) {
    this.erroEntregas = 'Informe o motivo da entrega não concluída.';
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.http.patch<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}/nao-entregue`),
    { motivo },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.entregaEmAtualizacao = null;
      this.entregaEmNaoEntrega = null;
      this.motivoNaoEntrega = '';
      this.mensagemEntregas = `Tentativa da entrega #${entrega.id_entrega} registrada.`;
      this.carregarEntregas();

      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.entregaEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível registrar a tentativa de entrega.';
      this.cdr.detectChanges();
    }
  });
}

validarArquivoEntrega(arquivo: File): string {
  const extensao = arquivo.name.split('.').pop()?.toLowerCase();
  const extensoesPermitidas = ['pdf', 'png', 'jpg', 'jpeg', 'webp'];

  if (!extensao || !extensoesPermitidas.includes(extensao)) {
    return 'Formato inválido. Selecione um arquivo PDF, PNG, JPG ou WEBP.';
  }

  if (arquivo.size > 5 * 1024 * 1024) {
    return 'O arquivo deve possuir no máximo 5 MB.';
  }

  return '';
}

selecionarArquivoNovaEntrega(evento: Event) {
  const campo = evento.target as HTMLInputElement;
  const arquivo = campo.files?.[0] || null;

  this.erroNovaEntrega = '';
  this.arquivoNovaEntrega = null;

  if (!arquivo) {
    return;
  }

  const erro = this.validarArquivoEntrega(arquivo);
  if (erro) {
    this.erroNovaEntrega = erro;
    campo.value = '';
    return;
  }

  this.arquivoNovaEntrega = arquivo;
}

enviarArquivoEntrega(arquivo: File) {
  const token = localStorage.getItem('token');

  return this.http.post<any>(
    this.urlApi('/arquivos/entregas'),
    arquivo,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': arquivo.type || 'application/octet-stream',
        'X-Nome-Arquivo': encodeURIComponent(arquivo.name)
      }
    }
  );
}

criarEntrega() {
  this.erroNovaEntrega = '';

  if (this.novaEntrega.id_cliente === null) {
    this.erroNovaEntrega = 'Selecione um cliente.';
    return;
  }

  if (
    this.novaEntrega.data_agendada &&
    !this.dataIsoValida(this.novaEntrega.data_agendada)
  ) {
    this.erroNovaEntrega = 'Informe uma data de agendamento válida.';
    return;
  }

  if (
    this.novaEntrega.data_agendada &&
    this.novaEntrega.data_agendada < this.formatarDataHoje()
  ) {
    this.erroNovaEntrega = 'A data agendada não pode ser anterior à data atual.';
    return;
  }

  if (
    this.novaEntrega.id_entregador !== null &&
    (
      !this.novaEntrega.data_agendada ||
      (!this.novaEntrega.anexo_pedido.trim() && !this.arquivoNovaEntrega)
    )
  ) {
    this.erroNovaEntrega = 'Ao definir um entregador, informe a data e o anexo do pedido.';
    return;
  }

  const dados = {
    id_cliente: this.novaEntrega.id_cliente,
    id_entregador: this.novaEntrega.id_entregador,
    data_agendada: this.novaEntrega.data_agendada || null,
    anexo_pedido: this.novaEntrega.anexo_pedido.trim() || null,
    observacao: this.novaEntrega.observacao.trim() || null
  };

  this.criandoEntrega = true;

  if (this.arquivoNovaEntrega) {
    this.enviandoArquivoEntrega = true;

    this.enviarArquivoEntrega(this.arquivoNovaEntrega).subscribe({
      next: (arquivo) => {
        this.enviandoArquivoEntrega = false;
        dados.anexo_pedido = arquivo.url;
        this.registrarNovaEntrega(dados);
      },

      error: (erro) => {
        console.error('Erro ao enviar anexo da entrega:', erro);
        const detalhe = erro.error?.detail;

        this.criandoEntrega = false;
        this.enviandoArquivoEntrega = false;
        this.erroNovaEntrega = typeof detalhe === 'string'
          ? detalhe
          : 'Não foi possível enviar o anexo da entrega.';
        this.cdr.detectChanges();
      }
    });
    return;
  }

  this.registrarNovaEntrega(dados);
}

novaEntregaSeraAgendada(): boolean {
  const dataAgendada = this.novaEntrega.data_agendada;
  return Boolean(
    dataAgendada &&
    this.dataIsoValida(dataAgendada) &&
    dataAgendada >= this.formatarDataHoje()
  );
}

registrarNovaEntrega(dados: any) {
  const token = localStorage.getItem('token');

  this.http.post<any>(this.urlApi('/entregas/'), dados, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (entrega) => {
      this.descartarRascunho('entrega');
      this.criandoEntrega = false;
      this.arquivoNovaEntrega = null;
      this.novaEntrega = {
        id_cliente: null,
        id_entregador: null,
        data_agendada: '',
        anexo_pedido: '',
        observacao: ''
      };
      this.telaAtual = 'entregas';
      window.history.pushState({ tela: 'entregas' }, '', '/sistema?tela=entregas');
      this.filtroEntregas = {
        busca: '',
        status: entrega.status,
        prazo: '',
        entregador: '',
        data_agendada: '',
        ordem: 'recentes'
      };
      this.reiniciarPagina('entregas');
      this.mensagemEntregas = entrega.status === 'AGENDADA'
        ? `Entrega #${entrega.id_entrega} cadastrada e agendada com sucesso!`
        : `Entrega #${entrega.id_entrega} cadastrada com sucesso!`;
      this.carregarEntregas();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao criar entrega:', erro);
      const detalhe = erro.error?.detail;

      this.criandoEntrega = false;
      this.erroNovaEntrega = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível cadastrar a entrega.';
      this.cdr.detectChanges();
    }
  });
}

atribuirEntregador(entrega: any) {
  const idEntregador = this.entregadoresSelecionados[entrega.id_entrega];

  if (idEntregador === null || idEntregador === undefined) {
    this.erroEntregas = 'Selecione um entregador.';
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.http.patch<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}/atribuir-entregador`),
    { id_entregador: idEntregador },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: () => {
      this.entregaEmAtualizacao = null;
      this.fecharFormularioAuxiliarEntrega();
      this.mensagemEntregas = `Entregador da entrega #${entrega.id_entrega} atualizado com sucesso.`;
      this.carregarEntregas();

      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao atribuir entregador:', erro);
      const detalhe = erro.error?.detail;

      this.entregaEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível atribuir o entregador.';
      this.cdr.detectChanges();
    }
  });
}

obterAcaoEntrega(statusEntrega: string): { endpoint: string; rotulo: string } | null {
  const acoes: Record<string, { endpoint: string; rotulo: string }> = {
    AGENDADA: { endpoint: 'iniciar-separacao', rotulo: 'Iniciar separação' },
    EM_SEPARACAO: { endpoint: 'pronta', rotulo: 'Marcar como pronta' },
    PRONTA_PARA_ENTREGA: { endpoint: 'em-rota', rotulo: 'Iniciar rota' },
    EM_ROTA: { endpoint: 'entregue', rotulo: 'Marcar como entregue' }
  };

  return acoes[statusEntrega] || null;
}

podeAvancarEntrega(statusEntrega: string): boolean {
  if (['AGENDADA', 'EM_SEPARACAO'].includes(statusEntrega)) {
    return this.podeGerenciarPreparacaoEntrega();
  }

  if (['PRONTA_PARA_ENTREGA', 'EM_ROTA'].includes(statusEntrega)) {
    return this.podeMovimentarEntregaEmRota();
  }

  return false;
}

avancarEntrega(entrega: any) {
  const acao = this.obterAcaoEntrega(entrega.status);

  if (!acao) {
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.http.patch<any>(
    this.urlApi(`/entregas/${entrega.id_entrega}/${acao.endpoint}`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (entregaAtualizada) => {
      this.entregaEmAtualizacao = null;
      const mensagens: Record<string, string> = {
        EM_SEPARACAO: `Entrega #${entrega.id_entrega} enviada para separação.`,
        PRONTA_PARA_ENTREGA: `Entrega #${entrega.id_entrega} marcada como pronta.`,
        EM_ROTA: `Entrega #${entrega.id_entrega} colocada em rota.`,
        ENTREGUE: `Entrega #${entrega.id_entrega} concluída com sucesso.`
      };
      this.mensagemEntregas = mensagens[entregaAtualizada.status] ||
        `Entrega #${entrega.id_entrega} atualizada com sucesso.`;
      this.carregarEntregas();

      if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
        this.carregarHistoricoEntrega(entrega.id_entrega);
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao atualizar entrega:', erro);
      const detalhe = erro.error?.detail;

      this.entregaEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível atualizar a entrega.';
      this.cdr.detectChanges();
    }
  });
}

alternarHistoricoEntrega(idEntrega: number) {
  if (this.entregaHistoricoSelecionada === idEntrega) {
    this.entregaHistoricoSelecionada = null;
    this.historicoEntrega = [];
    this.erroHistoricoEntrega = '';
    return;
  }

  this.entregaHistoricoSelecionada = idEntrega;
  this.historicoEntrega = [];
  this.carregarHistoricoEntrega(idEntrega);
}

carregarHistoricoEntrega(idEntrega: number) {
  const token = localStorage.getItem('token');

  this.carregandoHistoricoEntrega = true;
  this.erroHistoricoEntrega = '';

  this.http.get<any[]>(
    this.urlApi(`/entregas/${idEntrega}/historico`),
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (historico) => {
      if (this.entregaHistoricoSelecionada === idEntrega) {
        this.historicoEntrega = historico;
      }

      this.carregandoHistoricoEntrega = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar histórico da entrega:', erro);
      const detalhe = erro.error?.detail;

      this.carregandoHistoricoEntrega = false;
      this.erroHistoricoEntrega = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar o histórico da entrega.';
      this.cdr.detectChanges();
    }
  });
}

formatarAcaoHistorico(acao: string): string {
  const nomes: Record<string, string> = {
    CADASTRO: 'Entrega cadastrada',
    EDICAO: 'Entrega editada',
    AGENDAMENTO: 'Entrega agendada',
    REAGENDAMENTO: 'Entrega reagendada',
    NAO_ENTREGA: 'Entrega não concluída',
    ALTERACAO_STATUS: 'Alteração de status',
    ATRIBUICAO_ENTREGADOR: 'Entregador atribuído',
    ANEXO_COMPROVANTE: 'Comprovante anexado',
    CANCELAMENTO: 'Entrega cancelada'
  };

  return nomes[acao] || acao.replaceAll('_', ' ');
}

anexoEhLink(anexo: string): boolean {
  return /^https?:\/\//i.test(anexo);
}

anexoEhArquivoInterno(anexo: string): boolean {
  return anexo.startsWith('/arquivos/entregas/');
}

obterNomeArquivo(anexo: string): string {
  return decodeURIComponent(anexo.split('/').pop() || 'arquivo-entrega');
}

podePreVisualizarAnexo(anexo: string): boolean {
  const nome = this.obterNomeArquivo(anexo).toLowerCase().split('?')[0];
  return this.anexoEhArquivoInterno(anexo) && /\.(png|jpe?g|webp)$/.test(nome);
}

visualizarArquivoEntrega(anexo: string, idEntrega: number): void {
  if (!this.podePreVisualizarAnexo(anexo)) {
    return;
  }

  const token = localStorage.getItem('token');
  this.anexoPreVisualizacaoCarregando = idEntrega;
  this.erroEntregas = '';

  this.http.get(this.urlApi(anexo), {
    headers: { Authorization: `Bearer ${token}` },
    responseType: 'blob'
  }).subscribe({
    next: arquivo => {
      this.liberarUrlPreVisualizacao();
      this.anexoPreVisualizacaoUrl = URL.createObjectURL(arquivo);
      this.anexoPreVisualizacaoNome = this.obterNomeArquivo(anexo);
      this.anexoPreVisualizacaoCarregando = null;
      this.cdr.detectChanges();
    },
    error: () => {
      this.anexoPreVisualizacaoCarregando = null;
      this.erroEntregas = 'Não foi possível visualizar o anexo da entrega.';
      this.cdr.detectChanges();
    }
  });
}

carregarResumoMinhasEntregas(): void {
  if (this.perfilUsuario !== 'ENTREGADOR') return;
  const token = localStorage.getItem('token');
  this.http.get<any>(this.urlApi('/entregas/minhas-resumo'), {
    headers: { Authorization: `Bearer ${token}` }
  }).subscribe({
    next: resumo => {
      this.resumoMinhasEntregas = resumo;
      this.cdr.detectChanges();
    },
    error: () => {
      this.resumoMinhasEntregas = {
        hoje: this.contarAbaMinhasEntregas('hoje'),
        em_rota: this.entregas.filter(item => item.status === 'EM_ROTA').length,
        pendentes: this.entregas.filter(item => !['ENTREGUE', 'CANCELADA'].includes(item.status)).length,
        concluidas_hoje: 0
      };
    }
  });
}

selecionarAbaMinhasEntregas(aba: AbaMinhasEntregas): void {
  this.abaMinhasEntregas = aba;
  this.salvarEstadoNavegacao();
}

obterMinhasEntregasFiltradas(): any[] {
  const hoje = this.formatarDataHoje();
  const encerradas = ['ENTREGUE', 'CANCELADA'];
  const filtradas = this.entregas.filter(entrega => {
    if (this.abaMinhasEntregas === 'hoje') {
      return entrega.data_agendada === hoje && !encerradas.includes(entrega.status);
    }
    if (this.abaMinhasEntregas === 'proximas') {
      return Boolean(entrega.data_agendada && entrega.data_agendada > hoje) &&
        !encerradas.includes(entrega.status);
    }
    if (this.abaMinhasEntregas === 'andamento') {
      return ['PRONTA_PARA_ENTREGA', 'EM_ROTA', 'NAO_ENTREGUE'].includes(entrega.status);
    }
    return entrega.status === 'ENTREGUE';
  });
  return filtradas.sort((a, b) => {
    const dataA = a.data_agendada || '9999-12-31';
    const dataB = b.data_agendada || '9999-12-31';
    return dataA.localeCompare(dataB) || b.id_entrega - a.id_entrega;
  });
}

contarAbaMinhasEntregas(aba: AbaMinhasEntregas): number {
  const atual = this.abaMinhasEntregas;
  this.abaMinhasEntregas = aba;
  const total = this.obterMinhasEntregasFiltradas().length;
  this.abaMinhasEntregas = atual;
  return total;
}

baixarArquivoPreVisualizado(): void {
  if (!this.anexoPreVisualizacaoUrl) {
    return;
  }

  const link = document.createElement('a');
  link.href = this.anexoPreVisualizacaoUrl;
  link.download = this.anexoPreVisualizacaoNome;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

alterarZoomPreVisualizacao(variacao: number): void {
  this.zoomPreVisualizacao = Math.min(
    3,
    Math.max(0.5, Number((this.zoomPreVisualizacao + variacao).toFixed(1)))
  );
}

fecharPreVisualizacao(): void {
  this.liberarUrlPreVisualizacao();
  this.cdr.detectChanges();
}

private liberarUrlPreVisualizacao(): void {
  if (this.anexoPreVisualizacaoUrl) {
    URL.revokeObjectURL(this.anexoPreVisualizacaoUrl);
  }
  this.anexoPreVisualizacaoUrl = null;
  this.anexoPreVisualizacaoNome = '';
  this.zoomPreVisualizacao = 1;
}

baixarArquivoEntrega(anexo: string, idEntrega: number) {
  const token = localStorage.getItem('token');
  const url = this.anexoEhArquivoInterno(anexo)
    ? this.urlApi(anexo)
    : anexo;

  this.arquivoEntregaEmDownload = idEntrega;
  this.erroEntregas = '';

  this.http.get(url, {
    headers: {
      Authorization: `Bearer ${token}`
    },
    responseType: 'blob'
  }).subscribe({
    next: (arquivo) => {
      const enderecoArquivo = URL.createObjectURL(arquivo);
      const link = document.createElement('a');

      link.href = enderecoArquivo;
      link.download = this.obterNomeArquivo(anexo);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(enderecoArquivo);

      this.arquivoEntregaEmDownload = null;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao baixar arquivo da entrega:', erro);
      this.arquivoEntregaEmDownload = null;
      this.erroEntregas = 'Não foi possível baixar o arquivo da entrega.';
      this.cdr.detectChanges();
    }
  });
}

podeAnexarComprovante(entrega: any): boolean {
  if (!['EM_ROTA', 'ENTREGUE'].includes(entrega.status)) {
    return false;
  }

  return this.perfilUsuario === 'ADMINISTRADOR' || (
    this.perfilUsuario === 'ENTREGADOR' &&
    entrega.id_entregador === this.idUsuarioAtual
  );
}

selecionarComprovanteEntrega(evento: Event, idEntrega: number) {
  const campo = evento.target as HTMLInputElement;
  const arquivo = campo.files?.[0] || null;

  this.erroEntregas = '';
  this.comprovantesSelecionados[idEntrega] = null;

  if (!arquivo) {
    return;
  }

  const erro = this.validarArquivoEntrega(arquivo);
  if (erro) {
    this.erroEntregas = erro;
    campo.value = '';
    return;
  }

  this.comprovantesSelecionados[idEntrega] = arquivo;
}

anexarComprovanteEntrega(entrega: any) {
  const arquivo = this.comprovantesSelecionados[entrega.id_entrega];

  if (!arquivo) {
    this.erroEntregas = 'Selecione o arquivo do comprovante.';
    return;
  }

  const token = localStorage.getItem('token');
  this.entregaComprovanteEmAtualizacao = entrega.id_entrega;
  this.erroEntregas = '';
  this.mensagemEntregas = '';

  this.enviarArquivoEntrega(arquivo).subscribe({
    next: (arquivoEnviado) => {
      this.http.patch<any>(
        this.urlApi(`/entregas/${entrega.id_entrega}/comprovante`),
        { comprovante_entrega: arquivoEnviado.url },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      ).subscribe({
        next: () => {
          this.entregaComprovanteEmAtualizacao = null;
          this.comprovantesSelecionados[entrega.id_entrega] = null;
          this.fecharFormularioAuxiliarEntrega();
          this.mensagemEntregas = `Comprovante anexado à entrega #${entrega.id_entrega}.`;
          this.carregarEntregas();

          if (this.entregaHistoricoSelecionada === entrega.id_entrega) {
            this.carregarHistoricoEntrega(entrega.id_entrega);
          }

          this.cdr.detectChanges();
        },

        error: (erro) => {
          console.error('Erro ao vincular comprovante:', erro);
          const detalhe = erro.error?.detail;

          this.entregaComprovanteEmAtualizacao = null;
          this.erroEntregas = typeof detalhe === 'string'
            ? detalhe
            : 'Não foi possível vincular o comprovante à entrega.';
          this.cdr.detectChanges();
        }
      });
    },

    error: (erro) => {
      console.error('Erro ao enviar comprovante:', erro);
      const detalhe = erro.error?.detail;

      this.entregaComprovanteEmAtualizacao = null;
      this.erroEntregas = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível enviar o comprovante.';
      this.cdr.detectChanges();
    }
  });
}

carregarClientes() {
  const token = localStorage.getItem('token');

  this.carregandoClientes = true;
  this.erroClientes = '';

  this.http.get<any[]>(this.urlApi('/clientes/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (clientes) => {
      this.clientes = clientes;
      this.carregandoClientes = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar clientes:', erro);
      this.carregandoClientes = false;
      this.erroClientes = 'Não foi possível carregar os clientes.';
      this.cdr.detectChanges();
    }
  });
}

podeEditarClientes(): boolean {
  return ['FUNCIONARIO', 'ADMINISTRADOR'].includes(this.perfilUsuario);
}

podeAlterarStatusCliente(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

limparFormularioCliente() {
  this.clienteEmEdicaoId = null;
  this.formularioCliente = {
    nome: '',
    cpf_cnpj: '',
    telefone: '',
    endereco: '',
    numero: '',
    bairro: '',
    cidade: '',
    uf: '',
    observacao: ''
  };
}

abrirNovoCliente() {
  this.limparFormularioCliente();
  this.erroFormularioCliente = '';
  this.telaAtual = 'formulario-cliente';
}

editarCliente(cliente: any) {
  this.clienteEmEdicaoId = cliente.id_cliente;
  this.erroFormularioCliente = '';
  this.formularioCliente = {
    nome: cliente.nome || '',
    cpf_cnpj: this.formatarCpfCnpj(cliente.cpf_cnpj || ''),
    telefone: this.formatarTelefone(cliente.telefone || ''),
    endereco: cliente.endereco || '',
    numero: cliente.numero || '',
    bairro: cliente.bairro || '',
    cidade: cliente.cidade || '',
    uf: cliente.uf || '',
    observacao: cliente.observacao || ''
  };
  this.telaAtual = 'formulario-cliente';
}

salvarCliente() {
  this.erroFormularioCliente = '';

  const cpfCnpj = this.formularioCliente.cpf_cnpj.replace(/\D/g, '');
  const telefone = this.formularioCliente.telefone.replace(/\D/g, '');
  const camposObrigatorios = [
    this.formularioCliente.nome,
    this.formularioCliente.endereco,
    this.formularioCliente.numero,
    this.formularioCliente.bairro,
    this.formularioCliente.cidade,
    this.formularioCliente.uf
  ];

  if (camposObrigatorios.some(campo => !campo.trim())) {
    this.erroFormularioCliente = 'Preencha todos os campos obrigatórios.';
    return;
  }

  if (cpfCnpj && ![11, 14].includes(cpfCnpj.length)) {
    this.erroFormularioCliente = 'O CPF deve ter 11 dígitos ou o CNPJ deve ter 14 dígitos.';
    return;
  }

  if (cpfCnpj && !this.validarCpfCnpj(cpfCnpj)) {
    this.erroFormularioCliente = cpfCnpj.length === 11
      ? 'Informe um CPF válido.'
      : 'Informe um CNPJ válido.';
    return;
  }

  if (telefone && (telefone.length < 10 || telefone.length > 15)) {
    this.erroFormularioCliente = 'O telefone deve ter entre 10 e 15 dígitos.';
    return;
  }

  const token = localStorage.getItem('token');
  const editando = this.clienteEmEdicaoId !== null;
  const url = editando
    ? this.urlApi(`/clientes/${this.clienteEmEdicaoId}`)
    : this.urlApi('/clientes/');
  const dados = {
    nome: this.formularioCliente.nome.trim(),
    cpf_cnpj: cpfCnpj || null,
    telefone: telefone || null,
    endereco: this.formularioCliente.endereco.trim(),
    numero: this.formularioCliente.numero.trim(),
    bairro: this.formularioCliente.bairro.trim(),
    cidade: this.formularioCliente.cidade.trim(),
    uf: this.formularioCliente.uf.trim().toUpperCase(),
    observacao: this.formularioCliente.observacao.trim() || null
  };

  this.salvandoCliente = true;

  this.http.request<any>(editando ? 'PUT' : 'POST', url, {
    body: dados,
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (cliente) => {
      this.salvandoCliente = false;
      this.telaAtual = 'clientes';
      this.mensagemClientes = editando
        ? `Cliente ${cliente.nome} atualizado com sucesso!`
        : `Cliente ${cliente.nome} cadastrado com sucesso!`;
      this.limparFormularioCliente();
      this.carregarClientes();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao salvar cliente:', erro);
      const detalhe = erro.error?.detail;

      this.salvandoCliente = false;
      this.erroFormularioCliente = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível salvar o cliente.';
      this.cdr.detectChanges();
    }
  });
}

alterarStatusCliente(cliente: any) {
  const token = localStorage.getItem('token');
  const acao = cliente.ativo ? 'desativar' : 'ativar';

  this.clienteEmAtualizacao = cliente.id_cliente;
  this.erroClientes = '';
  this.mensagemClientes = '';

  this.http.patch<any>(
    this.urlApi(`/clientes/${cliente.id_cliente}/${acao}`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (clienteAtualizado) => {
      this.clienteEmAtualizacao = null;
      this.mensagemClientes = `Cliente ${clienteAtualizado.nome} ${clienteAtualizado.ativo ? 'ativado' : 'desativado'} com sucesso!`;
      this.carregarClientes();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao alterar status do cliente:', erro);
      const detalhe = erro.error?.detail;

      this.clienteEmAtualizacao = null;
      this.erroClientes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível alterar o status do cliente.';
      this.cdr.detectChanges();
    }
  });
}

carregarUsuarios() {
  const token = localStorage.getItem('token');

  this.carregandoUsuarios = true;
  this.erroUsuarios = '';

  this.http.get<any[]>(this.urlApi('/usuarios/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (usuarios) => {
      this.usuarios = usuarios;
      this.carregandoUsuarios = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar usuários:', erro);
      const detalhe = erro.error?.detail;

      this.carregandoUsuarios = false;
      this.erroUsuarios = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar os usuários.';
      this.cdr.detectChanges();
    }
  });
}

podeGerenciarUsuarios(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

ehUsuarioAtual(usuario: any): boolean {
  return usuario.id_usuario === this.idUsuarioAtual;
}

limparFormularioUsuario() {
  this.usuarioEmEdicaoId = null;
  this.formularioUsuario = {
    nome: '',
    login: '',
    senha: '',
    perfil: 'FUNCIONARIO'
  };
}

abrirNovoUsuario() {
  this.limparFormularioUsuario();
  this.erroFormularioUsuario = '';
  this.telaAtual = 'formulario-usuario';
}

editarUsuario(usuario: any) {
  this.usuarioEmEdicaoId = usuario.id_usuario;
  this.erroFormularioUsuario = '';
  this.formularioUsuario = {
    nome: usuario.nome || '',
    login: usuario.login || '',
    senha: '',
    perfil: usuario.perfil || 'FUNCIONARIO'
  };
  this.telaAtual = 'formulario-usuario';
}

salvarUsuario() {
  this.erroFormularioUsuario = '';

  if (
    !this.formularioUsuario.nome.trim() ||
    !this.formularioUsuario.login.trim() ||
    !this.formularioUsuario.perfil
  ) {
    this.erroFormularioUsuario = 'Preencha todos os campos obrigatórios.';
    return;
  }

  const editando = this.usuarioEmEdicaoId !== null;
  const senha = this.formularioUsuario.senha;

  if ((!editando || senha) && senha.length < 6) {
    this.erroFormularioUsuario = 'A senha deve possuir pelo menos 6 caracteres.';
    return;
  }

  const token = localStorage.getItem('token');
  const url = editando
    ? this.urlApi(`/usuarios/${this.usuarioEmEdicaoId}`)
    : this.urlApi('/usuarios/');
  const dados: any = {
    nome: this.formularioUsuario.nome.trim(),
    login: this.formularioUsuario.login.trim(),
    perfil: this.formularioUsuario.perfil
  };

  if (senha) {
    dados.senha = senha;
  }

  this.salvandoUsuario = true;

  this.http.request<any>(editando ? 'PUT' : 'POST', url, {
    body: dados,
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (usuario) => {
      this.salvandoUsuario = false;
      this.telaAtual = 'usuarios';
      this.mensagemUsuarios = editando
        ? `Usuário ${usuario.nome} atualizado com sucesso!`
        : `Usuário ${usuario.nome} cadastrado com sucesso!`;

      if (usuario.id_usuario === this.idUsuarioAtual) {
        this.login = usuario.login;
      }

      this.limparFormularioUsuario();
      this.carregarUsuarios();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao salvar usuário:', erro);
      const detalhe = erro.error?.detail;

      this.salvandoUsuario = false;
      this.erroFormularioUsuario = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível salvar o usuário.';
      this.cdr.detectChanges();
    }
  });
}

alterarStatusUsuario(usuario: any) {
  if (this.ehUsuarioAtual(usuario)) {
    this.erroUsuarios = 'Você não pode desativar a própria conta.';
    return;
  }

  const token = localStorage.getItem('token');
  const url = usuario.ativo
    ? this.urlApi(`/usuarios/${usuario.id_usuario}/desativar`)
    : this.urlApi(`/usuarios/${usuario.id_usuario}`);

  this.usuarioEmAtualizacao = usuario.id_usuario;
  this.erroUsuarios = '';
  this.mensagemUsuarios = '';

  this.http.request<any>(usuario.ativo ? 'PATCH' : 'PUT', url, {
    body: usuario.ativo ? {} : { ativo: true },
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (usuarioAtualizado) => {
      this.usuarioEmAtualizacao = null;
      this.mensagemUsuarios = `Usuário ${usuarioAtualizado.nome} ${usuarioAtualizado.ativo ? 'ativado' : 'desativado'} com sucesso!`;
      this.carregarUsuarios();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao alterar status do usuário:', erro);
      const detalhe = erro.error?.detail;

      this.usuarioEmAtualizacao = null;
      this.erroUsuarios = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível alterar o status do usuário.';
      this.cdr.detectChanges();
    }
  });
}

carregarFornecedores() {
  const token = localStorage.getItem('token');

  this.carregandoFornecedores = true;
  this.erroFornecedores = '';

  this.http.get<any[]>(this.urlApi('/fornecedores/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (fornecedores) => {
      this.fornecedores = fornecedores;
      this.carregandoFornecedores = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar fornecedores:', erro);
      this.carregandoFornecedores = false;
      this.erroFornecedores = 'Não foi possível carregar os fornecedores.';
      this.cdr.detectChanges();
    }
  });
}

podeGerenciarFornecedores(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

limparFormularioFornecedor() {
  this.fornecedorEmEdicaoId = null;
  this.formularioFornecedor = {
    razao_social: '',
    nome_fantasia: '',
    cnpj: '',
    telefone: '',
    email: ''
  };
}

abrirNovoFornecedor() {
  this.limparFormularioFornecedor();
  this.erroFormularioFornecedor = '';
  this.telaAtual = 'formulario-fornecedor';
}

editarFornecedor(fornecedor: any) {
  this.fornecedorEmEdicaoId = fornecedor.id_fornecedor;
  this.erroFormularioFornecedor = '';
  this.formularioFornecedor = {
    razao_social: fornecedor.razao_social || '',
    nome_fantasia: fornecedor.nome_fantasia || '',
    cnpj: this.formatarCnpj(fornecedor.cnpj || ''),
    telefone: this.formatarTelefone(fornecedor.telefone || ''),
    email: fornecedor.email || ''
  };
  this.telaAtual = 'formulario-fornecedor';
}

salvarFornecedor() {
  this.erroFormularioFornecedor = '';

  const cnpj = this.formularioFornecedor.cnpj.replace(/\D/g, '');
  const telefone = this.formularioFornecedor.telefone.replace(/\D/g, '');

  if (!this.formularioFornecedor.razao_social.trim()) {
    this.erroFormularioFornecedor = 'Informe a razão social.';
    return;
  }

  if (cnpj.length !== 14) {
    this.erroFormularioFornecedor = 'O CNPJ deve ter 14 dígitos.';
    return;
  }

  if (!this.validarCnpj(cnpj)) {
    this.erroFormularioFornecedor = 'Informe um CNPJ válido.';
    return;
  }

  if (telefone && (telefone.length < 10 || telefone.length > 15)) {
    this.erroFormularioFornecedor = 'O telefone deve ter entre 10 e 15 dígitos.';
    return;
  }

  const token = localStorage.getItem('token');
  const editando = this.fornecedorEmEdicaoId !== null;
  const url = editando
    ? this.urlApi(`/fornecedores/${this.fornecedorEmEdicaoId}`)
    : this.urlApi('/fornecedores/');
  const dados = {
    razao_social: this.formularioFornecedor.razao_social.trim(),
    nome_fantasia: this.formularioFornecedor.nome_fantasia.trim() || null,
    cnpj,
    telefone: telefone || null,
    email: this.formularioFornecedor.email.trim() || null
  };

  this.salvandoFornecedor = true;

  this.http.request<any>(editando ? 'PUT' : 'POST', url, {
    body: dados,
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (fornecedor) => {
      this.salvandoFornecedor = false;
      this.telaAtual = 'fornecedores';
      this.mensagemFornecedores = editando
        ? `Fornecedor ${fornecedor.razao_social} atualizado com sucesso!`
        : `Fornecedor ${fornecedor.razao_social} cadastrado com sucesso!`;
      this.limparFormularioFornecedor();
      this.carregarFornecedores();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao salvar fornecedor:', erro);
      const detalhe = erro.error?.detail;

      this.salvandoFornecedor = false;
      this.erroFormularioFornecedor = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível salvar o fornecedor.';
      this.cdr.detectChanges();
    }
  });
}

alterarStatusFornecedor(fornecedor: any) {
  const token = localStorage.getItem('token');
  const acao = fornecedor.ativo ? 'desativar' : 'ativar';

  this.fornecedorEmAtualizacao = fornecedor.id_fornecedor;
  this.erroFornecedores = '';
  this.mensagemFornecedores = '';

  this.http.patch<any>(
    this.urlApi(`/fornecedores/${fornecedor.id_fornecedor}/${acao}`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (fornecedorAtualizado) => {
      this.fornecedorEmAtualizacao = null;
      this.mensagemFornecedores = `Fornecedor ${fornecedorAtualizado.razao_social} ${fornecedorAtualizado.ativo ? 'ativado' : 'desativado'} com sucesso!`;
      this.carregarFornecedores();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao alterar status do fornecedor:', erro);
      const detalhe = erro.error?.detail;

      this.fornecedorEmAtualizacao = null;
      this.erroFornecedores = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível alterar o status do fornecedor.';
      this.cdr.detectChanges();
    }
  });
}

carregarProdutosTela() {
  const token = localStorage.getItem('token');

  this.carregandoProdutosTela = true;
  this.erroProdutos = '';

  this.http.get<any[]>(this.urlApi('/produtos/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (produtos) => {
      this.produtos = produtos;
      this.carregandoProdutosTela = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar produtos:', erro);
      this.carregandoProdutosTela = false;
      this.erroProdutos = 'Não foi possível carregar os produtos.';
      this.cdr.detectChanges();
    }
  });
}

obterProdutosAtivos(): any[] {
  return this.produtos.filter(produto => produto.ativo);
}

podeGerenciarProdutos(): boolean {
  return ['ADMINISTRADOR', 'ESTOQUE'].includes(this.perfilUsuario);
}

podeAlterarStatusProduto(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

limparFormularioProduto() {
  this.produtoEmEdicaoId = null;
  this.formularioProduto = {
    codigo: '',
    nome: '',
    categoria: '',
    marca: '',
    unidade: '',
    descricao: ''
  };
}

abrirNovoProduto() {
  this.limparFormularioProduto();
  this.erroFormularioProduto = '';
  this.telaAtual = 'formulario-produto';
}

editarProduto(produto: any) {
  this.produtoEmEdicaoId = produto.id_produto;
  this.erroFormularioProduto = '';
  this.formularioProduto = {
    codigo: produto.codigo || '',
    nome: produto.nome || '',
    categoria: produto.categoria || '',
    marca: produto.marca || '',
    unidade: produto.unidade || '',
    descricao: produto.descricao || ''
  };
  this.telaAtual = 'formulario-produto';
}

salvarProduto() {
  this.erroFormularioProduto = '';

  const camposObrigatorios = [
    this.formularioProduto.codigo,
    this.formularioProduto.nome,
    this.formularioProduto.categoria,
    this.formularioProduto.marca,
    this.formularioProduto.unidade
  ];

  if (camposObrigatorios.some(campo => !campo.trim())) {
    this.erroFormularioProduto = 'Preencha todos os campos obrigatórios.';
    return;
  }

  const token = localStorage.getItem('token');
  const editando = this.produtoEmEdicaoId !== null;
  const url = editando
    ? this.urlApi(`/produtos/${this.produtoEmEdicaoId}`)
    : this.urlApi('/produtos/');
  const dados = {
    codigo: this.formularioProduto.codigo.trim(),
    nome: this.formularioProduto.nome.trim(),
    categoria: this.formularioProduto.categoria.trim(),
    marca: this.formularioProduto.marca.trim(),
    unidade: this.formularioProduto.unidade.trim(),
    descricao: this.formularioProduto.descricao.trim() || null
  };

  this.salvandoProduto = true;

  this.http.request<any>(editando ? 'PUT' : 'POST', url, {
    body: dados,
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (produto) => {
      this.salvandoProduto = false;
      this.telaAtual = 'produtos';
      this.mensagemProdutos = editando
        ? `Produto ${produto.nome} atualizado com sucesso!`
        : `Produto ${produto.nome} cadastrado com sucesso!`;
      this.limparFormularioProduto();
      this.carregarProdutosTela();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao salvar produto:', erro);
      const detalhe = erro.error?.detail;

      this.salvandoProduto = false;
      this.erroFormularioProduto = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível salvar o produto.';
      this.cdr.detectChanges();
    }
  });
}

alterarStatusProduto(produto: any) {
  const token = localStorage.getItem('token');
  const acao = produto.ativo ? 'desativar' : 'ativar';

  this.produtoEmAtualizacao = produto.id_produto;
  this.erroProdutos = '';
  this.mensagemProdutos = '';

  this.http.patch<any>(
    this.urlApi(`/produtos/${produto.id_produto}/${acao}`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (produtoAtualizado) => {
      this.produtoEmAtualizacao = null;
      this.mensagemProdutos = `Produto ${produtoAtualizado.nome} ${produtoAtualizado.ativo ? 'ativado' : 'desativado'} com sucesso!`;
      this.carregarProdutosTela();
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao alterar status do produto:', erro);
      const detalhe = erro.error?.detail;

      this.produtoEmAtualizacao = null;
      this.erroProdutos = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível alterar o status do produto.';
      this.cdr.detectChanges();
    }
  });
}

carregarNotificacoes(silencioso = false) {
  const token = localStorage.getItem('token');

  if (silencioso && this.atualizandoNotificacoesEmSegundoPlano) {
    return;
  }

  if (!silencioso) {
    this.carregandoNotificacoes = true;
    this.erroNotificacoes = '';
    this.mensagemNotificacoes = '';
  } else {
    this.atualizandoNotificacoesEmSegundoPlano = true;
  }

  this.http.get<any[]>(this.urlApi('/notificacoes/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (notificacoes) => {
      const idsConhecidos = new Set(
        this.notificacoes.map(notificacao => notificacao.id_notificacao)
      );
      const quantidadeNovas = this.notificacoesInicializadas && silencioso
        ? notificacoes.filter(notificacao =>
          !notificacao.lida && !idsConhecidos.has(notificacao.id_notificacao)
        ).length
        : 0;

      this.notificacoes = notificacoes;
      this.notificacoesInicializadas = true;
      this.atualizarTituloNotificacoes();
      this.carregandoNotificacoes = false;
      this.atualizandoNotificacoesEmSegundoPlano = false;
      this.ultimaAtualizacaoNotificacoes = new Date();

      if (quantidadeNovas > 0) {
        this.avisoNovaNotificacao = quantidadeNovas === 1
          ? 'Você recebeu uma nova notificação.'
          : `Você recebeu ${quantidadeNovas} novas notificações.`;
      }

      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar notificações:', erro);
      this.carregandoNotificacoes = false;
      this.atualizandoNotificacoesEmSegundoPlano = false;

      if (!silencioso) {
        this.erroNotificacoes = 'Não foi possível carregar as notificações.';
      }

      this.cdr.detectChanges();
    }
  });
}

iniciarAtualizacaoAutomaticaNotificacoes(): void {
  this.pararAtualizacaoAutomaticaNotificacoes();
  this.atualizacaoNotificacoesId = setInterval(() => {
    if (this.logado) {
      this.carregarNotificacoes(true);
    }
  }, this.intervaloAtualizacaoNotificacoesMs);
}

pararAtualizacaoAutomaticaNotificacoes(): void {
  if (this.atualizacaoNotificacoesId !== null) {
    clearInterval(this.atualizacaoNotificacoesId);
    this.atualizacaoNotificacoesId = null;
  }
  this.atualizandoNotificacoesEmSegundoPlano = false;
}

contarNotificacoesNaoLidas(): number {
  return this.notificacoes.filter(notificacao => !notificacao.lida).length;
}

carregarResumoDashboard(): void {
  const token = localStorage.getItem('token');
  this.carregandoResumoDashboard = true;
  this.erroResumoDashboard = '';

  this.http.get<any>(this.urlApi('/dashboard/resumo'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (resumo) => {
      this.resumoDashboard = resumo;
      this.carregandoResumoDashboard = false;
      this.cdr.detectChanges();
    },

    error: () => {
      this.carregandoResumoDashboard = false;
      this.erroResumoDashboard = 'Não foi possível carregar o resumo operacional.';
      this.cdr.detectChanges();
    }
  });
}

atualizarTituloNotificacoes(): void {
  const quantidade = this.logado ? this.contarNotificacoesNaoLidas() : 0;
  document.title = quantidade > 0
    ? `(${quantidade}) ${this.tituloBase}`
    : this.tituloBase;
}

dispensarAvisoNovaNotificacao(): void {
  this.avisoNovaNotificacao = '';
}

marcarTodasNotificacoesComoLidas(): void {
  if (!this.contarNotificacoesNaoLidas()) {
    return;
  }

  const token = localStorage.getItem('token');
  this.marcandoTodasNotificacoes = true;
  this.erroNotificacoes = '';
  this.mensagemNotificacoes = '';

  this.http.patch<{ quantidade_atualizada: number }>(
    this.urlApi('/notificacoes/todas/lidas'),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (resposta) => {
      this.notificacoes = this.notificacoes.map(notificacao => ({
        ...notificacao,
        lida: true
      }));
      this.atualizarTituloNotificacoes();
      this.marcandoTodasNotificacoes = false;
      this.mensagemNotificacoes = resposta.quantidade_atualizada === 1
        ? '1 notificação marcada como lida.'
        : `${resposta.quantidade_atualizada} notificações marcadas como lidas.`;
      this.cdr.detectChanges();
    },

    error: () => {
      this.marcandoTodasNotificacoes = false;
      this.erroNotificacoes = 'Não foi possível marcar todas as notificações como lidas.';
      this.cdr.detectChanges();
    }
  });
}

carregarRelatorio() {
  this.erroRelatorio = '';
  this.mensagemRelatorio = '';

  if (
    this.filtroRelatorio.data_inicio &&
    this.filtroRelatorio.data_fim &&
    this.filtroRelatorio.data_inicio > this.filtroRelatorio.data_fim
  ) {
    this.erroRelatorio = 'A data inicial não pode ser posterior à data final.';
    return;
  }

  let parametros = new HttpParams();

  if (this.filtroRelatorio.data_inicio) {
    parametros = parametros.set('data_inicio', this.filtroRelatorio.data_inicio);
  }

  if (this.filtroRelatorio.data_fim) {
    parametros = parametros.set('data_fim', this.filtroRelatorio.data_fim);
  }

  const token = localStorage.getItem('token');
  this.carregandoRelatorio = true;

  this.http.get<any>(this.urlApi('/relatorios/resumo'), {
    params: parametros,
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (relatorio) => {
      this.relatorioResumo = relatorio;
      this.carregandoRelatorio = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao carregar relatório:', erro);
      const detalhe = erro.error?.detail;

      this.carregandoRelatorio = false;
      this.erroRelatorio = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar os indicadores gerenciais.';
      this.cdr.detectChanges();
    }
  });
}

exportarRelatorioCsv() {
  this.erroRelatorio = '';
  this.mensagemRelatorio = '';

  if (
    this.filtroRelatorio.data_inicio &&
    this.filtroRelatorio.data_fim &&
    this.filtroRelatorio.data_inicio > this.filtroRelatorio.data_fim
  ) {
    this.erroRelatorio = 'A data inicial não pode ser posterior à data final.';
    return;
  }

  let parametros = new HttpParams();

  if (this.filtroRelatorio.data_inicio) {
    parametros = parametros.set('data_inicio', this.filtroRelatorio.data_inicio);
  }

  if (this.filtroRelatorio.data_fim) {
    parametros = parametros.set('data_fim', this.filtroRelatorio.data_fim);
  }

  const token = localStorage.getItem('token');
  this.exportandoRelatorio = true;

  this.http.get(this.urlApi('/relatorios/exportar.csv'), {
    params: parametros,
    headers: {
      Authorization: `Bearer ${token}`
    },
    responseType: 'blob'
  }).subscribe({
    next: (arquivo) => {
      const enderecoArquivo = URL.createObjectURL(arquivo);
      const link = document.createElement('a');

      link.href = enderecoArquivo;
      link.download = `relatorio-gerencial-fcl-${this.formatarDataHoje()}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(enderecoArquivo);

      this.exportandoRelatorio = false;
      this.mensagemRelatorio = 'Relatório CSV exportado com sucesso!';
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao exportar relatório:', erro);
      this.exportandoRelatorio = false;
      this.erroRelatorio = 'Não foi possível exportar o relatório CSV.';
      this.cdr.detectChanges();
    }
  });
}

limparFiltroRelatorio() {
  this.filtroRelatorio = {
    data_inicio: '',
    data_fim: ''
  };
  this.carregarRelatorio();
}

obterStatusRelatorio(grupo: any): Array<{ status: string; total: number }> {
  if (!grupo?.por_status) {
    return [];
  }

  return Object.entries(grupo.por_status).map(([status, total]) => ({
    status: status.replaceAll('_', ' '),
    total: Number(total)
  }));
}

obterPercentualStatusRelatorio(grupo: any, total: number): number {
  const maiorTotal = Math.max(
    1,
    ...this.obterStatusRelatorio(grupo).map(item => item.total)
  );
  return Math.round((Number(total) / maiorTotal) * 100);
}

carregarAuditoria() {
  const token = localStorage.getItem('token');
  this.carregandoAuditoria = true;
  this.erroAuditoria = '';
  this.mensagemAuditoria = '';

  this.http.get<any[]>(this.urlApi('/auditoria/'), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (eventos) => {
      this.eventosAuditoria = eventos;
      this.carregandoAuditoria = false;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      const detalhe = erro.error?.detail;
      this.carregandoAuditoria = false;
      this.erroAuditoria = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível carregar a auditoria.';
      this.cdr.detectChanges();
    }
  });
}

obterTiposAuditoria(): string[] {
  return [...new Set(
    this.eventosAuditoria.map(evento => String(evento.tipo_registro))
  )].sort((a, b) => a.localeCompare(b, 'pt-BR'));
}

obterAcoesAuditoria(): string[] {
  return [...new Set(
    this.eventosAuditoria.map(evento => String(evento.acao))
  )].sort((a, b) => a.localeCompare(b, 'pt-BR'));
}

obterUsuariosAuditoria(): Array<{
  id_usuario: string;
  nome: string;
  login: string;
}> {
  const usuarios = new Map<string, { id_usuario: string; nome: string; login: string }>();

  for (const evento of this.eventosAuditoria) {
    const idUsuario = String(evento.id_usuario);

    if (!usuarios.has(idUsuario)) {
      usuarios.set(idUsuario, {
        id_usuario: idUsuario,
        nome: String(evento.usuario_nome ?? ''),
        login: String(evento.usuario_login ?? '')
      });
    }
  }

  return [...usuarios.values()].sort((a, b) =>
    a.nome.localeCompare(b.nome, 'pt-BR') || a.login.localeCompare(b.login, 'pt-BR')
  );
}

obterEventosAuditoriaFiltrados(): any[] {
  if (this.periodoAuditoriaInvalido()) {
    return [];
  }

  const busca = this.normalizarPesquisa(this.filtroAuditoria.busca.trim());
  const eventos = this.eventosAuditoria.filter(evento => {
    const dataEvento = String(evento.data_hora ?? '').slice(0, 10);
    const texto = this.normalizarPesquisa(
      `${evento.id_historico} ${evento.usuario_nome} ${evento.usuario_login} ` +
      `${evento.tipo_registro} ${evento.id_registro} ${evento.acao} ${evento.descricao}`
    );

    return (
      (!busca || texto.includes(busca)) &&
      (!this.filtroAuditoria.usuario ||
        String(evento.id_usuario) === this.filtroAuditoria.usuario) &&
      (!this.filtroAuditoria.tipo || evento.tipo_registro === this.filtroAuditoria.tipo) &&
      (!this.filtroAuditoria.acao || evento.acao === this.filtroAuditoria.acao) &&
      (!this.filtroAuditoria.data_inicio || dataEvento >= this.filtroAuditoria.data_inicio) &&
      (!this.filtroAuditoria.data_fim || dataEvento <= this.filtroAuditoria.data_fim)
    );
  });

  return eventos.sort((a, b) => {
    const dataA = new Date(a.data_hora).getTime();
    const dataB = new Date(b.data_hora).getTime();
    return this.filtroAuditoria.ordem === 'antigos'
      ? dataA - dataB || a.id_historico - b.id_historico
      : dataB - dataA || b.id_historico - a.id_historico;
  });
}

periodoAuditoriaInvalido(): boolean {
  return Boolean(
    this.filtroAuditoria.data_inicio &&
    this.filtroAuditoria.data_fim &&
    this.filtroAuditoria.data_inicio > this.filtroAuditoria.data_fim
  );
}

limparFiltrosAuditoria(): void {
  this.filtroAuditoria = {
    busca: '',
    usuario: '',
    tipo: '',
    acao: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  this.erroAuditoria = '';
  this.mensagemAuditoria = '';
  this.reiniciarPagina('auditoria');
}

gerarConteudoAuditoriaCsv(eventos: any[]): string {
  const cabecalho = [
    'ID do evento',
    'Data e hora',
    'Tipo de registro',
    'ID do registro',
    'Ação',
    'Usuário',
    'Login',
    'Descrição'
  ];
  const linhas = eventos.map(evento => [
    evento.id_historico,
    new Date(evento.data_hora).toLocaleString('pt-BR'),
    this.formatarTipoAuditoria(String(evento.tipo_registro)),
    evento.id_registro,
    this.formatarAcaoAuditoria(String(evento.acao)),
    evento.usuario_nome,
    evento.usuario_login,
    evento.descricao
  ]);

  return '\uFEFF' + [cabecalho, ...linhas]
    .map(linha => linha.map((valor: unknown) => this.formatarValorCsv(valor)).join(';'))
    .join('\r\n');
}

formatarValorCsv(valor: unknown): string {
  let texto = String(valor ?? '');

  if (/^[\s]*[=+\-@]/.test(texto)) {
    texto = `'${texto}`;
  }

  return `"${texto.replaceAll('"', '""')}"`;
}

exportarAuditoriaCsv(): void {
  this.erroAuditoria = '';
  this.mensagemAuditoria = '';

  if (this.periodoAuditoriaInvalido()) {
    this.erroAuditoria = 'A data inicial não pode ser posterior à data final.';
    return;
  }

  const eventos = this.obterEventosAuditoriaFiltrados();

  if (!eventos.length) {
    this.erroAuditoria = 'Não há eventos para exportar com os filtros atuais.';
    return;
  }

  this.exportandoAuditoria = true;

  try {
    const conteudo = this.gerarConteudoAuditoriaCsv(eventos);
    const arquivo = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
    const enderecoArquivo = URL.createObjectURL(arquivo);
    const link = document.createElement('a');

    link.href = enderecoArquivo;
    link.download = `auditoria-fcl-${this.formatarDataHoje()}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(enderecoArquivo);

    this.mensagemAuditoria = `${eventos.length} evento(s) exportado(s) com sucesso!`;
  } catch (erro) {
    console.error('Erro ao exportar auditoria:', erro);
    this.erroAuditoria = 'Não foi possível gerar o arquivo de auditoria.';
  } finally {
    this.exportandoAuditoria = false;
    this.cdr.detectChanges();
  }
}

formatarTipoAuditoria(tipo: string): string {
  const nomes: Record<string, string> = {
    CLIENTE: 'Cliente',
    ENTREGA: 'Entrega',
    FORNECEDOR: 'Fornecedor',
    PRODUTO: 'Produto',
    SOLICITACAO: 'Solicitação',
    PEDIDO: 'Pedido',
    RECEBIMENTO: 'Recebimento',
    USUARIO: 'Usuário',
    SISTEMA: 'Sistema'
  };

  return nomes[tipo] || tipo.replaceAll('_', ' ');
}

formatarAcaoAuditoria(acao: string): string {
  const nomes: Record<string, string> = {
    CADASTRO: 'Cadastro',
    EDICAO: 'Edição',
    ATIVACAO: 'Ativação',
    DESATIVACAO: 'Desativação',
    APROVACAO: 'Aprovação',
    REJEICAO: 'Rejeição',
    ALTERACAO_STATUS: 'Alteração de status',
    ATRIBUICAO_ENTREGADOR: 'Atribuição de entregador',
    ANEXO_COMPROVANTE: 'Anexo de comprovante',
    ALTERACAO_SENHA: 'Alteração de senha',
    CANCELAMENTO: 'Cancelamento',
    ESTORNO: 'Estorno',
    NAO_ENTREGA: 'Entrega não concluída',
    AGENDAMENTO: 'Agendamento',
    REAGENDAMENTO: 'Reagendamento',
    PEDIDO_CRIADO: 'Pedido criado',
    PEDIDO_REALIZADO: 'Pedido realizado',
    PEDIDO_CANCELADO: 'Pedido cancelado',
    ENVIO_RECEBIMENTO: 'Envio para recebimento',
    RECEBIMENTO_PARCIAL: 'Recebimento parcial',
    RECEBIMENTO_TOTAL: 'Recebimento total',
    ESTORNO_RECEBIMENTO: 'Estorno de recebimento'
  };

  return nomes[acao] || acao.replaceAll('_', ' ');
}

marcarNotificacaoComoLida(notificacao: any) {
  if (notificacao.lida) {
    return;
  }

  const token = localStorage.getItem('token');
  this.notificacaoEmAtualizacao = notificacao.id_notificacao;
  this.erroNotificacoes = '';

  this.http.patch<any>(
    this.urlApi(`/notificacoes/${notificacao.id_notificacao}/lida`),
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  ).subscribe({
    next: (notificacaoAtualizada) => {
      const indice = this.notificacoes.findIndex(
        item => item.id_notificacao === notificacaoAtualizada.id_notificacao
      );

      if (indice >= 0) {
        this.notificacoes[indice] = notificacaoAtualizada;
      }

      this.atualizarTituloNotificacoes();
      this.notificacaoEmAtualizacao = null;
      this.cdr.detectChanges();
    },

    error: (erro) => {
      console.error('Erro ao marcar notificação como lida:', erro);
      const detalhe = erro.error?.detail;

      this.notificacaoEmAtualizacao = null;
      this.erroNotificacoes = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível marcar a notificação como lida.';
      this.cdr.detectChanges();
    }
  });
}

obterTotalPaginas(totalItens: number, chave: ChavePaginacao): number {
  return Math.max(1, Math.ceil(totalItens / this.paginacao[chave].porPagina));
}

obterPaginaAtual(totalItens: number, chave: ChavePaginacao): number {
  return Math.min(
    Math.max(this.paginacao[chave].pagina, 1),
    this.obterTotalPaginas(totalItens, chave)
  );
}

paginarLista(registros: any[], chave: ChavePaginacao): any[] {
  const pagina = this.obterPaginaAtual(registros.length, chave);
  const porPagina = this.paginacao[chave].porPagina;
  const inicio = (pagina - 1) * porPagina;

  return registros.slice(inicio, inicio + porPagina);
}

alterarPagina(
  chave: ChavePaginacao,
  pagina: number,
  totalItens: number
): void {
  this.paginacao[chave].pagina = Math.min(
    Math.max(pagina, 1),
    this.obterTotalPaginas(totalItens, chave)
  );
  this.salvarEstadoNavegacao();
}

reiniciarPagina(chave: ChavePaginacao): void {
  this.paginacao[chave].pagina = 1;
  this.salvarEstadoNavegacao();
}

normalizarPesquisa(valor: unknown): string {
  return String(valor ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

aplicarFiltroLista(
  registros: any[],
  filtro: { busca: string; status: string; ordem: string },
  obterTexto: (registro: any) => string,
  obterStatus: (registro: any) => string,
  obterId: (registro: any) => number,
  obterNome: (registro: any) => string
): any[] {
  const busca = this.normalizarPesquisa(filtro.busca.trim());
  const resultado = registros.filter(registro => {
    const correspondeBusca = !busca || this.normalizarPesquisa(
      obterTexto(registro)
    ).includes(busca);
    const correspondeStatus = !filtro.status || obterStatus(registro) === filtro.status;

    return correspondeBusca && correspondeStatus;
  });

  return resultado.sort((a, b) => {
    if (filtro.ordem === 'az') {
      return obterNome(a).localeCompare(obterNome(b), 'pt-BR');
    }

    if (filtro.ordem === 'za') {
      return obterNome(b).localeCompare(obterNome(a), 'pt-BR');
    }

    if (filtro.ordem === 'antigos') {
      return obterId(a) - obterId(b);
    }

    return obterId(b) - obterId(a);
  });
}

obterSolicitacoesFiltradas(): any[] {
  return this.aplicarFiltroLista(
    this.solicitacoes,
    this.filtroSolicitacoes,
    item => `${item.id_solicitacao} ${item.motivo} ${item.observacao} ${item.prioridade} ${item.status} ${item.motivo_rejeicao} ${item.motivo_cancelamento}`,
    item => item.status,
    item => item.id_solicitacao,
    item => item.motivo || ''
  );
}

selecionarEtapaListagem(
  listagem: 'solicitacoes' | 'pedidos' | 'entregas',
  status: string
): void {
  if (listagem === 'solicitacoes') {
    this.filtroSolicitacoes.status = status;
  } else if (listagem === 'pedidos') {
    this.filtroPedidos.status = status;
  } else {
    this.filtroEntregas.status = status;
  }

  this.reiniciarPagina(listagem);
}

contarRegistrosEtapa(registros: any[], status: string): number {
  return status
    ? registros.filter(registro => registro.status === status).length
    : registros.length;
}

temFiltrosSolicitacoes(): boolean {
  return Boolean(
    this.filtroSolicitacoes.busca ||
    this.filtroSolicitacoes.status ||
    this.filtroSolicitacoes.ordem !== 'recentes'
  );
}

limparFiltrosSolicitacoes(): void {
  this.filtroSolicitacoes = { busca: '', status: '', ordem: 'recentes' };
  this.reiniciarPagina('solicitacoes');
}

obterPedidosFiltrados(): any[] {
  if (this.periodoPedidosInvalido()) {
    return [];
  }

  const pedidosFiltrados = this.aplicarFiltroLista(
    this.pedidos,
    this.filtroPedidos,
    item => `${item.id_pedido_compra} ${item.id_solicitacao} ${item.numero_pedido} ${item.status} ${this.obterNomeFornecedor(item.id_fornecedor)} ${item.observacao} ${item.motivo_cancelamento} ${(item.itens || []).map((produto: any) => this.obterNomeProduto(produto.id_produto)).join(' ')}`,
    item => item.status,
    item => item.id_pedido_compra,
    item => item.numero_pedido || ''
  );

  return pedidosFiltrados.filter(pedido => (
    (!this.filtroPedidos.fornecedor ||
      String(pedido.id_fornecedor) === this.filtroPedidos.fornecedor) &&
    (!this.filtroPedidos.data_inicio ||
      pedido.data_pedido >= this.filtroPedidos.data_inicio) &&
    (!this.filtroPedidos.data_fim ||
      pedido.data_pedido <= this.filtroPedidos.data_fim)
  ));
}

periodoPedidosInvalido(): boolean {
  return Boolean(
    this.filtroPedidos.data_inicio &&
    this.filtroPedidos.data_fim &&
    this.filtroPedidos.data_inicio > this.filtroPedidos.data_fim
  );
}

temFiltrosPedidos(): boolean {
  return Boolean(
    this.filtroPedidos.busca ||
    this.filtroPedidos.status ||
    this.filtroPedidos.fornecedor ||
    this.filtroPedidos.data_inicio ||
    this.filtroPedidos.data_fim ||
    this.filtroPedidos.ordem !== 'recentes'
  );
}

limparFiltrosPedidos(): void {
  this.filtroPedidos = {
    busca: '',
    status: '',
    fornecedor: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  this.reiniciarPagina('pedidos');
}

gerarConteudoPedidosCsv(pedidos: any[]): string {
  const cabecalho = [
    'Pedido',
    'Solicitação de origem',
    'Fornecedor',
    'Data',
    'Status',
    'Produto',
    'Quantidade pedida',
    'Quantidade recebida',
    'Saldo pendente',
    'Observação',
    'Motivo do cancelamento'
  ];
  const linhas = pedidos.flatMap(pedido => {
    const itens = pedido.itens?.length ? pedido.itens : [null];
    return itens.map((item: any) => [
      pedido.numero_pedido || `#${pedido.id_pedido_compra}`,
      pedido.id_solicitacao,
      this.obterNomeFornecedor(pedido.id_fornecedor),
      this.formatarDataBrasileira(pedido.data_pedido),
      pedido.status,
      item ? this.obterNomeProduto(item.id_produto) : '',
      item?.quantidade ?? '',
      item?.quantidade_recebida ?? '',
      item?.saldo_pendente ?? '',
      pedido.observacao,
      pedido.motivo_cancelamento
    ]);
  });

  return '\uFEFF' + [cabecalho, ...linhas]
    .map(linha => linha.map((valor: unknown) => this.formatarValorCsv(valor)).join(';'))
    .join('\r\n');
}

exportarPedidosCsv(): void {
  this.erroPedidos = '';
  this.mensagemPedidos = '';

  if (this.periodoPedidosInvalido()) {
    this.erroPedidos = 'A data inicial não pode ser posterior à data final.';
    return;
  }

  const pedidos = this.obterPedidosFiltrados();
  if (!pedidos.length) {
    this.erroPedidos = 'Não há pedidos para exportar com os filtros atuais.';
    return;
  }

  this.exportandoPedidos = true;

  try {
    const conteudo = this.gerarConteudoPedidosCsv(pedidos);
    const arquivo = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
    const enderecoArquivo = URL.createObjectURL(arquivo);
    const link = document.createElement('a');

    link.href = enderecoArquivo;
    link.download = `pedidos-fcl-${this.formatarDataHoje()}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(enderecoArquivo);

    this.mensagemPedidos = `${pedidos.length} pedido(s) exportado(s) com sucesso!`;
  } catch (erro) {
    console.error('Erro ao exportar pedidos:', erro);
    this.erroPedidos = 'Não foi possível gerar o arquivo de pedidos.';
  } finally {
    this.exportandoPedidos = false;
    this.cdr.detectChanges();
  }
}

obterRecebimentosFiltrados(): any[] {
  return this.aplicarFiltroLista(
    this.obterPedidosDisponiveisRecebimento(),
    this.filtroRecebimentos,
    item => `${item.id_pedido_compra} ${item.numero_pedido} ${item.status} ${this.obterNomeFornecedor(item.id_fornecedor)}`,
    item => item.status,
    item => item.id_pedido_compra,
    item => item.numero_pedido || ''
  );
}

periodoHistoricoRecebimentosInvalido(): boolean {
  return Boolean(
    this.filtroHistoricoRecebimentos.data_inicio &&
    this.filtroHistoricoRecebimentos.data_fim &&
    this.filtroHistoricoRecebimentos.data_inicio >
      this.filtroHistoricoRecebimentos.data_fim
  );
}

obterHistoricoRecebimentosFiltrado(): any[] {
  if (this.periodoHistoricoRecebimentosInvalido()) {
    return [];
  }

  const busca = this.normalizarPesquisa(
    this.filtroHistoricoRecebimentos.busca.trim()
  );
  const resultado = this.recebimentos.filter(recebimento => {
    const produtos = (recebimento.itens || [])
      .map((item: any) => this.obterNomeProduto(item.id_produto))
      .join(' ');
    const texto = this.normalizarPesquisa([
      recebimento.id_recebimento,
      this.obterNumeroPedidoRecebimento(recebimento.id_pedido_compra),
      recebimento.numero_nota_fiscal,
      recebimento.observacao,
      recebimento.motivo_estorno,
      produtos
    ].join(' '));
    const data = String(recebimento.data_recebimento || '').slice(0, 10);

    return (
      (!busca || texto.includes(busca)) &&
      (!this.filtroHistoricoRecebimentos.status ||
        recebimento.status === this.filtroHistoricoRecebimentos.status) &&
      (!this.filtroHistoricoRecebimentos.data_inicio ||
        data >= this.filtroHistoricoRecebimentos.data_inicio) &&
      (!this.filtroHistoricoRecebimentos.data_fim ||
        data <= this.filtroHistoricoRecebimentos.data_fim)
    );
  });

  return resultado.sort((a, b) => {
    const comparacao = String(a.data_recebimento)
      .localeCompare(String(b.data_recebimento));
    return this.filtroHistoricoRecebimentos.ordem === 'antigos'
      ? comparacao
      : -comparacao;
  });
}

temFiltrosHistoricoRecebimentos(): boolean {
  return Boolean(
    this.filtroHistoricoRecebimentos.busca ||
    this.filtroHistoricoRecebimentos.status ||
    this.filtroHistoricoRecebimentos.data_inicio ||
    this.filtroHistoricoRecebimentos.data_fim ||
    this.filtroHistoricoRecebimentos.ordem !== 'recentes'
  );
}

limparFiltrosHistoricoRecebimentos(): void {
  this.filtroHistoricoRecebimentos = {
    busca: '',
    status: '',
    data_inicio: '',
    data_fim: '',
    ordem: 'recentes'
  };
  this.reiniciarPagina('historico_recebimentos');
}

gerarConteudoHistoricoRecebimentosCsv(recebimentos: any[]): string {
  const cabecalho = [
    'Recebimento',
    'Pedido',
    'Data e hora',
    'Status',
    'Nota fiscal',
    'Produto',
    'Quantidade recebida',
    'Observação',
    'Motivo do estorno'
  ];
  const linhas = recebimentos.flatMap(recebimento => {
    const itens = recebimento.itens?.length ? recebimento.itens : [null];
    return itens.map((item: any) => [
      recebimento.id_recebimento,
      this.obterNumeroPedidoRecebimento(recebimento.id_pedido_compra),
      new Date(recebimento.data_recebimento).toLocaleString('pt-BR'),
      recebimento.status,
      recebimento.numero_nota_fiscal,
      item ? this.obterNomeProduto(item.id_produto) : '',
      item?.quantidade_recebida ?? '',
      recebimento.observacao,
      recebimento.motivo_estorno
    ]);
  });

  return '\uFEFF' + [cabecalho, ...linhas]
    .map(linha => linha.map((valor: unknown) => this.formatarValorCsv(valor)).join(';'))
    .join('\r\n');
}

exportarHistoricoRecebimentosCsv(): void {
  this.erroRecebimentos = '';
  this.mensagemRecebimentos = '';

  if (this.periodoHistoricoRecebimentosInvalido()) {
    this.erroRecebimentos = 'A data inicial não pode ser posterior à data final.';
    return;
  }

  const recebimentos = this.obterHistoricoRecebimentosFiltrado();
  if (!recebimentos.length) {
    this.erroRecebimentos = 'Não há recebimentos para exportar com os filtros atuais.';
    return;
  }

  this.exportandoHistoricoRecebimentos = true;

  try {
    const conteudo = this.gerarConteudoHistoricoRecebimentosCsv(recebimentos);
    const arquivo = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
    const enderecoArquivo = URL.createObjectURL(arquivo);
    const link = document.createElement('a');

    link.href = enderecoArquivo;
    link.download = `recebimentos-fcl-${this.formatarDataHoje()}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(enderecoArquivo);

    this.mensagemRecebimentos = `${recebimentos.length} recebimento(s) exportado(s) com sucesso!`;
  } catch (erro) {
    console.error('Erro ao exportar recebimentos:', erro);
    this.erroRecebimentos = 'Não foi possível gerar o arquivo de recebimentos.';
  } finally {
    this.exportandoHistoricoRecebimentos = false;
    this.cdr.detectChanges();
  }
}

obterEntregasFiltradas(): any[] {
  const entregasFiltradas = this.aplicarFiltroLista(
    this.entregas,
    this.filtroEntregas,
    item => `${item.id_entrega} ${item.status} ${this.obterNomeCliente(item.id_cliente)} ${this.obterNomeUsuario(item.id_entregador)} ${item.observacao}`,
    item => item.status,
    item => item.id_entrega,
    item => this.obterNomeCliente(item.id_cliente)
  );

  const entregasPorRota = entregasFiltradas.filter(entrega => {
    const correspondeEntregador = !this.filtroEntregas.entregador || (
      this.filtroEntregas.entregador === 'SEM_ENTREGADOR'
        ? entrega.id_entregador == null
        : String(entrega.id_entregador) === this.filtroEntregas.entregador
    );
    const correspondeData = !this.filtroEntregas.data_agendada ||
      entrega.data_agendada === this.filtroEntregas.data_agendada;

    return correspondeEntregador && correspondeData;
  });

  const entregasPorPrazo = this.filtroEntregas.prazo
    ? entregasPorRota.filter(
        entrega => this.obterSituacaoPrazoEntrega(entrega) === this.filtroEntregas.prazo
      )
    : entregasPorRota;

  if (!['data_proxima', 'data_distante'].includes(this.filtroEntregas.ordem)) {
    return entregasPorPrazo;
  }

  return entregasPorPrazo.sort((a, b) => {
    if (!a.data_agendada) {
      return 1;
    }
    if (!b.data_agendada) {
      return -1;
    }

    const comparacao = a.data_agendada.localeCompare(b.data_agendada);
    return this.filtroEntregas.ordem === 'data_proxima'
      ? comparacao
      : -comparacao;
  });
}

obterSituacaoPrazoEntrega(entrega: any): string {
  if (['ENTREGUE', 'CANCELADA'].includes(entrega.status)) {
    return 'ENCERRADA';
  }

  if (!entrega.data_agendada || !this.dataIsoValida(entrega.data_agendada)) {
    return 'SEM_DATA';
  }

  const hoje = this.formatarDataHoje();
  if (entrega.data_agendada < hoje) {
    return 'ATRASADA';
  }
  if (entrega.data_agendada === hoje) {
    return 'HOJE';
  }

  return 'FUTURA';
}

contarEntregasPorPrazo(situacao: string): number {
  return this.entregas.filter(
    entrega => this.obterSituacaoPrazoEntrega(entrega) === situacao
  ).length;
}

temFiltrosEntrega(): boolean {
  return Boolean(
    this.filtroEntregas.busca ||
    this.filtroEntregas.status ||
    this.filtroEntregas.prazo ||
    this.filtroEntregas.entregador ||
    this.filtroEntregas.data_agendada ||
    this.filtroEntregas.ordem !== 'recentes'
  );
}

limparFiltrosEntrega(): void {
  this.filtroEntregas = {
    busca: '',
    status: '',
    prazo: '',
    entregador: '',
    data_agendada: '',
    ordem: 'recentes'
  };
  this.reiniciarPagina('entregas');
}

formatarSituacaoPrazoEntrega(entrega: any): string {
  const nomes: Record<string, string> = {
    ATRASADA: 'Atrasada',
    HOJE: 'Para hoje',
    FUTURA: 'Data futura',
    SEM_DATA: 'Sem data',
    ENCERRADA: 'Encerrada'
  };

  return nomes[this.obterSituacaoPrazoEntrega(entrega)];
}

gerarConteudoEntregasCsv(entregas: any[]): string {
  const cabecalho = [
    'Entrega',
    'Cliente',
    'Endereço',
    'Telefone',
    'Entregador',
    'Data agendada',
    'Prazo',
    'Status',
    'Observação'
  ];
  const linhas = entregas.map(entrega => {
    const cliente = this.clientes.find(
      item => item.id_cliente === entrega.id_cliente
    );

    return [
      entrega.id_entrega,
      this.obterNomeCliente(entrega.id_cliente),
      this.obterEnderecoCliente(entrega.id_cliente),
      cliente?.telefone ? this.formatarTelefone(cliente.telefone) : '',
      this.obterNomeUsuario(entrega.id_entregador),
      entrega.data_agendada
        ? this.formatarDataBrasileira(entrega.data_agendada)
        : '',
      this.formatarSituacaoPrazoEntrega(entrega),
      entrega.status,
      entrega.observacao
    ];
  });

  return '\uFEFF' + [cabecalho, ...linhas]
    .map(linha => linha.map((valor: unknown) => this.formatarValorCsv(valor)).join(';'))
    .join('\r\n');
}

exportarEntregasCsv(): void {
  this.erroEntregas = '';
  this.mensagemEntregas = '';
  const entregas = this.obterEntregasFiltradas();

  if (!entregas.length) {
    this.erroEntregas = 'Não há entregas para exportar com os filtros atuais.';
    return;
  }

  this.exportandoEntregas = true;

  try {
    const conteudo = this.gerarConteudoEntregasCsv(entregas);
    const arquivo = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
    const enderecoArquivo = URL.createObjectURL(arquivo);
    const link = document.createElement('a');

    link.href = enderecoArquivo;
    link.download = `entregas-fcl-${this.formatarDataHoje()}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(enderecoArquivo);

    this.mensagemEntregas = `${entregas.length} entrega(s) exportada(s) com sucesso!`;
  } catch (erro) {
    console.error('Erro ao exportar entregas:', erro);
    this.erroEntregas = 'Não foi possível gerar o arquivo de entregas.';
  } finally {
    this.exportandoEntregas = false;
    this.cdr.detectChanges();
  }
}

obterClientesFiltrados(): any[] {
  return this.aplicarFiltroLista(
    this.clientes,
    this.filtroClientes,
    item => `${item.nome} ${item.cpf_cnpj} ${item.telefone} ${item.cidade} ${item.uf}`,
    item => item.ativo ? 'ATIVO' : 'INATIVO',
    item => item.id_cliente,
    item => item.nome || ''
  );
}

obterFornecedoresFiltrados(): any[] {
  return this.aplicarFiltroLista(
    this.fornecedores,
    this.filtroFornecedores,
    item => `${item.razao_social} ${item.nome_fantasia} ${item.cnpj} ${item.telefone} ${item.email}`,
    item => item.ativo ? 'ATIVO' : 'INATIVO',
    item => item.id_fornecedor,
    item => item.nome_fantasia || item.razao_social || ''
  );
}

obterProdutosFiltrados(): any[] {
  return this.aplicarFiltroLista(
    this.produtos,
    this.filtroProdutos,
    item => `${item.codigo} ${item.nome} ${item.categoria} ${item.marca} ${item.unidade}`,
    item => item.ativo ? 'ATIVO' : 'INATIVO',
    item => item.id_produto,
    item => item.nome || ''
  );
}

temFiltrosCadastro(tipo: 'clientes' | 'fornecedores' | 'produtos' | 'usuarios'): boolean {
  if (tipo === 'usuarios') {
    return Boolean(
      this.filtroUsuarios.busca ||
      this.filtroUsuarios.status ||
      this.filtroUsuarios.perfil ||
      this.filtroUsuarios.ordem !== 'az'
    );
  }

  const filtro = tipo === 'clientes'
    ? this.filtroClientes
    : tipo === 'fornecedores'
      ? this.filtroFornecedores
      : this.filtroProdutos;

  return Boolean(filtro.busca || filtro.status || filtro.ordem !== 'az');
}

limparFiltrosCadastro(tipo: 'clientes' | 'fornecedores' | 'produtos' | 'usuarios'): void {
  if (tipo === 'clientes') {
    this.filtroClientes = { busca: '', status: '', ordem: 'az' };
  } else if (tipo === 'fornecedores') {
    this.filtroFornecedores = { busca: '', status: '', ordem: 'az' };
  } else if (tipo === 'produtos') {
    this.filtroProdutos = { busca: '', status: '', ordem: 'az' };
  } else {
    this.filtroUsuarios = { busca: '', status: '', perfil: '', ordem: 'az' };
  }

  this.reiniciarPagina(tipo);
}

obterNotificacoesFiltradas(): any[] {
  return this.aplicarFiltroLista(
    this.notificacoes,
    this.filtroNotificacoes,
    item => `${item.titulo} ${item.mensagem}`,
    item => item.lida ? 'LIDA' : 'NAO_LIDA',
    item => item.id_notificacao,
    item => item.titulo || ''
  );
}

temFiltrosNotificacoes(): boolean {
  return Boolean(
    this.filtroNotificacoes.busca ||
    this.filtroNotificacoes.status ||
    this.filtroNotificacoes.ordem !== 'recentes'
  );
}

limparFiltrosNotificacoes(): void {
  this.filtroNotificacoes = { busca: '', status: '', ordem: 'recentes' };
  this.reiniciarPagina('notificacoes');
}

obterUsuariosFiltrados(): any[] {
  const usuariosPorPerfil = this.filtroUsuarios.perfil
    ? this.usuarios.filter(usuario => usuario.perfil === this.filtroUsuarios.perfil)
    : this.usuarios;

  return this.aplicarFiltroLista(
    usuariosPorPerfil,
    this.filtroUsuarios,
    item => `${item.nome} ${item.login} ${item.perfil}`,
    item => item.ativo ? 'ATIVO' : 'INATIVO',
    item => item.id_usuario,
    item => item.nome || ''
  );
}

classeStatus(status: string): string {
  const statusSucesso = [
    'APROVADA',
    'PEDIDO_REALIZADO',
    'RECEBIDO_TOTAL',
    'ENTREGUE',
    'ATIVO',
    'LIDA'
  ];
  const statusErro = [
    'REJEITADA',
    'CANCELADO',
    'CANCELADA',
    'NAO_ENTREGUE',
    'ESTORNADO',
    'INATIVO'
  ];
  const statusInformativo = [
    'SOLICITADA',
    'CRIADO',
    'RECEBIDO_PARCIAL',
    'PRONTA_PARA_ENTREGA',
    'EM_ROTA'
  ];

  if (statusSucesso.includes(status)) {
    return 'status-sucesso';
  }

  if (statusErro.includes(status)) {
    return 'status-erro';
  }

  if (statusInformativo.includes(status)) {
    return 'status-informativo';
  }

  return 'status-pendente';
}

formatarStatus(status: string | null | undefined): string {
  const rotulos: Record<string, string> = {
    SOLICITADA: 'Solicitada',
    EM_ANALISE: 'Em análise',
    APROVADA: 'Aprovada',
    REJEITADA: 'Rejeitada',
    CANCELADO: 'Cancelado',
    CANCELADA: 'Cancelada',
    CRIADO: 'Criado',
    AGUARDANDO_RECEBIMENTO: 'Aguardando recebimento',
    RECEBIDO_PARCIAL: 'Recebido parcial',
    RECEBIDO_TOTAL: 'Recebido total',
    REGISTRADO: 'Registrado',
    ESTORNADO: 'Estornado',
    CADASTRADA: 'Cadastrada',
    AGENDADA: 'Agendada',
    EM_SEPARACAO: 'Em separação',
    PRONTA_PARA_ENTREGA: 'Pronta para entrega',
    EM_ROTA: 'Em rota',
    NAO_ENTREGUE: 'Não entregue',
    ENTREGUE: 'Entregue',
    ATIVO: 'Ativo',
    INATIVO: 'Inativo',
    LIDA: 'Lida',
    NAO_LIDA: 'Não lida',
    BAIXA: 'Baixa',
    MEDIA: 'Média',
    ALTA: 'Alta'
  };

  if (!status) {
    return '';
  }

  return rotulos[status] ?? status
    .toLowerCase()
    .replaceAll('_', ' ')
    .replace(/^./, letra => letra.toUpperCase());
}

formatarPerfil(perfil: string): string {
  const perfis: Record<string, string> = {
    ADMINISTRADOR: 'Administrador',
    FUNCIONARIO: 'Funcionário',
    ESTOQUE: 'Estoque',
    ENTREGADOR: 'Entregador'
  };

  return perfis[perfil] ?? this.formatarStatus(perfil);
}

classePrioridade(prioridade: string): string {
  if (prioridade === 'ALTA') {
    return 'status-erro';
  }

  if (prioridade === 'BAIXA') {
    return 'status-informativo';
  }

  return 'status-pendente';
}

etapaEntregaConcluida(statusAtual: string, statusEtapa: string): boolean {
  const indiceEtapa = this.etapasEntregaVisual.findIndex(
    etapa => etapa.status === statusEtapa
  );
  const statusComparacao = statusAtual === 'NAO_ENTREGUE'
    ? 'EM_ROTA'
    : statusAtual;
  const indiceAtual = this.etapasEntregaVisual.findIndex(
    etapa => etapa.status === statusComparacao
  );

  return indiceAtual >= indiceEtapa && indiceAtual >= 0;
}

podeAcessarSolicitacoes(): boolean {
  return ['ADMINISTRADOR', 'FUNCIONARIO', 'ESTOQUE'].includes(this.perfilUsuario);
}

podeAdministrarSolicitacoes(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

podeAcessarPedidos(): boolean {
  return ['ADMINISTRADOR', 'ESTOQUE'].includes(this.perfilUsuario);
}

podeAdministrarPedidos(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

podeAcessarRecebimentos(): boolean {
  return ['ADMINISTRADOR', 'ESTOQUE'].includes(this.perfilUsuario);
}

podeAcessarCadastrosDeCompras(): boolean {
  return ['ADMINISTRADOR', 'FUNCIONARIO', 'ESTOQUE'].includes(this.perfilUsuario);
}

podeAcessarRelatorios(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

podeAcessarAuditoria(): boolean {
  return this.perfilUsuario === 'ADMINISTRADOR';
}

tituloTelaAtual(): string {
  const titulos: Record<string, string> = {
    dashboard: 'Visão geral',
    'minha-conta': 'Minha conta',
    solicitacoes: 'Solicitações de compra',
    'nova-solicitacao': 'Nova solicitação',
    pedidos: 'Pedidos de compra',
    'novo-pedido': 'Novo pedido',
    recebimentos: 'Recebimentos',
    entregas: 'Entregas',
    'minhas-entregas': 'Minhas entregas',
    'nova-entrega': 'Nova entrega',
    clientes: 'Clientes',
    'formulario-cliente': this.clienteEmEdicaoId === null
      ? 'Novo cliente'
      : 'Editar cliente',
    fornecedores: 'Fornecedores',
    'formulario-fornecedor': this.fornecedorEmEdicaoId === null
      ? 'Novo fornecedor'
      : 'Editar fornecedor',
    produtos: 'Produtos',
    'formulario-produto': this.produtoEmEdicaoId === null
      ? 'Novo produto'
      : 'Editar produto',
    usuarios: 'Usuários',
    'formulario-usuario': this.usuarioEmEdicaoId === null
      ? 'Novo usuário'
      : 'Editar usuário',
    notificacoes: 'Notificações',
    relatorios: 'Relatórios gerenciais',
    auditoria: 'Auditoria'
  };

  return titulos[this.telaAtual] ?? 'Sistema FCL';
}

alternarMenuMobile(): void {
  this.menuMobileAberto = !this.menuMobileAberto;
}

fecharMenuMobile(): void {
  this.menuMobileAberto = false;
}

  abrirTela(tela: string, registrarHistorico = true) {
    if (!this.telaPermitida(tela)) tela = this.telaInicialPerfil();
    if (this.telaAtual !== tela) this.salvarEstadoNavegacao();
    this.telaAtual = tela;
    if (
      registrarHistorico &&
      new URLSearchParams(window.location.search).get('tela') !== tela
    ) {
      const url = `/sistema?tela=${encodeURIComponent(tela)}`;
      window.history.pushState({ tela }, '', url);
    }
    this.fecharMenuMobile();
    this.fecharPainelDetalhes();
    this.fecharPreVisualizacao();
    this.fecharFormularioAuxiliarEntrega();

  if (tela === 'minha-conta') {
    this.erroMinhaConta = '';
    this.mensagemMinhaConta = '';
    this.formularioMinhaSenha = {
      senha_atual: '',
      nova_senha: '',
      confirmar_nova_senha: ''
    };
  }

  if (tela === 'dashboard') {
    this.carregarNotificacoes(true);
    this.carregarResumoDashboard();
  }

  if (tela === 'solicitacoes') {
    this.erroSolicitacoes = '';
    this.mensagemSolicitacoes = '';
    this.cancelarRejeicaoSolicitacao();
    this.solicitacaoHistoricoSelecionada = null;
    this.historicoSolicitacao = [];
    this.erroHistoricoSolicitacao = '';
    this.carregarSolicitacoes();
    this.carregarProdutos();
  }

  if (tela === 'nova-solicitacao') {
    this.erroNovaSolicitacao = '';
    this.carregarProdutos();
    this.verificarRascunho('solicitacao');
  }

  if (tela === 'pedidos') {
    this.mensagemPedidos = '';
    this.erroAcaoPedidos = '';
    this.desistirEdicaoPedido();
    this.pedidoHistoricoSelecionado = null;
    this.historicoPedido = [];
    this.erroHistoricoPedido = '';
    this.carregarPedidos();
  }

  if (tela === 'novo-pedido') {
    this.erroNovoPedido = '';

    if (!this.solicitacoes.length || !this.fornecedores.length) {
      this.carregarPedidos();
    }
    this.verificarRascunho('pedido');
  }

  if (tela === 'recebimentos') {
    this.recebimentoHistoricoExpandido = null;
    this.mensagemRecebimentos = '';
    this.carregarRecebimentos();
  }

  if (tela === 'entregas') {
    this.mensagemEntregas = '';
    this.desistirEdicaoEntrega();
    this.entregaHistoricoSelecionada = null;
    this.historicoEntrega = [];
    this.erroHistoricoEntrega = '';
    this.carregarEntregas();
  }

  if (tela === 'minhas-entregas') {
    this.mensagemEntregas = '';
    this.carregarEntregas();
  }

  if (tela === 'nova-entrega') {
    this.erroNovaEntrega = '';

    if (!this.clientes.length || !this.usuariosResumo.length) {
      this.carregarEntregas();
    }
    this.verificarRascunho('entrega');
  }

  if (tela === 'clientes') {
    this.mensagemClientes = '';
    this.carregarClientes();
  }

  if (tela === 'usuarios') {
    this.mensagemUsuarios = '';
    this.carregarUsuarios();
  }

  if (tela === 'fornecedores') {
    this.mensagemFornecedores = '';
    this.carregarFornecedores();
  }

  if (tela === 'produtos') {
    this.mensagemProdutos = '';
    this.carregarProdutosTela();
  }

  if (tela === 'notificacoes') {
    this.dispensarAvisoNovaNotificacao();
    this.carregarNotificacoes();
  }

  if (tela === 'relatorios') {
    this.mensagemRelatorio = '';
    this.carregarRelatorio();
  }

  if (tela === 'auditoria') {
    this.erroAuditoria = '';
    this.mensagemAuditoria = '';
    this.carregarAuditoria();
  }

  window.setTimeout(() => {
    if (!navigator.userAgent.toLowerCase().includes('jsdom')) {
      window.scrollTo({ top: this.posicoesRolagem[tela] || 0, behavior: 'auto' });
    }
  }, 0);
}

  obterNomeProduto(idProduto: number): string {
  const produto = this.produtos.find(
    p => p.id_produto === idProduto
  );

  return produto ? produto.nome : `Produto #${idProduto}`;
}

obterNomeFornecedor(idFornecedor: number): string {
  const fornecedor = this.fornecedores.find(
    item => item.id_fornecedor === idFornecedor
  );

  return fornecedor
    ? fornecedor.nome_fantasia || fornecedor.razao_social
    : `Fornecedor #${idFornecedor}`;
}

  criarSolicitacao() {
  const token = localStorage.getItem('token');

  this.erroNovaSolicitacao = '';

  if (!this.novaSolicitacao.motivo.trim()) {
    this.erroNovaSolicitacao = 'Informe o motivo da compra.';
    return;
  }

  if (
    !this.novaSolicitacao.itens.length ||
    this.novaSolicitacao.itens.some(
      item => !item.id_produto || Number(item.quantidade) < 1
    )
  ) {
    this.erroNovaSolicitacao = 'Selecione os produtos e informe quantidades válidas.';
    return;
  }

  const dados = {
  prioridade: this.novaSolicitacao.prioridade,
  motivo: this.novaSolicitacao.motivo.trim(),
  observacao: this.novaSolicitacao.observacao.trim() || null,
  itens: this.novaSolicitacao.itens
};

  this.criandoSolicitacao = true;

  this.http.post<any>(this.urlApi('/solicitacoes/'), dados, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  }).subscribe({
    next: (resposta) => {

  this.descartarRascunho('solicitacao');

  this.criandoSolicitacao = false;

  this.novaSolicitacao = {
  prioridade: 'MEDIA',
  motivo: '',
  observacao: '',
  itens: [
    {
      id_produto: null,
      quantidade: 1
    }
  ]
};

  this.telaAtual = 'solicitacoes';
  window.history.pushState({ tela: 'solicitacoes' }, '', '/sistema?tela=solicitacoes');

  this.mensagemSolicitacoes = `Solicitação #${resposta.id_solicitacao} criada com sucesso!`;

  this.carregarSolicitacoes();

  this.cdr.detectChanges();
},

    error: (erro) => {
      console.error('Erro ao criar solicitação:', erro);
      const detalhe = erro.error?.detail;

      this.criandoSolicitacao = false;
      this.erroNovaSolicitacao = typeof detalhe === 'string'
        ? detalhe
        : 'Não foi possível criar a solicitação.';
      this.cdr.detectChanges();
    }
  });
}

}
