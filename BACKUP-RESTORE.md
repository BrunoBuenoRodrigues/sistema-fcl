# Backup e teste de restauração do Sistema FCL

## Escopo e estado verificado

O estado de produção usa PostgreSQL 16 em volume Docker `postgres_data` e mantém anexos em volume separado `uploads_data`. O container atualmente em execução ainda está montado em `./backups` dentro do repositório, que pode ser sincronizado pelo OneDrive. A configuração Compose preparada nesta auditoria aponta os próximos containers de backup e monitor para `%LOCALAPPDATA%\SistemaFCL\Backups\Automaticos`. Backups manuais ficam no diretório pai e não são montados nos containers. As cópias antigas em `./backups` foram preservadas e não movidas nem apagadas.

Em 27/09/2026 foi criada e validada uma cópia adicional em `%LOCALAPPDATA%\SistemaFCL\Backups\<UTC>`, fora do repositório e da pasta OneDrive. Ela contém `database.dump` (formato custom), `attachments.tar.gz`, `config.env` (credenciais), `compose.yaml`, `manifest.txt` (versão, contagens exatas, constraints, chaves estrangeiras, sequências e quantidade de usuários) e `SHA256SUMS`. Trate toda a pasta como segredo; não a envie por e-mail, GitHub ou armazenamento sincronizado sem criptografia.

O script antigo de restauração (`scripts/restaurar-backup.ps1`) para serviços e substitui o banco/anexos configurados no Compose. Ele não é adequado para teste. Não foi executado nesta auditoria. Os scripts de teste abaixo usam um container PostgreSQL descartável, rede `none`, armazenamento temporário em memória e sem portas publicadas ou volumes de produção.

## Criar, verificar e provar uma restauração

No PowerShell, com Docker Desktop aberto e o sistema em execução:

```powershell
.scriptsackup-completo.ps1
.scriptserificar-backup.ps1 -Backup "$env:LOCALAPPDATA\SistemaFCL\Backups\<UTC>"
.scripts	estar-restauracao-isolada.ps1 -Backup "$env:LOCALAPPDATA\SistemaFCL\Backups\<UTC>"
```

`backup-completo.ps1` usa `pg_dump -Fc`, coleta também os arquivos montados em `/app/uploads`, copia `.env` sem exibir seu conteúdo, grava contagens exatas e hashes, cria uma pasta única e não substitui nem apaga cópias antigas. O destino manual padrão é LocalAppData; um destino customizado precisa ficar fora do repositório.

`verificar-backup.ps1` confere os arquivos obrigatórios e SHA-256, lista o catálogo via `pg_restore -l` e testa a leitura do tar de anexos. `testar-restauracao-isolada.ps1` restaura em PostgreSQL 16 sem rede/portas, compara contagens de todas as tabelas, constraints, chaves estrangeiras, sequências e número de usuários, extrai os anexos e verifica referências de arquivos da tabela de entregas. Ao final, para somente o container identificado pela etiqueta do teste; seu armazenamento é temporário em memória. Nenhum registro de produção é alterado.

## Agendamento, retenção e recuperação

O serviço Compose continua configurado para criar backups automáticos a cada 24 horas. A configuração nova monta a mesma pasta local externa no backup e no monitor, que aceita os formatos de backup automático e manual. O monitor atual reportou-se não saudável porque o container ainda observa a pasta antiga e o backup automático mais recente visto ali tinha mais de 26 horas. Não reinicie/recrie os serviços sem janela de manutenção: isso será necessário para aplicar as novas montagens e o loop com novas tentativas.

O script do próximo backup automático no container ativo foi atualizado sem reinício e conferido por SHA-256 para não excluir cópias antigas. O loop ativo ainda está dormindo no intervalo de 24 horas e, após uma falha, só tentará novamente no ciclo seguinte. O código-fonte do loop foi ajustado para repetir tentativas a cada cinco minutos, mas essa parte só será carregada quando o serviço for recriado em uma janela aprovada.

Não existe limpeza automática nos novos scripts. Como política inicial, proponho backups diários com retenção de 30 diários e 12 mensais, removidos manualmente somente após confirmar uma cópia recente verificada e aprovar a remoção. LocalAppData protege contra sincronização acidental e vazamento pelo Git, mas não protege contra perda/avaria deste computador. Após validação, copie uma versão criptografada para mídia externa/off-site; não automatize o envio nesta etapa.

Restauração para uso real é uma operação de manutenção: requer cópia atual adicional, confirmação do destino, parada planejada de escrita, restauração coordenada do banco e anexos e validação do sistema antes de reabrir o acesso. O script de restauração atual aponta para os serviços/volumes do Compose e pode sobrescrever dados. Não o execute como teste, nem use `docker compose down -v`, limpeza de volumes, `pg_restore --clean` ou comandos SQL destrutivos.

## Diagnóstico do backup automático

Identifique os serviços e leia logs sem mostrar o arquivo `.env`:

```powershell
docker compose ps backup monitor db backend frontend
docker compose logs --tail 100 backup monitor
docker compose config --quiet
```

O monitor considera o backup mais recente pelo nome UTC da pasta e verifica a idade pelo horário de modificação da pasta, os nomes/formato reconhecidos, os checksums SHA-256, se `pg_restore --list` consegue ler o dump e se `tar -tzf` consegue ler os anexos. Ele também verifica frontend e API; portanto, `unhealthy` pode apontar para esses serviços, não apenas para o backup. A cópia de teste manual tem o mesmo formato que o monitor reconhece.

Se os logs mostrarem falha de conexão com o banco, confira `docker compose ps db backend` e aguarde os healthchecks; o loop atual tenta novamente em cinco minutos após falha. Se a mensagem for checksum/formato, não substitua nem apague a cópia: execute `verificar-backup.ps1` e `testar-restauracao-isolada.ps1` sobre ela. Se o monitor reportar backup antigo, confirme que backup e monitor montam `%LOCALAPPDATA%\SistemaFCL\Backups\Automaticos` (`docker compose config`) e que existe ali uma pasta UTC recente com os arquivos íntegros.

Após uma janela aprovada para atualizar somente esses dois serviços, os comandos são:

```powershell
docker compose build backup monitor
docker compose up -d --no-deps --force-recreate backup monitor
docker compose ps backup monitor db backend frontend
docker compose logs --since 10m backup monitor
```

`--no-deps` impede que o Compose recrie `db`, `backend` ou `frontend`; não use `down` nem remova volumes. O container `backup` executa uma tentativa logo ao iniciar. Aguarde o log de sucesso, depois ao menos um intervalo do monitor (padrão cinco minutos) e confirme estado `healthy` e logs `OK`. Se não ficar healthy, preserve logs e todos os backups para diagnóstico.
