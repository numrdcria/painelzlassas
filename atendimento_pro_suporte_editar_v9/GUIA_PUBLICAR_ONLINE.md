# Publicar online

## Melhor caminho para iniciantes

Use Render ou Railway com PostgreSQL gerenciado.

### Variáveis de ambiente

Configure na hospedagem:
- SECRET_KEY
- DATABASE_URL
- APP_BASE_URL
- COMPANY_NAME
- COMPANY_WHATSAPP
- ADMIN_NAME
- ADMIN_EMAIL
- ADMIN_PASSWORD
- MP_ACCESS_TOKEN
- MP_WEBHOOK_SECRET
- ALERT_WINDOW_DAYS

### Banco

Use PostgreSQL gerenciado da própria plataforma.

### Domínio

Depois que o site abrir, aponte seu domínio e atualize APP_BASE_URL.

### Mercado Pago

Configure os webhooks com a URL: https://SEU-DOMINIO/webhooks/mercadopago
