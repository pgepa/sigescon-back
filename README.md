# 🚀 SIGESCON API - Sistema de Gestão de Contratos

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Produção-brightgreen)](README.md)

Sistema robusto de gestão de contratos desenvolvido com **FastAPI**, oferecendo uma API RESTful completa para gerenciamento do ciclo de vida de contratos, relatórios fiscais e fluxos de aprovação. **Projeto em produção** com todas as funcionalidades implementadas e testadas.

## 📑 Índice

- [🚀 SIGESCON API - Sistema de Gestão de Contratos](#-sigescon-api---sistema-de-gestão-de-contratos)
  - [📑 Índice](#-índice)
  - [✨ Características](#-características)
    - [Core Features](#core-features)
    - [Módulos Principais](#módulos-principais)
      - [👤 **Usuários**](#-usuários)
      - [📋 **Contratos**](#-contratos)
      - [📝 **Relatórios Fiscais**](#-relatórios-fiscais)
      - [⏰ **Pendências**](#-pendências)
  - [🏗 Arquitetura](#-arquitetura)
    - [Padrões Implementados](#padrões-implementados)
  - [🛠 Tecnologias](#-tecnologias)
    - [Backend](#backend)
    - [Database](#database)
    - [Testing](#testing)
  - [📋 Pré-requisitos](#-pré-requisitos)
  - [🚀 Instalação](#-instalação)
    - [1. Clone o repositório](#1-clone-o-repositório)
    - [2. Crie um ambiente virtual](#2-crie-um-ambiente-virtual)
    - [3. Instale as dependências](#3-instale-as-dependências)
    - [4. Configure o banco de dados](#4-configure-o-banco-de-dados)
  - [⚙️ Configuração](#️-configuração)
    - [1. Crie o arquivo .env na raiz do projeto](#1-crie-o-arquivo-env-na-raiz-do-projeto)
    - [2. Execute o seeder para dados iniciais](#2-execute-o-seeder-para-dados-iniciais)
  - [🏃 Execução](#-execução)
    - [Modo Desenvolvimento](#modo-desenvolvimento)
    - [Modo Produção](#modo-produção)
    - [Scheduler (Lembretes automáticos)](#scheduler-lembretes-automáticos)
  - [🧪 Testes](#-testes)
    - [Executar todos os testes](#executar-todos-os-testes)
    - [Script de validação completo](#script-de-validação-completo)
  - [📖 API Documentation](#-api-documentation)
    - [Endpoints Principais](#endpoints-principais)
      - [Autenticação](#autenticação)
      - [Usuários](#usuários)
      - [Contratos](#contratos)
      - [Relatórios](#relatórios)
      - [Pendências](#pendências)
      - [Arquivos](#arquivos)
      - [Tabelas Auxiliares](#tabelas-auxiliares)
  - [📁 Estrutura do Projeto](#-estrutura-do-projeto)
  - [🔄 Fluxo de Trabalho](#-fluxo-de-trabalho)
    - [Fluxo de Relatórios Fiscais](#fluxo-de-relatórios-fiscais)
    - [Níveis de Acesso](#níveis-de-acesso)
  - [💻 Desenvolvimento](#-desenvolvimento)
    - [Convenções de Código](#convenções-de-código)
    - [Comandos Úteis](#comandos-úteis)
    - [Variáveis de Ambiente para Desenvolvimento](#variáveis-de-ambiente-para-desenvolvimento)
  - [🚢 Deploy](#-deploy)
    - [Docker](#docker)
    - [Docker Compose](#docker-compose)
    - [Heroku](#heroku)
    - [Gunicorn com Uvicorn Workers](#gunicorn-com-uvicorn-workers)
  - [🤝 Contribuindo](#-contribuindo)
    - [Guidelines](#guidelines)
  - [📄 Licença](#-licença)
  - [👥 Autores](#-autores)
  - [🙏 Agradecimentos](#-agradecimentos)
  - [📞 Suporte](#-suporte)
  - [🔗 Links Úteis](#-links-úteis)

## ✨ Características

### Core Features
- 🔐 **Autenticação JWT** - Sistema seguro de autenticação com tokens e migração automática de senhas
- 👥 **Sistema de Perfis Múltiplos** - Permite que um único usuário possua vários perfis (ex: Gestor e Fiscal) com alternância de contexto e permissões dinâmicas
- 🔄 **Contexto de Sessão Ativo** - Alternância real entre perfis com persistência e isolamento automático de dados
- 🛡️ **Isolamento de Dados** - Fiscal vê apenas seus contratos, Gestor vê apenas os seus, Admin vê todos
- 📄 **Gestão de Contratos** - CRUD completo com validações avançadas e soft delete
- 📎 **Upload de Arquivos** - Suporte para múltiplos formatos com validação e organização automática
- 📊 **Relatórios Fiscais** - Fluxo completo de submissão, análise e aprovação/rejeição
- 📅 **Pendências e Prazos** - Sistema automatizado de notificações e lembretes
- 📧 **Notificações por Email** - Integração com SMTP para alertas automáticos personalizados
- 📈 **Paginação e Filtros** - Busca avançada e filtros dinâmicos em todos os módulos
- 🔄 **Soft Delete** - Preservação completa do histórico de dados
- ⚡ **100% Assíncrono** - Alta performance com asyncio e connection pooling
- 🔍 **Sistema de Auditoria** - Log completo de todas as ações críticas
- 📋 **Validações Avançadas** - CPF, CNPJ, datas, arquivos e regras de negócio
- 🎯 **Middleware Customizado** - Logging, auditoria e monitoramento de performance

### Módulos Principais

#### 👤 **Usuários**
- Criação e gestão de usuários com validações completas (sem dependência de estruturas legadas)
- Alteração e reset de senha (própria e administrativa)
- Sistema de múltiplos perfis com concessão/revogação dinâmica
- Contexto de sessão ativo com alternância real entre perfis
- Listagem paginada com filtros avançados
- Migração automática de senhas do sistema legado

#### 📋 **Contratos**
- Cadastro completo com múltiplos campos e validações
- **Upload múltiplo** de documentos contratuais (até 10 arquivos, 250MB total)
- **Gerenciamento de arquivos** - listar, baixar e excluir arquivos por contrato
- Associação com gestores, fiscais e substitutos
- Filtros avançados por data, status, responsáveis
- Controle de prazos e notificações de vencimento

#### 📝 **Relatórios Fiscais**
- Submissão por fiscais com upload de documentos
- Análise e aprovação/rejeição por administradores
- Sistema de reenvio em caso de rejeição com feedback
- Histórico completo de todas as versões
- Integração com sistema de pendências

#### ⏰ **Pendências**
- Criação automática e manual de tarefas para fiscais
- Controle rigoroso de prazos com múltiplos alertas
- Notificações automáticas em intervalos configuráveis
- Status de conclusão e histórico de alterações

## 🏗 Arquitetura

O projeto segue uma arquitetura em camadas (Clean Architecture) com separação clara de responsabilidades:

```
┌─────────────────┐
│   API Routes    │  ← FastAPI endpoints com validação
├─────────────────┤
│   Middlewares   │  ← Auditoria, CORS, tratamento de erros
├─────────────────┤
│    Services     │  ← Lógica de negócio e orquestração
├─────────────────┤
│  Repositories   │  ← Acesso a dados com queries otimizadas
├─────────────────┤
│    Database     │  ← PostgreSQL com connection pooling
└─────────────────┘
```

### Padrões Implementados
- **Repository Pattern** - Isolamento completo da camada de dados
- **Service Layer** - Centralização de toda lógica de negócio
- **Dependency Injection** - Injeção de dependências nativa do FastAPI
- **DTO Pattern** - Schemas Pydantic para validação e serialização
- **Async/Await** - Operações assíncronas em toda a aplicação
- **Exception Handling** - Tratamento centralizado de exceções customizadas
- **Middleware Pattern** - Cross-cutting concerns (logging, auditoria, CORS)

## 🛠 Tecnologias

### Backend
- **FastAPI** - Framework web moderno e de alta performance
- **Pydantic** - Validação de dados e serialização com type hints
- **asyncpg** - Driver PostgreSQL assíncrono de alta performance
- **python-jose** - Implementação JWT com criptografia
- **passlib + bcrypt** - Hashing seguro de senhas com migração automática
- **aiofiles** - Manipulação assíncrona de arquivos
- **aiosmtplib** - Envio assíncrono de emails
- **APScheduler** - Agendamento de tarefas e lembretes

### Database
- **PostgreSQL 14+** - Banco de dados relacional com índices otimizados
- **Connection Pooling** - Pool de conexões para alta performance
- **Soft Delete** - Preservação de histórico de dados
- **Índices Condicionais** - Otimização para registros ativos

### Testing
- **pytest** - Framework de testes robusto
- **pytest-asyncio** - Suporte completo para testes assíncronos
- **httpx** - Cliente HTTP assíncrono para testes de API
- **Fixtures** - Dados de teste organizados e reutilizáveis

## 📋 Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 14 ou superior
- pip ou uv (gerenciador de pacotes)
- Git

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/rafaelcostati/sigescon-fastapi.git
cd sigescon-fastapi
```

### 2. Crie um ambiente virtual
```bash
# Com venv
python -m venv .venv

# Ative o ambiente
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3. Instale as dependências
```bash
# Com pip
pip install -e .

# Ou com uv (mais rápido)
uv pip install -e .
```

### 4. Configure o banco de dados
```bash
# Acesse o PostgreSQL
psql -U postgres

# Crie o banco de dados
CREATE DATABASE sigescon;
\q

# Execute o script de criação das tabelas
psql -U postgres -d sigescon -f database/database.sql
```

## ⚙️ Configuração

### 1. Crie o arquivo .env na raiz do projeto
```env
# Banco de Dados
DATABASE_URL=postgresql://usuario:senha@localhost:5432/sigescon

# JWT
JWT_SECRET_KEY=sua_chave_secreta_muito_segura_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720

# CORS (opcional): origens do front, separadas por vírgula. Se omitido, permite qualquer origem
# e habilita Private Network Access no Chrome quando o Starlette suportar (útil se a API está em IP privado).
# CORS_ALLOW_ORIGINS=https://app.exemplo.gov.br,http://10.0.0.10:8080

# Admin padrão (criado pelo seeder)
ADMIN_EMAIL=admin@sigescon.com
ADMIN_PASSWORD=Admin@123

# Email (Opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=seu_email@gmail.com
SENDER_PASSWORD=sua_senha_app

# Testes (Opcional)
BASE_URL=http://localhost:8000
PDF_CONTRATO_PATH=tests/fixtures/contrato_teste.pdf
TXT_RELATORIO_PATH=tests/fixtures/relatorio_teste.txt
EMAIL_GESTOR=gestor.teste@example.com
EMAIL_FISCAL=fiscal.teste@example.com
```

### 2. Execute o seeder para dados iniciais
O seeder cria a base para o sistema de perfis, status e modalidades.
```bash
# Criar dados essenciais (perfis, status, etc.)
python -c "
import asyncio
import asyncpg
from app.seeder import seed_data
from app.core.config import settings

async def run_seeder():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    await seed_data(conn)
    await conn.close()

asyncio.run(run_seeder())
"
```

## 🗄️ Reset Completo do Banco (Desenvolvimento)

Para desenvolvimento e testes, você pode resetar completamente o banco e recriar com dados de exemplo:

### Opção 1: Script Interativo (Recomendado)
```bash
# Script completo com confirmação e logs detalhados
python scripts/reset_and_seed_database.py
```

### Opção 2: Script Shell
```bash
# Execução simplificada com verificações automáticas
./reset_database.sh
```

### Opção 3: SQL Direto
```bash
# Para quem prefere SQL puro
psql -U postgres -d contratos -f scripts/reset_database.sql
```

### Opção 4: Reset Rápido (CI/CD)
```bash
# Sem confirmação interativa
python scripts/quick_reset.py
```

**⚠️ ATENÇÃO:** Estes scripts **APAGAM TODOS OS DADOS**! Use apenas em desenvolvimento.

**📋 Dados criados após reset:**
- **3 usuários padrão** (admin, gestor, fiscal)
- **3 contratos de exemplo** com documentos
- **Tabelas de lookup** populadas
- **Pendências de teste** para workflow completo

**🔑 Credenciais padrão:**
- Admin: `admin@sigescon.gov.br` / `admin123`
- Gestor: `gestor@sigescon.gov.br` / `gestor123`
- Fiscal: `fiscal@sigescon.gov.br` / `fiscal123`

📖 **Documentação completa:** [docs/DATABASE_RESET.md](docs/DATABASE_RESET.md)

## 🏃 Execução

### Modo Desenvolvimento
```bash
# Com uvicorn (hot reload automático)
uvicorn app.main:app --reload --port 8000

# Com configurações customizadas
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Modo Produção
```bash
# Com workers para alta performance
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Ou com Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Scheduler (Lembretes automáticos)
```bash
# O scheduler é iniciado automaticamente com a aplicação
# Para executar separadamente (opcional):
python app/scheduler.py
```

## 🧪 Testes

### Executar todos os testes
```bash
# Testes básicos
pytest -sv --asyncio-mode=auto

# Com cobertura
pytest --cov=app tests/

# Testes específicos
pytest tests/test_contratos.py -v

# Com output detalhado
pytest -v -s
```

### Script de validação completo
```bash
# Torna o script executável
chmod +x run_tests.sh

# Executa validação completa
./run_tests.sh
```

## 📖 API Documentation

Com o servidor rodando, acesse:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Métricas**: [http://localhost:8000/metrics](http://localhost:8000/metrics)

### Endpoints Principais

#### Autenticação
- `POST /auth/login` - Realiza o login e retorna o token de acesso, incluindo o `contexto_sessao` com os perfis do usuário.
- `POST /auth/alternar-perfil` - Permite que o usuário alterne seu perfil de sessão atual.
- `GET /auth/contexto` - Retorna o contexto de sessão atual do usuário, incluindo perfil e permissões.
- `GET /auth/dashboard` - Retorna dados contextuais para o dashboard do usuário.
- `GET /auth/permissoes` - Retorna as permissões do usuário para o contexto de sessão atual.

#### Usuários
- `GET /api/v1/usuarios` - Listar usuários paginado com filtros (Admin)
- `POST /api/v1/usuarios` - Criar usuário (Admin)
- `GET /api/v1/usuarios/{id}` - Buscar usuário específico
- `PATCH /api/v1/usuarios/{id}` - Atualizar usuário (Admin)
- `DELETE /api/v1/usuarios/{id}` - Deletar usuário (Admin)
- `GET /api/v1/usuarios/me` - Dados do usuário logado
- `PATCH /api/v1/usuarios/{id}/alterar-senha` - Alterar própria senha
- `PATCH /api/v1/usuarios/{id}/resetar-senha` - Reset de senha (Admin)
- `GET /api/v1/usuarios/{usuario_id}/perfis` - Lista os perfis associados a um usuário.
- `POST /api/v1/usuarios/{usuario_id}/perfis/conceder` - Concede um ou mais perfis a um usuário.
- `POST /api/v1/usuarios/{usuario_id}/perfis/revogar` - Revoga um ou mais perfis de um usuário.

#### Contratos
- `GET /api/v1/contratos` - Listar contratos com filtros avançados e paginação
- `POST /api/v1/contratos` - Criar contrato com upload múltiplo (Admin)
- `GET /api/v1/contratos/{id}` - Detalhes completos do contrato
- `PATCH /api/v1/contratos/{id}` - Atualizar contrato com arquivos adicionais (Admin)
- `DELETE /api/v1/contratos/{id}` - Deletar contrato (Admin)

#### Gerenciamento de Arquivos
- `GET /api/v1/contratos/{id}/arquivos` - Listar arquivos do contrato
- `GET /api/v1/contratos/{id}/arquivos/{arquivo_id}/download` - Download de arquivo
- `DELETE /api/v1/contratos/{id}/arquivos/{arquivo_id}` - Excluir arquivo (Admin)
- `GET /api/v1/arquivos/relatorios/contrato/{id}` - **NOVO** - Listar arquivos de relatórios separadamente

#### Relatórios e Pendências
- `GET /api/v1/contratos/{id}/relatorios` - Listar relatórios do contrato
- `POST /api/v1/contratos/{id}/relatorios` - Submeter relatório com arquivo (Fiscal/Admin)
- `PATCH /api/v1/contratos/{id}/relatorios/{id}/analise` - **ATUALIZADO** - Analisar relatório (aprovar/rejeitar)
- `GET /api/v1/contratos/{id}/pendencias` - Listar pendências do contrato
- `POST /api/v1/contratos/{id}/pendencias` - Criar pendência (Admin)
- `PATCH /api/v1/contratos/{id}/pendencias/{id}/cancelar` - **NOVO** - Cancelar pendência (Admin)
- `GET /api/v1/contratos/{id}/pendencias/contador` - **NOVO** - Contador por status para dashboard

#### Dashboard do Fiscal
- `GET /api/v1/dashboard/fiscal/minhas-pendencias` - **NOVO** - Pendências específicas do fiscal logado
- `GET /api/v1/dashboard/fiscal/completo` - **NOVO** - Dashboard completo do fiscal

#### Arquivos
- `GET /api/v1/arquivos/{id}/download` - Download de arquivos com controle de acesso

#### Termos Aditivos e Robô de Sincronização
- `GET /api/v1/tipos-termo-aditivo` - Listar tipos de termo aditivo (1 - Prazo, 2 - Valor, 3 - Misto, 4 - Outros)
- `GET /api/v1/contratos/{id}/aditivos` - Listar termos aditivos do contrato
- `POST /api/v1/contratos/{id}/aditivos` - Criar termo aditivo com validação de tipo e inativação seletiva
- `GET /api/v1/contratos/{id}/aditivos/{aditivo_id}` - Buscar termo aditivo por ID
- `PATCH /api/v1/contratos/{id}/aditivos/{aditivo_id}` - Atualizar termo aditivo
- `DELETE /api/v1/contratos/{id}/aditivos/{aditivo_id}` - Inativar termo aditivo (soft delete)
- `DELETE /api/v1/contratos/{id}/aditivos/{aditivo_id}/permanente` - Excluir definitivamente (hard delete)
- `POST /api/v1/contratos/{id}/aditivos/{aditivo_id}/arquivo` - Upload de arquivo vinculado ao aditivo
- `GET /api/v1/aditivos/relatorio` - Relatório consolidado de termos aditivos de todos os contratos

#### Tabelas Auxiliares
- `GET /api/v1/tipos-termo-aditivo` - Listar tipos de termo aditivo (FK)
- `GET /api/v1/perfis` - Listar perfis de usuário
- `GET /api/v1/modalidades` - Listar modalidades de contratação
- `GET /api/v1/status` - Listar status de contratos
- `GET /api/v1/statusrelatorio` - Listar status de relatórios
- `GET /api/v1/statuspendencia` - Listar status de pendências
- `GET /api/v1/contratados` - Listar contratados com paginação

## 📁 Estrutura do Projeto

```
sigescon-fastapi/
├── app/
│   ├── api/
│   │   ├── dependencies.py         # Injeção de dependências
│   │   ├── permissions.py          # Controle de permissões
│   │   ├── doc_dependencies.py     # Proteção da documentação
│   │   ├── exception_handlers.py   # Tratamento de exceções
│   │   └── routers/                # Endpoints da API
│   │       ├── auth_router.py
│   │       ├── contrato_router.py
│   │       ├── usuario_router.py
│   │       ├── arquivo_router.py
│   │       └── ...
│   ├── core/
│   │   ├── config.py              # Configurações globais
│   │   ├── database.py            # Pool de conexões
│   │   ├── security.py            # JWT e hashing
│   │   └── exceptions.py          # Exceções customizadas
│   ├── middleware/
│   │   ├── audit.py               # Middleware de auditoria
│   │   └── logging.py             # Configuração de logs
│   ├── repositories/              # Camada de dados
│   │   ├── usuario_repo.py
│   │   ├── contrato_repo.py
│   │   └── ...
│   ├── schemas/                   # Modelos Pydantic
│   │   ├── usuario_schema.py
│   │   ├── contrato_schema.py
│   │   └── ...
│   ├── services/                  # Lógica de negócio
│   │   ├── usuario_service.py
│   │   ├── contrato_service.py
│   │   ├── email_service.py
│   │   ├── file_service.py
│   │   └── notification_service.py
│   ├── main.py                   # Aplicação FastAPI
│   ├── seeder.py                 # Popular dados iniciais
│   └── scheduler.py              # Tarefas agendadas
├── database/
│   └── database.sql              # Script completo do banco
├── tests/                        # Testes automatizados
│   ├── conftest.py
│   ├── test_usuarios.py
│   ├── test_contratos.py
│   ├── test_auth.py
│   └── fixtures/                 # Arquivos de teste
├── uploads/                      # Arquivos enviados
├── logs/                         # Arquivos de log
├── .env.example                  # Exemplo de configuração
├── .gitignore
├── pyproject.toml                # Configuração do projeto
├── pytest.ini                   # Configuração de testes
├── README.md
└── run_tests.sh                  # Script de validação
```

## 🔄 Fluxo de Trabalho

### Fluxo de Relatórios Fiscais

```mermaid
graph LR
    A[Admin cria Pendência<br/>Status: Pendente] --> B[Fiscal recebe email]
    B --> C{Fiscal responde}
    C -->|Envia Relatório + PDF| D[Relatório: Pendente de Análise<br/>Pendência: Aguardando Análise]
    C -->|Não responde| E[Lembrete automático]
    E --> C
    A --> F[Admin pode cancelar]
    F --> G[Fiscal recebe email de cancelamento]
    D --> H[Admin analisa relatório]
    H --> I{Decisão}
    I -->|Aprova| J[Relatório: Aprovado<br/>Pendência: Concluída]
    I -->|Rejeita| K[Relatório: Rejeitado<br/>Pendência: volta para Pendente]
    K --> L[Fiscal recebe feedback]
    L --> M[Fiscal reenvia<br/>Substitui arquivo anterior]
    M --> D
    J --> N[Fiscal recebe confirmação]
```

### 🆕 Principais Melhorias no Fluxo de Pendências

#### **Cancelamento de Pendências**
- Administradores podem cancelar pendências via `PATCH /contratos/{id}/pendencias/{id}/cancelar`
- Fiscal recebe notificação automática por email
- Status muda para "Cancelada" e não requer mais ação do fiscal

#### **Upload e Gestão de Relatórios com Arquivos**
- Fiscais podem enviar PDFs, DOCs, XLS ou qualquer arquivo como resposta
- **Reenvio inteligente**: Novo arquivo substitui automaticamente o anterior
- **Visualização separada**: Arquivos de relatórios ficam separados dos arquivos contratuais
- Endpoint dedicado: `GET /arquivos/relatorios/contrato/{id}`

#### **Análise Aprimorada pelo Administrador**
- **Aprovar**: Relatório aceito, pendência finalizada
- **Rejeitar**: Com observações, fiscal pode corrigir e reenviar
- Notificações automáticas por email em todas as decisões

#### **Dashboard com Contadores**
- Endpoint `GET /pendencias/contador` retorna estatísticas em tempo real
- Permite exibir badges no frontend: "Pendências(3)" se houver ações necessárias
- **Novos Status de Pendências:**
  - **Pendente**: Aguardando envio de relatório pelo fiscal
  - **Aguardando Análise**: Relatório enviado, aguardando análise do administrador
  - **Concluída**: Relatório aprovado pelo administrador
  - **Cancelada**: Pendência cancelada pelo administrador

### Níveis de Acesso

O sistema utiliza um modelo de perfis flexível com **isolamento automático de dados**, onde um usuário pode ter múltiplos papéis e alternar entre eles com persistência real. As permissões são contextuais, baseadas no perfil que está ativo na sessão do usuário.

| Perfil        | Permissões Principais (quando ativo) | Isolamento de Dados |
|---------------|------------------------------------------------------|---------------------|
| **Administrador** | Acesso total ao sistema, incluindo criação de usuários, gestão de perfis e aprovação de relatórios. | Vê **todos** os contratos |
| **Gestor** | Visualização e gestão de contratos sob sua responsabilidade, análise de relatórios da sua equipe. | Vê **apenas** contratos onde é gestor |
| **Fiscal** | Submissão de relatórios para seus contratos designados e visualização de pendências. | Vê **apenas** contratos onde é fiscal/substituto |

#### **Exemplo Prático de Isolamento:**
```
Usuário: João Silva
- Fiscal nos contratos: CON-001, CON-002
- Gestor no contrato: CON-003

Sessão como Fiscal (perfil ativo):
GET /api/v1/contratos/ → Retorna apenas CON-001 e CON-002

Alterna para Gestor:
POST /auth/alternar-perfil {"novo_perfil_id": 2}

Sessão como Gestor (perfil ativo):
GET /api/v1/contratos/ → Retorna apenas CON-003
```

A alternância entre perfis é **persistente** e **automática**, não requerendo logout e garantindo isolamento rigoroso dos dados.

## 💻 Desenvolvimento

### Convenções de Código

- **PEP 8** - Style guide para Python rigorosamente seguido
- **Type Hints** - Tipagem completa em todas as funções
- **Docstrings** - Documentação detalhada em todos os módulos
- **Async/Await** - Para todas as operações I/O sem exceção
- **Error Handling** - Tratamento específico para cada tipo de erro
- **Soft Delete** - Preservação de dados em todas as entidades

### Comandos Úteis

```bash
# Formatar código
black app/ tests/

# Verificar tipos
mypy app/

# Ordenar imports
isort app/ tests/

# Verificar estilo
flake8 app/ tests/

# Executar todos os testes
pytest

# Executar servidor de desenvolvimento
uvicorn app.main:app --reload
```

### Variáveis de Ambiente para Desenvolvimento

```bash
# Debug mode
export DEBUG=True

# Log level
export LOG_LEVEL=DEBUG

# Reload on changes
export RELOAD=True
```

## 🚢 Deploy

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/sigescon
      - JWT_SECRET_KEY=your-secret-key
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=sigescon
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Heroku

```bash
# Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Gunicorn com Uvicorn Workers

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Guidelines

- Escreva testes para todas as novas funcionalidades
- Mantenha a cobertura de testes acima de 80%
- Siga rigorosamente as convenções de código do projeto
- Atualize a documentação quando necessário
- Use type hints em todo o código
- Implemente tratamento de erros adequado

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores

- **Rafael Costa** - *Desenvolvimento e Arquitetura* - [@rafaelcostati](https://github.com/rafaelcostati)

## 🙏 Agradecimentos

- FastAPI pela excelente framework e performance
- Comunidade Python pelo suporte e bibliotecas
- PostgreSQL pela robustez e confiabilidade
- Todos os contribuidores e testadores

## 📞 Suporte

Para suporte técnico:
- 📧 Email: suporte.sigescon@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/rafaelcostati/sigescon-fastapi/issues)
- 📖 Documentação: Acesse `/docs` com o servidor rodando

## 📚 Documentação Adicional

### Documentação Completa
- **`CLAUDE.md`** - Documentação técnica detalhada da API, arquitetura e funcionalidades
- **`FLUXO_USUARIOS_MULTIPLOS_PERFIS.md`** - Guia completo para implementação do frontend React TypeScript

### Funcionalidades Documentadas
- ✅ **Sistema de Pendências e Relatórios** - Fluxo completo com upload de arquivos
- ✅ **Múltiplos Perfis por Usuário** - Alternância de contexto sem logout
- ✅ **Sistema de Notificações** - Templates de email para todas as ações
- ✅ **Gerenciamento de Arquivos** - Separação entre arquivos contratuais e de relatórios
- ✅ **Dashboard Inteligente** - Contadores em tempo real por status

## 🔗 Links Úteis

- [Documentação FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Pydantic](https://pydantic-docs.helpmanual.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pytest Documentation](https://docs.pytest.org/en/latest/)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/current/)