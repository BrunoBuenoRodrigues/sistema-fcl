# Frontend do Sistema FCL

Aplicação Angular do Sistema Interno de Gestão de Compras e Entregas.

## Ambientes

- Desenvolvimento: usa `http://127.0.0.1:8000`, definido em `src/environments/environment.ts`.
- Produção: usa `/api`, definido em `src/environments/environment.production.ts`.

O build de produção substitui automaticamente o arquivo de desenvolvimento. Em uma implantação no mesmo domínio, configure o servidor web para encaminhar `/api` ao backend removendo esse prefixo. Se a API estiver em outro domínio, altere `apiUrl` no arquivo de produção antes do build.

## Comandos

```bash
npm install
npm start
npm run build:dev
npm run build:prod
npm test -- --watch=false
```

O servidor de desenvolvimento fica disponível em `http://localhost:4200`. Os arquivos do build são gerados em `dist/frontend`.

A aplicação usa um shell mínimo e rotas sob demanda. A tela de login possui um pacote próprio e o módulo operacional só é baixado após a autenticação; sessões salvas seguem diretamente para o sistema e são revalidadas pela API.
