# Homologação do Sistema FCL

## Verificação técnica

Com o Docker Desktop aberto, execute na pasta raiz:

```powershell
.\scripts\verificar-instalacao.ps1
```

Para testar também uma credencial real sem exibir a senha:

```powershell
.\scripts\verificar-instalacao.ps1 -TestarLogin
```

O comando valida os serviços Docker, o frontend, a API, o PostgreSQL, as proteções de produção e o backup mais recente.

## Checklist funcional por perfil

### Administrador

- Entrar com uma conta administrativa antiga.
- Abrir `Minha conta` e confirmar que a troca de senha exige a senha atual.
- Após trocar uma senha, confirmar que outra sessão aberta da mesma conta é encerrada e que a sessão usada na alteração permanece conectada.
- Conferir usuários, produtos, fornecedores e relatórios.
- Abrir `Auditoria` e filtrar os eventos por usuário responsável, tipo, ação e período.
- Editar e desativar um cadastro de teste e confirmar os dois eventos na auditoria.
- Exportar a auditoria filtrada para CSV e abrir o arquivo em um editor de planilhas.
- Confirmar que os totais do painel correspondem aos registros migrados.
- Exportar um relatório CSV e abrir o arquivo.
- Dividir uma solicitação com dois produtos entre fornecedores diferentes e confirmar que os saldos diminuem sem duplicar quantidades.
- Cancelar um pedido sem recebimentos informando um motivo e confirmar que o motivo, a data e o responsável ficam registrados e que suas quantidades voltam ao saldo; tentar cancelar um pedido já recebido e confirmar o bloqueio.
- Editar um pedido em `CRIADO`, corrigindo fornecedor e quantidades, e confirmar a atualização dos saldos; enviá-lo para recebimento e confirmar que novas edições ficam bloqueadas.
- Tentar cadastrar ou editar dois pedidos com o mesmo número e confirmar que o segundo é recusado sem alterar o primeiro.
- Abrir `Ver histórico` em um pedido e conferir a criação, o envio para recebimento, os recebimentos parciais ou totais e eventuais estornos ou cancelamento.
- Filtrar pedidos por fornecedor e período, pesquisar um produto, limpar os filtros e exportar o CSV conferindo quantidades pedida, recebida e pendente.
- Cancelar uma entrega antes da rota informando um motivo; confirmar o histórico e tentar cancelar uma entrega em rota ou concluída para validar o bloqueio.
- Agendar uma entrega cadastrada, reagendá-la antes da rota e confirmar as duas datas no histórico; validar que uma data passada é recusada.
- Editar uma entrega antes da rota, corrigindo cliente, entregador, data e observação; confirmar o evento no histórico e o bloqueio após `EM_ROTA`.
- Conferir o resumo de prazos das entregas, os alertas de atraso e de entregas para hoje, os filtros por prazo e a ordenação por data agendada.
- Filtrar as entregas, exportar o CSV e conferir cliente, endereço, telefone, entregador, agendamento, prazo e status no arquivo gerado.
- Selecionar um entregador e uma data agendada para montar uma rota, testar a opção `Sem entregador`, exportar o resultado e restaurar a listagem com `Limpar filtros`.
- Em uma entrega com telefone e endereço completos, testar os atalhos de ligação e `Abrir no mapa`; confirmar que os atalhos ausentes não aparecem quando o cadastro não possui esses dados.

### Funcionário

- Conferir clientes e solicitações existentes.
- Criar uma solicitação real e confirmar que ela aparece na listagem.
- Cancelar uma solicitação própria ainda não analisada, informando o motivo, e confirmar que o registro continua na listagem como `CANCELADA`.
- Editar uma solicitação própria em `SOLICITADA`, alterando produtos e quantidades; iniciar a análise e confirmar que novas edições ficam bloqueadas.
- Abrir `Ver histórico` em uma solicitação e conferir a ordem dos eventos desde o cadastro até a decisão e os pedidos vinculados.
- Verificar o recebimento da notificação após aprovação ou rejeição.
- Usar `Marcar todas como lidas` e confirmar que o contador do menu é zerado.
- Manter a sessão aberta e confirmar que o contador recebe novas notificações sem atualizar a página.
- Confirmar que a quantidade não lida aparece no título da aba e some após a leitura.
- Confirmar que uma notificação recebida durante a sessão gera um alerta com o botão `Ver`.

### Estoque

- Conferir pedidos aguardando recebimento.
- Registrar as quantidades recebidas de um pedido real.
- Confirmar que um recebimento sem itens ou com o mesmo item repetido é recusado.
- Confirmar se o saldo pendente e o status foram atualizados corretamente.
- Pesquisar o histórico por pedido, nota fiscal e produto; filtrar por status e período, validar a paginação e exportar o CSV resultante.
- Como administrador, estornar um recebimento com motivo, confirmar a devolução do saldo e registrar novamente a quantidade correta.

### Entregador

- Conferir somente as entregas permitidas para o perfil.
- Confirmar com duas contas de entregador que uma não acessa a entrega atribuída à outra.
- Baixar o anexo e o comprovante da própria entrega e confirmar que outro entregador recebe acesso negado aos mesmos arquivos.
- Atualizar uma entrega real pelas etapas de rota.
- Anexar o comprovante quando a entrega for concluída.
- Confirmar que um endereço interno sem arquivo correspondente não pode ser vinculado como comprovante.
- Em uma entrega em rota, registrar uma tentativa não concluída com motivo e confirmar que o responsável foi notificado; depois reagendar e concluir uma nova tentativa.

## Critérios de aceite

- Nenhum perfil visualiza ou executa ações sem permissão.
- Cadastros e alterações continuam presentes após reiniciar o Docker.
- Notificações são geradas nas mudanças importantes do fluxo.
- Relatórios refletem as operações realizadas.
- O backup técnico termina sem falhas.
- O painel inicial mostra apenas indicadores compatíveis com o perfil conectado.

## Pendência conhecida da migração

O banco antigo contém 17 referências a anexos de pedidos, mas os arquivos correspondentes não estavam na instalação anterior. Os registros foram preservados; esses links antigos podem ficar indisponíveis.

A auditoria de 16/09/2026 também encontrou 12 solicitações, 1 pedido e 1 recebimento legados sem linhas de itens. Os registros foram preservados para não inventar nem apagar informações históricas. Novos cadastros e recebimentos sem itens são bloqueados pela API; a regularização dos registros antigos depende da conferência dos documentos de origem.
