# Operação do Sistema FCL

## Acesso

Com o Docker Desktop aberto, acesse `http://localhost:8080` e use uma credencial do sistema anterior.

## Consulta diária

Para visualizar os serviços, o monitor e o backup mais recente:

```powershell
.\scripts\status-sistema.ps1
```

O estado esperado dos serviços é `Up` ou `healthy`, e o monitor deve registrar `OK`.

## Verificação completa

Execute periodicamente, ou depois de uma atualização:

```powershell
.\scripts\verificar-instalacao.ps1
```

## Reinicialização segura

```powershell
docker compose restart
docker compose ps
```

Os volumes do banco e dos anexos permanecem preservados.

## Em caso de falha

1. Execute `.\scripts\status-sistema.ps1 -Linhas 100`.
2. Confirme que o Docker Desktop está aberto.
3. Execute `docker compose restart` e aguarde os healthchecks.
4. Execute `.\scripts\verificar-instalacao.ps1`.
5. Antes de qualquer restauração, preserve a pasta `backups` e identifique o último backup válido.

## Monitoramento automático

O serviço `monitor` verifica a cada cinco minutos:

- disponibilidade do frontend;
- disponibilidade da API e conexão com o banco;
- existência, idade e integridade do backup mais recente.

Os logs de todos os serviços possuem rotação automática, com cinco arquivos de até 10 MB por serviço. Os intervalos e limites podem ser alterados no `.env`.
