# Sistema FCL

Implantação integrada do frontend Angular, da API FastAPI e do PostgreSQL.

## Pré-requisitos

- Docker Desktop com Docker Compose.

## Primeira execução

Na pasta raiz do projeto:

```powershell
.\scripts\configurar-docker.ps1
```

O script cria senhas aleatórias fortes sem exibi-las no terminal. Para uma configuração manual, copie `.env.docker.example` para `.env` e substitua as senhas de exemplo. Depois execute:

```powershell
docker compose up --build -d
docker compose ps
```

Abra `http://localhost:8080` e entre com `ADMIN_INICIAL_LOGIN` e `ADMIN_INICIAL_SENHA` definidos no `.env`.

Por padrão, `APP_HOST=127.0.0.1` restringe o acesso ao próprio computador. Isso é o mais indicado enquanto não houver domínio e HTTPS.

O backend cria as tabelas e o administrador inicial somente quando eles ainda não existem. Os dados do PostgreSQL e os anexos ficam preservados em volumes Docker.

## Operação

```powershell
docker compose logs -f
docker compose restart
docker compose down
```

`docker compose down` mantém os volumes e os dados. A remoção dos volumes deve ser feita apenas quando houver intenção de apagar definitivamente o banco e os anexos.

## Arquitetura

- `frontend`: Nginx na porta configurada por `APP_PORT`.
- `backend`: FastAPI disponível apenas na rede interna do Compose.
- `db`: PostgreSQL disponível apenas na rede interna do Compose.
- `/api`: encaminhado pelo Nginx para o backend.

## Acesso sem domínio

Continue usando `http://localhost:8080`. A publicação com HTTPS fica pendente até existir um domínio apontado para o servidor.

Se o sistema precisar ser acessado por outros computadores da mesma rede, altere `APP_HOST` para `0.0.0.0` no `.env`, recrie o serviço e acesse `http://IP-DESTE-COMPUTADOR:8080`. Esse modo usa HTTP sem criptografia e deve ficar restrito a uma rede local confiável; não encaminhe a porta 8080 no roteador.

## Proteções da instalação

- O login é bloqueado temporariamente após cinco falhas consecutivas do mesmo usuário e endereço de rede.
- Cada usuário pode alterar a própria senha pela tela `Minha conta`, confirmando a senha atual.
- Ao alterar ou redefinir uma senha, os tokens anteriores da conta são invalidados; na troca pela tela `Minha conta`, somente a sessão atual recebe um token renovado.
- A documentação interna da API fica desativada em produção.
- O endpoint de diagnóstico com o nome do banco também fica desativado em produção; somente o healthcheck mínimo permanece público.
- O Nginx adiciona políticas de segurança ao navegador e a API impede cache de respostas privadas.
- Entregadores listam, consultam e movimentam somente as entregas atribuídas à própria conta, e só baixam anexos e comprovantes vinculados a essas entregas.
- Uploads de entrega não vinculados são preservados por sete dias e depois removidos automaticamente; arquivos vinculados e nomes legados não são afetados. O prazo pode ser configurado por `ARQUIVO_ORFAO_RETENCAO_HORAS`.

## Auditoria

Administradores possuem uma tela central de auditoria com pesquisa, filtros por usuário responsável, tipo, ação e período, exportação CSV e identificação do autor de cada evento registrado no sistema. O arquivo exportado respeita todos os filtros e a ordenação selecionados. Cadastros, edições, ativações e desativações de clientes, fornecedores, produtos e usuários são registrados automaticamente, sem armazenar senhas no histórico.

## Notificações

Cada conta visualiza somente as próprias notificações. A central permite marcar uma notificação individual ou todas as pendentes como lidas, atualizando imediatamente os contadores do menu e do título da aba do navegador. Enquanto a sessão estiver ativa, novas notificações são consultadas automaticamente a cada minuto e geram um alerta interno com acesso direto à central.

## Resumo operacional

O painel inicial apresenta atalhos com as pendências pertinentes ao perfil conectado. Funcionários veem as próprias solicitações; Administrador e Estoque acompanham pedidos aguardando recebimento; entregadores veem somente suas entregas em aberto; e todos acompanham as próprias notificações não lidas.

## Divisão de compras

Uma solicitação aprovada pode gerar pedidos para fornecedores diferentes. Em cada pedido, o administrador escolhe os produtos e as quantidades, limitados ao saldo ainda não distribuído. A solicitação permanece `APROVADA` enquanto houver saldo e muda para `PEDIDO_REALIZADO` somente quando todos os seus itens estiverem totalmente incluídos em pedidos.

Pedidos ainda não recebidos podem ser cancelados pelo administrador mediante motivo obrigatório. O registro é preservado com status `CANCELADO`, identifica quem cancelou e quando, o evento fica disponível na auditoria e as quantidades retornam automaticamente ao saldo da solicitação.

Cada pedido possui uma linha do tempo na própria listagem. Ela registra a criação, o envio para recebimento, cada recebimento parcial ou total, estornos e cancelamento, com data e descrição do evento.

A consulta de pedidos permite filtrar por fornecedor e período, além da pesquisa, do status e da ordenação. O resultado pode ser exportado para CSV com uma linha por produto e as quantidades pedida, recebida e pendente, preservando também a solicitação de origem, observações e cancelamentos.

Enquanto estiver em `CRIADO`, um pedido pode ser corrigido pelo administrador. Fornecedor, número, data, observação, produtos e quantidades podem ser alterados dentro do saldo da solicitação; a solicitação e os históricos são atualizados automaticamente. Após o envio ao recebimento, a edição é bloqueada.

