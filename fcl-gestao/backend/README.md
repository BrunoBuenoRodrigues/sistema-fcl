# Backend do Sistema FCL

API FastAPI do Sistema Interno de Gestão de Compras e Entregas.

## Configuração

Crie o arquivo local de ambiente a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Configure no `.env`:

- `APP_ENV`: `development` ou `production`.
- `DATABASE_URL`: conexão com o PostgreSQL.
- `JWT_SECRET_KEY`: chave longa e exclusiva; é obrigatória em produção.
- `JWT_ALGORITHM`: algoritmo JWT, normalmente `HS256`.
- `TOKEN_EXPIRACAO_MINUTOS`: duração da sessão.
- `LOGIN_MAX_TENTATIVAS`: falhas permitidas antes do bloqueio temporário.
- `LOGIN_BLOQUEIO_MINUTOS`: duração do bloqueio de login.
- `CORS_ORIGINS`: origens permitidas, separadas por vírgula e sem barra final.
- `ADMIN_INICIAL_NOME`, `ADMIN_INICIAL_LOGIN` e `ADMIN_INICIAL_SENHA`: conta criada somente quando o login ainda não existe.

O `.env` está ignorado pelo Git e não deve ser enviado ao repositório.

## Execução

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API de desenvolvimento fica disponível em `http://127.0.0.1:8000`, com documentação em `/docs`.

Na inicialização, a API cria as tabelas ausentes. Alterações futuras em tabelas existentes devem continuar sendo aplicadas pelas migrações da pasta `migrations`.

## Testes

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
