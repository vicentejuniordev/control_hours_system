# Controle de Horas — Sistema de Estágio

Sistema simples para controle de carga horária de estagiários, com dois fluxos de registro (Presencial e Home Office) no mesmo banco de dados.

## Stack

- **Backend:** Django 5
- **Banco:** SQLite (zero configuração, ideal para início)
- **Frontend:** Templates HTML + CSS
- **Exportação:** PDF (ReportLab) e Excel (OpenPyXL)

## Funcionalidades

### Estagiário
- Login e seleção do fluxo (Presencial ou Home Office)
- **Presencial:** registrar entrada → saída → horas calculadas automaticamente (suporta múltiplos turnos/dia)
- **Home Office:** informar horas, descrever atividades, anexar arquivo (opcional)
- Dashboard com horas previstas, realizadas, presenciais, home office e restantes
- Histórico de registros com filtros
- Relatórios por período com exportação PDF/Excel

### Supervisor
- Dashboard com lista de estagiários e horas cumpridas
- Filtros: Todos, Presencial, Home Office, Pendentes, Aprovados
- Aprovar ou rejeitar registros de home office (com motivo)
- Relatórios por estagiário

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo   # dados de demonstração
python manage.py runserver
```

Acesse: http://127.0.0.1:8000

## Produção (online) com SQLite

Para sua demanda (12 estagiários + 1 supervisor), SQLite atende bem se o deploy estiver correto.

### 1) Configurar variáveis de ambiente

No servidor, defina:

```bash
export DEBUG=False
export SECRET_KEY='gere-uma-chave-forte-aqui'
export ALLOWED_HOSTS='seu-dominio.com,www.seu-dominio.com,IP_DO_SERVIDOR'
export CSRF_TRUSTED_ORIGINS='https://seu-dominio.com,https://www.seu-dominio.com'
```

### 2) Preparar aplicação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 3) Subir com Gunicorn (teste rápido)

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 60
```

### 4) Serviço systemd (produção)

Crie `/etc/systemd/system/control-hours.service`:

```ini
[Unit]
Description=Control Hours Django (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/caminho/para/control_hours_system
Environment="DEBUG=False"
Environment="SECRET_KEY=gere-uma-chave-forte-aqui"
Environment="ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com,IP_DO_SERVIDOR"
Environment="CSRF_TRUSTED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com"
ExecStart=/caminho/para/control_hours_system/.venv/bin/gunicorn config.wsgi:application --workers 2 --bind unix:/run/control-hours.sock --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now control-hours
sudo systemctl status control-hours
```

### 5) Nginx

Crie `/etc/nginx/sites-available/control-hours`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;

    client_max_body_size 20M;

    location /static/ {
        alias /caminho/para/control_hours_system/staticfiles/;
    }

    location /media/ {
        alias /caminho/para/control_hours_system/media/;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/control-hours.sock;
    }
}
```

Ative o site:

```bash
sudo ln -s /etc/nginx/sites-available/control-hours /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6) HTTPS (recomendado)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com
```

### 7) Backup do SQLite

Exemplo diário:

```bash
sqlite3 db.sqlite3 ".backup '/caminho/backups/db-$(date +%F).sqlite3'"
```

> Dica: mantenha backup automático (cron) e retenção de 7 a 30 dias.

## Usuários de demonstração

| Perfil      | Usuário    | Senha          |
|-------------|------------|----------------|
| Supervisor  | supervisor | supervisor123  |
| Estagiário  | maria      | estagiario123  |
| Estagiário  | joao       | estagiario123  |
| Estagiário  | pedro      | estagiario123  |

## Cadastro via Admin

Acesse `/admin/` para cadastrar novos estagiários e supervisores. Crie primeiro o usuário (User) e vincule o perfil de estagiário com supervisor, carga horária e datas.

## Estrutura do banco

**Estagiário:** nome, curso, instituição, supervisor, carga_total, carga_semanal, início, fim

**Registro:** estagiario_id, tipo (PRESENCIAL/HOME_OFFICE), data, entrada, saída, horas, descrição, status (PENDENTE/APROVADO/REJEITADO), observação, anexo

## Fluxo

```
Login → Selecionar Presencial ou Home Office
  Presencial: Entrada → Saída → Horas calculadas
  Home Office: Horas + Descrição → Pendente → Supervisor aprova → Horas contabilizadas
```