O número do pedido é único e essa regra é garantida também pelo PostgreSQL. Conflitos simultâneos de número do pedido, código de produto, CNPJ de fornecedor ou login de usuário retornam uma validação compreensível, sem expor erro interno.

Recebimentos lançados incorretamente podem ser estornados pelo administrador mediante motivo obrigatório. O registro original não é apagado: fica marcado como `ESTORNADO`, sai dos totais ativos e o saldo e o status do pedido são recalculados automaticamente.

Cada recebimento novo exige ao menos um item, não aceita o mesmo item repetido no lançamento e reserva o pedido durante a validação do saldo, evitando que operações simultâneas ultrapassem a quantidade pedida.

O histórico de recebimentos pode ser pesquisado por pedido, nota fiscal, observação, motivo de estorno ou produto, além de filtrado por status e período. O resultado é paginado e pode ser exportado para CSV, com uma linha por produto recebido e proteção contra fórmulas maliciosas.

Solicitações criadas por engano podem ser canceladas com motivo obrigatório. O solicitante pode cancelar a própria solicitação enquanto ela estiver em `SOLICITADA`; o administrador também pode cancelar em `EM_ANALISE` ou `APROVADA`, desde que não exista pedido ativo. O registro e seus itens são preservados com status `CANCELADA`.

Enquanto permanecer em `SOLICITADA`, a solicitação pode ser editada pelo solicitante ou pelo administrador. Prioridade, motivo, observação, produtos e quantidades podem ser corrigidos; todos os produtos são revalidados e a edição fica registrada na auditoria. Depois que a análise começa, a edição é bloqueada.

Cada solicitação possui uma linha do tempo consultável na própria listagem. O histórico registra cadastro, edição, início da análise, aprovação, rejeição, cancelamento e a criação ou o cancelamento de pedidos vinculados.

Entregas ainda não iniciadas em rota podem ser canceladas pelo administrador mediante motivo obrigatório. O registro e os anexos são preservados, o status passa para `CANCELADA`, o evento fica na auditoria e a entrega deixa de ser contabilizada como aberta ou atrasada.

O agendamento de uma entrega exige uma data atual ou futura. Enquanto a entrega ainda não entrou em rota, Funcionário, Estoque e Administrador podem alterar essa data pela própria listagem; o agendamento e cada reagendamento ficam registrados no histórico.

Enquanto estiver em `CADASTRADA`, `AGENDADA`, `EM_SEPARACAO` ou `PRONTA_PARA_ENTREGA`, uma entrega pode ser corrigida por Funcionário, Estoque ou Administrador. Cliente, entregador, data agendada e observação podem ser alterados, com registro no histórico; depois que a entrega entra em rota, a edição é bloqueada.

A listagem de entregas apresenta um resumo dos prazos em aberto, destaca entregas atrasadas e agendadas para o dia e permite filtrar por atraso, data atual, datas futuras ou ausência de agendamento. Também é possível ordenar as entregas pela data agendada mais próxima ou mais distante.

O endereço completo do cliente aparece em cada entrega. A listagem resultante da pesquisa e dos filtros pode ser exportada para CSV com cliente, endereço, telefone, entregador, agendamento, prazo, status e observação; entregadores exportam somente as entregas atribuídas à própria conta.

Para planejar as rotas, a listagem também pode ser filtrada por entregador e por uma data agendada exata, incluindo uma opção específica para entregas ainda sem responsável. O botão `Limpar filtros` restaura a visão geral, e o CSV sempre respeita a rota selecionada.

Cada entrega oferece atalhos operacionais para ligar para o telefone cadastrado do cliente e abrir o endereço completo diretamente no Google Maps. Os atalhos só aparecem quando os respectivos dados estão disponíveis.

Quando uma tentativa em rota não puder ser concluída, o entregador responsável ou o administrador pode registrar `NAO_ENTREGUE` com motivo obrigatório. O responsável pelo cadastro recebe uma notificação e a entrega pode ser reagendada para uma nova tentativa, mantendo todas as ocorrências no histórico.

## Backup e restauração

O serviço `backup` cria uma cópia assim que inicia e repete a operação a cada 24 horas. O intervalo e a retenção podem ser alterados no `.env` por meio de `BACKUP_INTERVALO_HORAS` e `BACKUP_RETENCAO_DIAS`.

Cada pasta dentro de `backups` contém:

- `banco.dump`: banco PostgreSQL em formato próprio para restauração.
- `anexos.tar.gz`: anexos e comprovantes enviados ao sistema.
- `checksums.sha256`: verificação de integridade dos dois arquivos.

Para criar uma cópia imediatamente:

```powershell
.\scripts\backup-agora.ps1
```

Para restaurar uma cópia, informe o nome da pasta. A confirmação explícita é obrigatória e um backup de segurança é criado antes da substituição:

```powershell
.\scripts\restaurar-backup.ps1 -Backup 20260913T120000Z -Confirmar
```

## Monitoramento e operação

O serviço `monitor` verifica continuamente o frontend, a API, o banco e a integridade do backup mais recente. Os logs possuem rotação automática para evitar crescimento ilimitado no disco.

Para consultar o estado atual:

```powershell
.\scripts\status-sistema.ps1
```

As rotinas de operação e recuperação estão descritas em `OPERACAO.md`.

## Homologação

Para verificar automaticamente a instalação após atualizações ou reinicializações:

```powershell
.\scripts\verificar-instalacao.ps1
```

O checklist funcional por perfil está em `HOMOLOGACAO.md`.
