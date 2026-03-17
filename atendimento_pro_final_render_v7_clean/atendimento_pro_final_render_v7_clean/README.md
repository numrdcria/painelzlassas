# Atendimento Pro

Sistema web para:
- cadastro de clientes com data de vencimento
- historico de atendimentos
- cobrancas com Mercado Pago
- mensagem pronta de renovacao no WhatsApp
- alertas automaticos de vencimento dentro do painel
- ponto da funcionaria
- login com perfis de administrador e funcionaria

## Rodar no Windows sem Docker

No PowerShell:

```powershell
.\rodar_windows.ps1
```

Se o PowerShell bloquear script, rode:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Ou use:

```powershell
.\rodar_windows.bat
```

Acesse:

```text
http://127.0.0.1:8000
```

Login inicial:

```text
admin@empresa.com
123456
```

## Rodar com Docker

```bash
docker compose up --build
```

## Configuracao Mercado Pago

Edite o arquivo `.env` e preencha:

```env
MP_ACCESS_TOKEN=
MP_WEBHOOK_SECRET=
APP_BASE_URL=https://seu-dominio.com
```

## Banco de dados

- No Windows sem Docker, o sistema usa SQLite local.
- Com Docker, o sistema usa PostgreSQL com volume persistente.

## Funcoes adicionadas nesta versao

- visual mais bonito
- remover clientes
- mensagem pronta de renovacao no WhatsApp
- alertas automaticos de vencimento
- botao de gerar cobranca
- botao de WhatsApp manual
