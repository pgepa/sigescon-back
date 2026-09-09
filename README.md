# 🚀 SIGESCON API - Sistema de Gestão de Contratos

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-blue)](https://www.postgresql.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-orange)](https://alembic.sqlalchemy.org/)
[![Status](https://img.shields.io/badge/Status-Produção-brightgreen)](README.md)

API RESTful de alta performance desenvolvida em **FastAPI** para o gerenciamento completo do ciclo de vida de contratos administrativos, termos aditivos, relatórios de fiscalização e pendências da **Procuradoria-Geral do Estado do Pará (PGE-PA)**.

---

## 📑 Índice

- [✨ Características](#-características)
  - [Core Features](#core-features)
  - [Módulos Principais](#módulos-principais)
- [🏗 Arquitetura](#-arquitetura)
  - [Padrões Implementados](#padrões-implementados)
- [🛠 Tecnologias](#-tecnologias)
- [📋 Pré-requisitos](#-pré-requisitos)
- [🚀 Instalação Passo a Passo](#-instalação-passo-a-passo)
  - [1. Clone o repositório](#1-clone-o-repositório)
  - [2. Crie e ative o ambiente virtual](#2-crie-e-ative-o-ambiente-virtual)
  - [3. Instale as dependências](#3-instale-as-dependências)
  - [4. Configure o banco de dados PostgreSQL](#4-configure-o-banco-de-dados-postgresql)
  - [5. Configure as variáveis de ambiente (.env)](#5-configure-as-variáveis-de-ambiente-env)
  - [6. Execute as migrações com Alembic](#6-execute-as-migrações-com-alembic)
  - [7. Execute o Seeder de dados iniciais](#7-execute-o-seeder-de-dados-iniciais)
- [🏃 Execução do Servidor](#-execução-do-servidor)
  - [Modo Desenvolvimento](#modo-desenvolvimento)
  - [Modo Produção](#modo-produção)
- [🧪 Testes Automatizados](#-testes-automatizados)
- [📖 Documentação da API](#-documentação-da-api)
  - [Endpoints Principais](#endpoints-principais)
- [📐 Regras de Negócio](#-regras-de-negócio)
  - [Módulo de Termos Aditivos](#módulo-de-termos-aditivos)
  - [Múltiplos Perfis e Isolamento de Dados](#múltiplos-perfis-e-isolamento-de-dados)
  - [Fluxo de Relatórios Fiscais e Pendências](#fluxo-de-relatórios-fiscais-e-pendências)
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)
- [💻 Desenvolvimento](#-desenvolvimento)
- [🤝 Contribuindo](#-contribuindo)
- [📄 Licença](#-licença)

---

## ✨ Características

### Core Features
- 🔐 **Autenticação JWT Segura**: Geração de tokens de acesso com suporte a expiração configurável e hash de senhas via bcrypt.
- 👥 **Múltiplos Perfis por Usuário**: Suporte a múltiplos papéis (Administrador, Gestor, Fiscal) atribuídos a um único usuário, com alternância instantânea de contexto em sessão sem necessidade de logout.
- 🛡️ **Isolamento Automático de Dados**: Filtragem contextual em nível de repositório — Fiscais acessam estritamente seus contratos designados, Gestores visualizam seus contratos supervisionados e Administradores mantêm visão global.
- 📋 **Gestão do Ciclo de Vida Contratual**: Controle de vigência, prorrogações, garantias, modalidades, anexos contratuais e soft delete com preservação de integridade.
- 📑 **Termos Aditivos Avançados**: Tratamento especializado de aditivos de **Prazo**, **Valor**, **Misto** e **Outros**, com preservação permanente das datas originais do contrato, obrigatoriedade de campos de vigência, recálculo financeiro dinâmico e controle de coexistência de status (`Ativo`, `Inativo`, `Vencido`).
- 📝 **Fluxo de Fiscalização e Relatórios**: Submissão de relatórios mensais pelos fiscais com envio de evidências em anexo, análise com aprovação/rejeição motivada por Administradores e ciclo de reenvio inteligente.
- ⏰ **Pendências Automatizadas**: Criação e encerramento automático de pendências contratuais vinculado à submissão e análise dos relatórios.
- 🗄️ **Migrações Automatizadas (Alembic)**: Execução automática de migrações pendentes no startup da aplicação (`lifespan`), garantindo sincronia contínua do banco em qualquer ambiente.
- ⚡ **100% Assíncrono**: Alto rendimento com `FastAPI`, `asyncpg` e connection pooling nativo para PostgreSQL.
- 🔍 **Auditoria Integrada**: Rastreabilidade de alterações críticas por usuário, data/hora e IP.

---

### Módulos Principais

#### 👤 **Usuários e Múltiplos Perfis**
- CRUD completo de operadores e colaboradores.
- Concessão e revogação dinâmica de perfis (`POST /api/v1/usuarios/{id}/perfis/conceder` e `/revogar`).
- Alternância de contexto de sessão ativo via `POST /auth/alternar-perfil`.
- Consulta do contexto de sessão e permissões via `GET /auth/contexto`.
- Alteração da própria senha e reset administrativo de senhas.

#### 📋 **Contratos**
- Cadastro de contratos com upload múltiplo de documentos (até 10 arquivos / 250 MB total).
- Designação de Gestor, Fiscal Titular e Fiscais Substitutos.
- Armazenamento imutável de `data_inicio_original` e `data_fim_original` ao registrar termos aditivos.
- Soft delete de contratos e restauração com validações de integridade.
- Download, listagem e exclusão individual de anexos contratuais.

#### 📑 **Termos Aditivos**
- Tipificação por natureza: **1 - Prazo**, **2 - Valor**, **3 - Misto**, **4 - Outros**.
- Exigência estrita de **Nova Data Início** e **Nova Data Fim** para aditivos de Prazo e Misto.
- Atualização em cascata do contrato vigente mantendo as datas contratuais originais intactas para auditoria.
- Coexistência de status: um aditivo de Valor não inativa um aditivo de Prazo vigente, permitindo que a vigência estendida permaneça com status `Ativo`.
- Recálculo contínuo do valor global do contrato a partir dos aditivos financeiros.
- Relatório analítico consolidado de termos aditivos (`GET /api/v1/aditivos/relatorio`).

#### 📝 **Relatórios Fiscais e Pendências**
- Submissão de relatórios pelos fiscais acompanhados de arquivos comprobatórios.
- Avaliação administrativa (Aprovar / Rejeitar com justificativa).
- Encerramento automático da pendência correspondente após aprovação do relatório.
- Reenvio com substituição de anexo em caso de relatório devolvido para correção.

---

## 🏗 Arquitetura

O sistema é estruturado conforme os princípios da **Clean Architecture**, dividindo responsabilidades de forma explícita:

```
┌──────────────────────────────────────────────┐
│                 API Routes                   │  ← Endpoints FastAPI, validação DTO (Pydantic)
├──────────────────────────────────────────────┤
│                 Middlewares                  │  ← Auditoria, CORS, Logging, Exception Handlers
├──────────────────────────────────────────────┤
│                Service Layer                 │  ← Regras de negócio, cálculos, validações
├──────────────────────────────────────────────┤
│              Repository Layer                │  ← Queries otimizadas em AsyncPG e isolamento
├──────────────────────────────────────────────┤
│            PostgreSQL 14+ / Alembic          │  ← Schema versionado e Connection Pooling
└──────────────────────────────────────────────┘
```

### Padrões Implementados
- **Repository Pattern**: Desacoplamento entre o acesso a dados e a camada de serviços.
- **Service Layer**: Centralização e reutilização de toda a lógica de negócio e regras contratuais.
- **Dependency Injection**: Injeção nativa de dependências do FastAPI para autenticação, repositórios e conexões.
- **DTO Pattern**: Schemas Pydantic tipados com validação automática de entrada e serialização de saída.
- **Async/Await**: Comunicação I/O não bloqueante com o banco de dados e sistema de arquivos.

---

## 🛠 Tecnologias

- **Linguagem**: Python 3.10+
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/)
- **Driver de Banco Assíncrono**: [asyncpg](https://magicstack.github.io/asyncpg/)
- **Versionamento de Banco de Dados**: [Alembic](https://alembic.sqlalchemy.org/)
- **Validação e Serialização**: [Pydantic v2](https://docs.pydantic.dev/)
- **Segurança**: Python-Jose (JWT) e Passlib / Bcrypt (Hashing de senhas)
- **Servidor ASGI**: [Uvicorn](https://www.uvicorn.org/) / [Gunicorn](https://gunicorn.org/)
- **Manipulação de Arquivos e Email**: `aiofiles`, `aiosmtplib`
- **Agendamento em Segundo Plano**: APScheduler
- **Testes Automatizados**: `pytest`, `pytest-asyncio`, `httpx`

---

## 📋 Pré-requisitos

Antes de iniciar, certifique-se de possuir instalado em seu ambiente:
- **Python 3.10** ou superior
- **PostgreSQL 14** ou superior
- **Git**

---

## 🚀 Instalação Passo a Passo

Siga a sequência abaixo para clonar, configurar e inicializar a API a partir de um ambiente limpo:

### 1. Clone o repositório
```bash
git clone https://github.com/pgepa/sigescon-back.git
cd sigescon-back
```

### 2. Crie e ative o ambiente virtual
```bash
# Criar o ambiente virtual (.venv)
python -m venv .venv

# Ativar no Linux / macOS:
source .venv/bin/activate

# Ativar no Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Ou no Windows (Prompt de Comando):
.venv\Scripts\activate.bat
```

### 3. Instale as dependências
O projeto gerencia suas dependências via `pyproject.toml`. Instale em modo editável:
```bash
# Instalação básica de dependências
pip install -e .

# Ou instalação completa incluindo ferramentas de desenvolvimento e testes:
pip install -e ".[dev]"
```

### 4. Configure o banco de dados PostgreSQL
Acesse o seu PostgreSQL e crie a base de dados do sistema:
```sql
CREATE DATABASE sigescon;
```

Em seguida, carregue o schema inicial completo do banco utilizando o utilitário `psql`:
```bash
psql -U postgres -d sigescon -f database/create_database_complete.sql
```

### 5. Configure as variáveis de ambiente (.env)
Copie o arquivo de exemplo `.env.example` para `.env` na raiz de `sigescon-back`:
```bash
cp .env.example .env
```

Edite o arquivo `.env` ajustando as credenciais de acesso ao seu banco de dados e as configurações de segurança:
```env
# Banco de Dados
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sigescon

# Segurança JWT
JWT_SECRET_KEY=sua_chave_secreta_super_segura_de_producao_32_caracteres_min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720

# CORS (origens permitidas do frontend - opcional, padrão permite todas)
# CORS_ALLOW_ORIGINS=http://localhost:5173,https://sigescon.pge.pa.gov.br

# Credenciais do Administrador Padrão
ADMIN_EMAIL=admin@sigescon.com
ADMIN_PASSWORD=Admin@123

# Configurações de Email / SMTP (Opcional para notificações)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=notificacoes@pge.pa.gov.br
SENDER_PASSWORD=sua_senha_ou_app_token
```

### 6. Execute as migrações com Alembic
O SIGESCON utiliza o **Alembic** para aplicar alterações incrementais na estrutura do banco.

> **Nota**: Ao iniciar a API, o `lifespan` do FastAPI executa automaticamente `alembic upgrade head`. No entanto, você pode aplicar as migrações manualmente a qualquer momento executando:

```bash
alembic upgrade head
```

Comandos adicionais úteis do Alembic:
```bash
# Exibir a versão de migração atual aplicada no banco
alembic current

# Exibir o histórico de revisões
alembic history

# Criar uma nova migração a partir de alterações nos modelos
alembic revision -m "descricao_da_migracao"
```

### 7. Execute o Seeder de dados iniciais
Para popular as tabelas auxiliares (perfis de usuário, tipos de termo aditivo, modalidades, status contratuais) e criar o usuário administrador inicial:
```bash
python run_seed.py
```

---

## 🏃 Execução do Servidor

### Modo Desenvolvimento
Inicie a aplicação com hot-reload automático na porta `8000`:
```bash
uvicorn app.main:app --reload --port 8000
```
A API ficará acessível em: `http://localhost:8000`

### Modo Produção
Para ambientes de homologação ou produção, execute com múltiplos workers:
```bash
# Execução direta com Uvicorn
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Ou via Gunicorn gerenciando workers Uvicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 🧪 Testes Automatizados

Execute a suíte de testes com `pytest`:
```bash
# Executar todos os testes assíncronos
pytest -sv --asyncio-mode=auto

# Executar com relatório de cobertura de código
pytest --cov=app tests/

# Executar um módulo de teste específico
pytest tests/test_contratos.py -v
```

---

## 📖 Documentação da API

Com a API em execução, a documentação interativa fica disponível nas seguintes URLs:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Endpoints Principais

#### 🔐 Autenticação & Contexto de Sessão
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `POST` | `/auth/login` | Autentica usuário, gera JWT e devolve perfis disponíveis | Público |
| `POST` | `/auth/alternar-perfil` | Alterna o perfil ativo na sessão do usuário logado | Autenticado |
| `GET` | `/auth/contexto` | Retorna os dados do contexto ativo (perfil, permissões) | Autenticado |
| `GET` | `/auth/dashboard` | Retorna contadores e métricas contextuais do perfil ativo | Autenticado |
| `GET` | `/auth/permissoes` | Lista as permissões ativas da sessão | Autenticado |

#### 👤 Gestão de Usuários e Perfis
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/v1/usuarios` | Lista usuários com paginação e filtros | Administrador |
| `POST` | `/api/v1/usuarios` | Cadastra novo usuário | Administrador |
| `GET` | `/api/v1/usuarios/{id}` | Obtém detalhes de um usuário | Autenticado |
| `PATCH` | `/api/v1/usuarios/{id}` | Atualiza dados cadastrais de um usuário | Administrador |
| `DELETE` | `/api/v1/usuarios/{id}` | Desativa usuário (soft delete) | Administrador |
| `GET` | `/api/v1/usuarios/me` | Retorna os dados do usuário conectado | Autenticado |
| `PATCH` | `/api/v1/usuarios/{id}/alterar-senha` | Usuário atualiza a sua própria senha | Autenticado |
| `PATCH` | `/api/v1/usuarios/{id}/resetar-senha` | Redefinição administrativa de senha | Administrador |
| `GET` | `/api/v1/usuarios/{id}/perfis` | Lista os perfis atribuídos a um usuário | Autenticado |
| `POST` | `/api/v1/usuarios/{id}/perfis/conceder`| Atribui novos perfis ao usuário | Administrador |
| `POST` | `/api/v1/usuarios/{id}/perfis/revogar` | Revoga perfis do usuário | Administrador |

#### 📋 Gestão de Contratos
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/v1/contratos` | Lista contratos (filtrados pelo perfil ativo) | Autenticado |
| `POST` | `/api/v1/contratos` | Cadastra contrato com upload de documentos | Administrador |
| `GET` | `/api/v1/contratos/{id}` | Obtém detalhes completos do contrato | Autenticado |
| `PATCH` | `/api/v1/contratos/{id}` | Atualiza contrato e adiciona novos anexos | Administrador |
| `DELETE` | `/api/v1/contratos/{id}` | Exclusão lógica (soft delete) | Administrador |
| `GET` | `/api/v1/contratos/{id}/arquivos` | Lista anexos vinculados ao contrato | Autenticado |
| `DELETE` | `/api/v1/contratos/{id}/arquivos/{arq_id}` | Remove um anexo do contrato | Administrador |

#### 📑 Termos Aditivos
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/v1/tipos-termo-aditivo` | Lista os tipos de aditivo (Prazo, Valor, Misto, Outros) | Autenticado |
| `GET` | `/api/v1/contratos/{id}/aditivos` | Lista termos aditivos de um contrato específico | Autenticado |
| `POST` | `/api/v1/contratos/{id}/aditivos` | Registra novo aditivo com regras de vigência e valor | Administrador |
| `GET` | `/api/v1/contratos/{id}/aditivos/{aditivo_id}` | Obtém detalhes de um termo aditivo | Autenticado |
| `PATCH` | `/api/v1/contratos/{id}/aditivos/{aditivo_id}` | Atualiza dados do termo aditivo | Administrador |
| `DELETE` | `/api/v1/contratos/{id}/aditivos/{aditivo_id}` | Inativação lógica do termo aditivo | Administrador |
| `DELETE` | `/api/v1/contratos/{id}/aditivos/{aditivo_id}/permanente` | Exclusão definitiva de aditivo | Administrador |
| `POST` | `/api/v1/contratos/{id}/aditivos/{aditivo_id}/arquivo` | Upload de arquivo digitalizado do aditivo | Administrador |
| `GET` | `/api/v1/aditivos/relatorio` | Relatório analítico consolidado de aditivos | Autenticado |

#### 📝 Relatórios Fiscais e Pendências
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/v1/contratos/{id}/relatorios` | Lista relatórios fiscais do contrato | Autenticado |
| `POST` | `/api/v1/contratos/{id}/relatorios` | Fiscal submete relatório mensal com arquivo | Fiscal / Admin |
| `PATCH` | `/api/v1/contratos/{id}/relatorios/{id}/analise` | Aprova ou rejeita relatório com parecer | Administrador |
| `GET` | `/api/v1/contratos/{id}/pendencias` | Lista pendências de relatórios do contrato | Autenticado |
| `POST` | `/api/v1/contratos/{id}/pendencias` | Cria pendência de relatório manualmente | Administrador |
| `PATCH` | `/api/v1/contratos/{id}/pendencias/{id}/cancelar` | Cancela pendência de relatório | Administrador |
| `GET` | `/api/v1/contratos/{id}/pendencias/contador` | Contadores de pendências por status | Autenticado |
| `GET` | `/api/v1/dashboard/fiscal/minhas-pendencias` | Pendências atribuídas ao fiscal logado | Fiscal |

#### 📁 Downloads e Tabelas Auxiliares
| Método | Endpoint | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/v1/arquivos/{id}/download` | Download seguro de arquivo anexado | Autenticado |
| `GET` | `/api/v1/modalidades` | Lista modalidades de licitação | Autenticado |
| `GET` | `/api/v1/status` | Lista status possíveis de contratos | Autenticado |
| `GET` | `/api/v1/statusrelatorio` | Lista status de relatórios fiscais | Autenticado |
| `GET` | `/api/v1/statuspendencia` | Lista status de pendências | Autenticado |
| `GET` | `/api/v1/termo-contratual` | Lista tipos de instrumentos contratuais | Autenticado |
| `GET` | `/api/v1/contratados` | Lista fornecedores/empresas contratadas | Autenticado |

---

## 📐 Regras de Negócio

### Módulo de Termos Aditivos

Os termos aditivos seguem regras estritas para preservar a segurança jurídica e a integridade do histórico contratual:

1. **Tipos de Aditivo**:
   - **Prazo**: Altera o período de vigência. Exige **Nova Data Início** e **Nova Data Fim**.
   - **Valor**: Altera o valor global do contrato (acréscimo ou supressão). Exige **Valor Aditivo**.
   - **Misto**: Altera concomitantemente vigência e valor. Exige **Nova Data Início**, **Nova Data Fim** e **Valor Aditivo**.
   - **Outros**: Modificações qualitativas ou cláusulas gerais sem alteração de prazo ou valor.

2. **Preservação de Datas Originais**:
   - Ao cadastrar o primeiro aditivo de Prazo ou Misto, as datas originais do contrato são gravadas de forma permanente e imutável nas colunas `data_inicio_original` e `data_fim_original`.
   - As colunas `data_inicio` e `data_fim` do contrato são atualizadas para refletir a vigência ativa do aditivo.

3. **Coexistência de Status**:
   - Quando um novo aditivo de Prazo entra em vigor com status `Ativo`, ele substitui a vigência de aditivos de prazo anteriores.
   - O cadastro subsequente de um aditivo de **Valor** NÃO inativa o aditivo de **Prazo** vigente, pois a prorrogação temporal continua em vigor. Ambos coexistem como `Ativo`.
   - Se o término da vigência estipulado pelo aditivo expirar, o robô de sincronização atualiza o status para `Vencido`.

4. **Impacto Financeiro no Valor Global**:
   - Para termos de Valor e Misto, o campo `valor_aditivo` (positivo ou negativo) é somado ao `valor_global` do contrato.
   - Em caso de cancelamento ou exclusão do termo aditivo, o montante correspondente é devidamente estornado do contrato.

---

### Múltiplos Perfis e Isolamento de Dados

O SIGESCON implementa o conceito de múltiplos papéis por usuário:
- Um usuário pode ser simultaneamente **Gestor** de determinados contratos e **Fiscal** de outros.
- O endpoint `POST /auth/alternar-perfil` chaveia o perfil ativo sem exigir novo login.
- O repositório filtra automaticamente os registros com base no perfil ativo:
  - **Administrador**: Visão irrestrita de todos os contratos, termos e relatórios do órgão.
  - **Gestor**: Acesso restrito aos contratos nos quais atua como Gestor.
  - **Fiscal**: Acesso restrito aos contratos nos quais foi nomeado como Fiscal Titular ou Substituto.

---

### Fluxo de Relatórios Fiscais e Pendências

```mermaid
graph TD
    A[Geração de Pendência Mensal] --> B[Fiscal Notificado]
    B --> C[Fiscal Submete Relatório + Anexo PDF]
    C --> D[Status: Pendente de Análise]
    D --> E{Análise pelo Administrador}
    E -->|Aprovado| F[Relatório: Aprovado<br/>Pendência: Concluída]
    E -->|Rejeitado| G[Relatório: Rejeitado com Parecer<br/>Pendência: Retorna a Pendente]
    G --> H[Fiscal Corrige e Reenvia Anexo]
    H --> D
```

---

## 📁 Estrutura do Projeto

```
sigescon-back/
├── alembic/                      # Configurações e scripts de migração do Alembic
│   ├── env.py                    # Script de contexto do Alembic
│   ├── script.py.mako            # Template para novas revisões
│   └── versions/                 # Arquivos de migração versionados
├── alembic.ini                   # Arquivo de configuração do Alembic
├── app/
│   ├── api/                      # Roteamento e camada HTTP
│   │   ├── dependencies.py       # Injeção de dependências e autenticação
│   │   ├── permissions.py        # Validação de permissões por perfil
│   │   ├── doc_dependencies.py   # Proteção da documentação OpenAPI
│   │   ├── exception_handlers.py # Tratamento global de exceções
│   │   └── routers/              # Controladores REST organizados por módulo
│   │       ├── auth_router.py
│   │       ├── contrato_router.py
│   │       ├── termo_aditivo_router.py
│   │       ├── relatorio_router.py
│   │       ├── pendencia_router.py
│   │       ├── usuario_router.py
│   │       ├── arquivo_router.py
│   │       └── ...
│   ├── core/                     # Configurações centrais da aplicação
│   │   ├── config.py             # Variáveis de ambiente e settings (Pydantic)
│   │   ├── database.py           # Conexão e pool assíncrono AsyncPG
│   │   ├── security.py           # JWT, criptografia e validação de senhas
│   │   └── exceptions.py         # Exceções customizadas da aplicação
│   ├── middleware/               # Middlewares ASGI
│   │   ├── audit.py              # Auditoria de requisições e ações
│   │   └── logging.py            # Log estruturado
│   ├── repositories/             # Camada de persistência (queries AsyncPG)
│   │   ├── contrato_repo.py
│   │   ├── termo_aditivo_repo.py
│   │   ├── usuario_repo.py
│   │   ├── relatorio_repo.py
│   │   └── ...
│   ├── schemas/                  # Schemas DTO de entrada e saída (Pydantic)
│   │   ├── contrato_schema.py
│   │   ├── termo_aditivo_schema.py
│   │   ├── usuario_schema.py
│   │   └── ...
│   ├── services/                 # Regras de negócio e casos de uso
│   │   ├── contrato_service.py
│   │   ├── termo_aditivo_service.py
│   │   ├── email_service.py
│   │   ├── file_service.py
│   │   └── ...
│   ├── main.py                   # Ponto de entrada da aplicação FastAPI e lifespan
│   ├── seeder.py                 # Funções para carga inicial de dados
│   └── scheduler.py              # Agendador de tarefas periódicas (APScheduler)
├── database/                     # Scripts de banco de dados
│   └── create_database_complete.sql # Dump completo da estrutura do banco
├── tests/                        # Testes automatizados com Pytest
├── uploads/                      # Diretório de armazenamento de anexos
├── logs/                         # Registros de log de execução
├── .env.example                  # Template das variáveis de ambiente
├── pyproject.toml                # Definição do pacote e dependências Python
├── pytest.ini                   # Configurações do Pytest
├── run_seed.py                   # Script para execução simples do seeder
└── README.md                     # Documentação oficial do backend
```

---

## 💻 Desenvolvimento

### Convenções de Código
- **PEP 8**: Padrão de estilo estritamente seguido em todos os módulos.
- **Tipagem Estática**: Uso rigoroso de Type Hints em todas as rotas, serviços e repositórios.
- **AsyncPG com Prepared Statements**: Consultas parametrizadas prevenindo qualquer vulnerabilidade a SQL Injection.
- **Soft Delete**: Entidades críticas mantêm a flag `ativo = false` para auditoria e preservação histórica.

---

## 🤝 Contribuindo

1. Crie uma branch para sua modificação:
   ```bash
   git checkout -b feature/minha-melhoria
   ```
2. Realize os testes automatizados locais:
   ```bash
   pytest -sv --asyncio-mode=auto
   ```
3. Envie suas alterações para o repositório institucional:
   ```bash
   git commit -m "feat: implementar nova funcionalidade"
   git push origin feature/minha-melhoria
   ```

---

## 📄 Licença

Este projeto é desenvolvido e mantido pela **Procuradoria-Geral do Estado do Pará (PGE-PA)**. Todos os direitos reservados.
