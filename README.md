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
