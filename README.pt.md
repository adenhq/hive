<p align="center">
  <img width="100%" alt="Hive Banner" src="https://storage.googleapis.com/aden-prod-assets/website/aden-title-card.png" />
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">简体中文</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.ru.md">Русский</a> |
  <a href="README.ko.md">한국어</a>
</p>

[![Apache 2.0 License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/adenhq/hive/blob/main/LICENSE)
[![Y Combinator](https://img.shields.io/badge/Y%20Combinator-Aden-orange)](https://www.ycombinator.com/companies/aden)
[![Docker Pulls](https://img.shields.io/docker/pulls/adenhq/hive?logo=Docker&labelColor=%23528bff)](https://hub.docker.com/u/adenhq)
[![Discord](https://img.shields.io/discord/1172610340073242735?logo=discord&labelColor=%235462eb&logoColor=%23f5f5f5&color=%235462eb)](https://discord.com/invite/MXE49hrKDk)
[![Twitter Follow](https://img.shields.io/twitter/follow/teamaden?logo=X&color=%23f5f5f5)](https://x.com/aden_hq)
[![LinkedIn](https://custom-icon-badges.demolab.com/badge/LinkedIn-0A66C2?logo=linkedin-white&logoColor=fff)](https://www.linkedin.com/company/teamaden/)

<p align="center">
  <img src="https://img.shields.io/badge/AI_Agents-Self--Improving-brightgreen?style=flat-square" alt="AI Agents" />
  <img src="https://img.shields.io/badge/Multi--Agent-Systems-blue?style=flat-square" alt="Multi-Agent" />
  <img src="https://img.shields.io/badge/Goal--Driven-Development-purple?style=flat-square" alt="Goal-Driven" />
  <img src="https://img.shields.io/badge/Human--in--the--Loop-orange?style=flat-square" alt="HITL" />
  <img src="https://img.shields.io/badge/Production--Ready-red?style=flat-square" alt="Production" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/OpenAI-supported-412991?style=flat-square&logo=openai" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Anthropic-supported-d4a574?style=flat-square" alt="Anthropic" />
  <img src="https://img.shields.io/badge/Google_Gemini-supported-4285F4?style=flat-square&logo=google" alt="Gemini" />
  <img src="https://img.shields.io/badge/MCP-12_Tools-00ADD8?style=flat-square" alt="MCP" />
</p>

## Visão Geral

Construa agentes de IA confiáveis e auto-aperfeiçoáveis sem codificar fluxos de trabalho. Defina seu objetivo através de uma conversa com um agente de codificação, e o framework gera um grafo de nós com código de conexão criado dinamicamente. Quando algo quebra, o framework captura dados de falha, evolui o agente através do agente de codificação e reimplanta. Nós de intervenção humana integrados, gerenciamento de credenciais e monitoramento em tempo real dão a você controle sem sacrificar a adaptabilidade.

Visite [adenhq.com](https://adenhq.com) para documentação completa, exemplos e guias.

## O que é Aden

<p align="center">
  <img width="100%" alt="Aden Architecture" src="docs/assets/aden-architecture-diagram.jpg" />
</p>

Aden é uma plataforma para construir, implantar, operar e adaptar agentes de IA:

- **Construir** - Um Agente de Codificação gera Agentes de Trabalho especializados (Vendas, Marketing, Operações) a partir de objetivos em linguagem natural
- **Implantar** - Implantação headless com integração CI/CD e gerenciamento completo do ciclo de vida de API
- **Operar** - Monitoramento em tempo real, observabilidade e guardrails de runtime mantêm os agentes confiáveis
- **Adaptar** - Avaliação contínua, supervisão e adaptação garantem que os agentes melhorem ao longo do tempo
- **Infraestrutura** - Memória compartilhada, integrações LLM, ferramentas e habilidades alimentam cada agente

## Links Rápidos

- **[Documentação](https://docs.adenhq.com/)** - Guias completos e referência de API
- **[Guia de Auto-Hospedagem](https://docs.adenhq.com/getting-started/quickstart)** - Implante o Hive em sua infraestrutura
- **[Changelog](https://github.com/adenhq/hive/releases)** - Últimas atualizações e versões
<!-- - **[Roadmap](https://adenhq.com/roadmap)** - Funcionalidades e planos futuros -->
- **[Reportar Problemas](https://github.com/adenhq/hive/issues)** - Relatórios de bugs e solicitações de funcionalidades

## Início Rápido

### Pré-requisitos

- [Python 3.11+](https://www.python.org/downloads/) - Para desenvolvimento de agentes
- [Docker](https://docs.docker.com/get-docker/) (v20.10+) - Opcional, para ferramentas containerizadas

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/adenhq/hive.git
cd hive

# Executar configuração do ambiente Python
./scripts/setup-python.sh
```

Isto instala:
- **framework** - Runtime do agente principal e executor de grafos
- **aden_tools** - 12 ferramentas MCP para capacidades de agentes
- Todas as dependências necessárias

### Construa Seu Primeiro Agente

```bash
# Instalar habilidades do Claude Code (uma vez)
./quickstart.sh

# Construir um agente usando Claude Code
claude> /building-agents-construction

# Testar seu agente
claude> /testing-agent

# Executar seu agente
PYTHONPATH=core:exports python -m your_agent_name run --input '{...}'
```

**[📖 Guia Completo de Configuração](ENVIRONMENT_SETUP.md)** - Instruções detalhadas para desenvolvimento de agentes

## Funcionalidades

- **Desenvolvimento Orientado a Objetivos** - Defina objetivos em linguagem natural; o agente de codificação gera o grafo de agentes e código de conexão para alcançá-los
- **Agentes Auto-Adaptáveis** - Framework captura falhas, atualiza objetivos e atualiza o grafo de agentes
- **Conexões de Nós Dinâmicas** - Sem arestas predefinidas; código de conexão é gerado por qualquer LLM capaz baseado em seus objetivos
- **Nós Envolvidos em SDK** - Cada nó recebe memória compartilhada, memória RLM local, monitoramento, ferramentas e acesso LLM prontos para uso
- **Humano no Loop** - Nós de intervenção que pausam a execução para entrada humana com timeouts e escalonamento configuráveis
- **Observabilidade em Tempo Real** - Streaming WebSocket para monitoramento ao vivo de execução de agentes, decisões e comunicação entre nós
- **Controle de Custo e Orçamento** - Defina limites de gastos, throttles e políticas de degradação automática de modelo
- **Pronto para Produção** - Auto-hospedável, construído para escala e confiabilidade

## Por que Aden

Frameworks de agentes tradicionais exigem que você projete manualmente fluxos de trabalho, defina interações de agentes e lide com falhas reativamente. Aden inverte esse paradigma—**você descreve resultados, e o sistema se constrói sozinho**.

```mermaid
flowchart LR
    subgraph BUILD["🏗️ BUILD"]
        GOAL["Define Goal<br/>+ Success Criteria"] --> NODES["Add Nodes<br/>LLM/Router/Function"]
        NODES --> EDGES["Connect Edges<br/>on_success/failure/conditional"]
        EDGES --> TEST["Test & Validate"] --> APPROVE["Approve & Export"]
    end

    subgraph EXPORT["📦 EXPORT"]
        direction TB
        JSON["agent.json<br/>(GraphSpec)"]
        TOOLS["tools.py<br/>(Functions)"]
        MCP["mcp_servers.json<br/>(Integrations)"]
    end

    subgraph RUN["🚀 RUNTIME"]
        LOAD["AgentRunner<br/>Load + Parse"] --> SETUP["Setup Runtime<br/>+ ToolRegistry"]
        SETUP --> EXEC["GraphExecutor<br/>Execute Nodes"]

        subgraph DECISION["Decision Recording"]
            DEC1["runtime.decide()<br/>intent → options → choice"]
            DEC2["runtime.record_outcome()<br/>success, result, metrics"]
        end
    end

    subgraph INFRA["⚙️ INFRASTRUCTURE"]
        CTX["NodeContext<br/>memory • llm • tools"]
        STORE[("FileStorage<br/>Runs & Decisions")]
    end

    APPROVE --> EXPORT
    EXPORT --> LOAD
    EXEC --> DECISION
    EXEC --> CTX
    DECISION --> STORE
    STORE -.->|"Analyze & Improve"| NODES

    style BUILD fill:#ffbe42,stroke:#cc5d00,stroke-width:3px,color:#333
    style EXPORT fill:#fff59d,stroke:#ed8c00,stroke-width:2px,color:#333
    style RUN fill:#ffb100,stroke:#cc5d00,stroke-width:3px,color:#333
    style DECISION fill:#ffcc80,stroke:#ed8c00,stroke-width:2px,color:#333
    style INFRA fill:#e8763d,stroke:#cc5d00,stroke-width:3px,color:#fff
    style STORE fill:#ed8c00,stroke:#cc5d00,stroke-width:2px,color:#fff
```

### A Vantagem Aden

| Frameworks Tradicionais | Aden |
|-------------------------|------|
| Codificar fluxos de trabalho de agentes | Descrever objetivos em linguagem natural |
| Definição manual de grafos | Grafos de agentes auto-gerados |
| Tratamento reativo de erros | Auto-evolução proativa |
| Configurações de ferramentas estáticas | Nós dinâmicos envolvidos em SDK |
| Configuração de monitoramento separada | Observabilidade em tempo real integrada |
| Gerenciamento de orçamento DIY | Controles de custo e degradação integrados |

### Como Funciona

1. **Defina Seu Objetivo** → Descreva o que você quer alcançar em linguagem simples
2. **Agente de Codificação Gera** → Cria o grafo de agentes, código de conexão e casos de teste
3. **Workers Executam** → Nós envolvidos em SDK executam com observabilidade completa e acesso a ferramentas
4. **Plano de Controle Monitora** → Métricas em tempo real, aplicação de orçamento, gerenciamento de políticas
5. **Auto-Aperfeiçoamento** → Em caso de falha, o sistema evolui o grafo e reimplanta automaticamente

## Como Aden se Compara

Aden adota uma abordagem fundamentalmente diferente para o desenvolvimento de agentes. Enquanto a maioria dos frameworks exige que você codifique fluxos de trabalho ou defina manualmente grafos de agentes, Aden usa um **agente de codificação para gerar todo o seu sistema de agentes** a partir de objetivos em linguagem natural. Quando os agentes falham, o framework não apenas registra erros—**ele evolui automaticamente o grafo de agentes** e reimplanta.

> **Nota:** Para a tabela de comparação detalhada de frameworks e perguntas frequentes, consulte o [README.md](README.md) em inglês.

### Quando Escolher Aden

Escolha Aden quando você precisar de:

- Agentes que **se auto-aperfeiçoam a partir de falhas** sem intervenção manual
- **Desenvolvimento orientado a objetivos** onde você descreve resultados, não fluxos de trabalho
- **Confiabilidade em produção** com recuperação e reimplantação automáticas
- **Iteração rápida** em arquiteturas de agentes sem reescrever código
- **Observabilidade completa** com monitoramento em tempo real e supervisão humana

Escolha outros frameworks quando você precisar de:

- **Fluxos de trabalho previsíveis e type-safe** (PydanticAI, Mastra)
- **RAG e processamento de documentos** (LlamaIndex, Haystack)
- **Pesquisa sobre emergência de agentes** (CAMEL)
- **Voz/multimodal em tempo real** (TEN Framework)
- **Encadeamento simples de componentes** (LangChain, Swarm)

## Estrutura do Projeto

```
hive/
├── core/                   # Framework principal - Runtime de agentes, executor de grafos, protocolos
├── tools/                  # Pacote de Ferramentas MCP - 12 ferramentas para capacidades de agentes
├── exports/                # Pacotes de Agentes - Agentes pré-construídos e exemplos
├── docs/                   # Documentação e guias
├── scripts/                # Scripts de build e utilitários
├── .claude/                # Habilidades Claude Code para construir agentes
├── ENVIRONMENT_SETUP.md    # Guia de configuração Python para desenvolvimento de agentes
├── DEVELOPER.md            # Guia do desenvolvedor
├── CONTRIBUTING.md         # Diretrizes de contribuição
└── ROADMAP.md              # Roadmap do produto
```

## Desenvolvimento

### Desenvolvimento de Agentes Python

Para construir e executar agentes orientados a objetivos com o framework:

```bash
# Configuração única
./scripts/setup-python.sh

# Isto instala:
# - pacote framework (runtime principal)
# - pacote aden_tools (12 ferramentas MCP)
# - Todas as dependências

# Construir novos agentes usando habilidades Claude Code
claude> /building-agents-construction

# Testar agentes
claude> /testing-agent

# Executar agentes
PYTHONPATH=core:exports python -m agent_name run --input '{...}'
```

Consulte [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) para instruções completas de configuração.

## Documentação

- **[Guia do Desenvolvedor](DEVELOPER.md)** - Guia abrangente para desenvolvedores
- [Começando](docs/getting-started.md) - Instruções de configuração rápida
- [Guia de Configuração](docs/configuration.md) - Todas as opções de configuração
- [Visão Geral da Arquitetura](docs/architecture.md) - Design e estrutura do sistema

## Roadmap

O Aden Agent Framework visa ajudar desenvolvedores a construir agentes auto-adaptativos orientados a resultados. Encontre nosso roadmap aqui

[ROADMAP.md](ROADMAP.md)

```mermaid
timeline
    title Aden Agent Framework Roadmap
    section Foundation
        Architecture : Node-Based Architecture : Python SDK : LLM Integration (OpenAI, Anthropic, Google) : Communication Protocol
        Coding Agent : Goal Creation Session : Worker Agent Creation : MCP Tools Integration
        Worker Agent : Human-in-the-Loop : Callback Handlers : Intervention Points : Streaming Interface
        Tools : File Use : Memory (STM/LTM) : Web Search : Web Scraper : Audit Trail
        Core : Eval System : Pydantic Validation : Docker Deployment : Documentation : Sample Agents
    section Expansion
        Intelligence : Guardrails : Streaming Mode : Semantic Search
        Platform : JavaScript SDK : Custom Tool Integrator : Credential Store
        Deployment : Self-Hosted : Cloud Services : CI/CD Pipeline
        Templates : Sales Agent : Marketing Agent : Analytics Agent : Training Agent : Smart Form Agent
```

## Comunidade e Suporte

Usamos [Discord](https://discord.com/invite/MXE49hrKDk) para suporte, solicitações de funcionalidades e discussões da comunidade.

- Discord - [Junte-se à nossa comunidade](https://discord.com/invite/MXE49hrKDk)
- Twitter/X - [@adenhq](https://x.com/aden_hq)
- LinkedIn - [Página da Empresa](https://www.linkedin.com/company/teamaden/)

## Contribuindo

Aceitamos contribuições! Por favor, consulte [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes.

**Importante:** Por favor, seja atribuído a uma issue antes de enviar um PR. Comente na issue para reivindicá-la e um mantenedor irá atribuí-la a você em 24 horas. Isso ajuda a evitar trabalho duplicado.

1. Encontre ou crie uma issue e seja atribuído
2. Faça fork do repositório
3. Crie sua branch de funcionalidade (`git checkout -b feature/amazing-feature`)
4. Faça commit das suas alterações (`git commit -m 'Add amazing feature'`)
5. Faça push para a branch (`git push origin feature/amazing-feature`)
6. Abra um Pull Request

## Junte-se ao Nosso Time

**Estamos contratando!** Junte-se a nós em funções de engenharia, pesquisa e go-to-market.

[Ver Posições Abertas](https://jobs.adenhq.com/a8cec478-cdbc-473c-bbd4-f4b7027ec193/applicant)

## Segurança

Para questões de segurança, por favor consulte [SECURITY.md](SECURITY.md).

## Licença

Este projeto está licenciado sob a Licença Apache 2.0 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Perguntas Frequentes (FAQ)

> **Nota:** Para as perguntas frequentes completas, consulte o [README.md](README.md) em inglês.

**P: O Aden depende do LangChain ou outros frameworks de agentes?**

Não. O Aden é construído do zero sem dependências do LangChain, CrewAI ou outros frameworks de agentes. O framework é projetado para ser leve e flexível, gerando grafos de agentes dinamicamente em vez de depender de componentes predefinidos.

**P: Quais provedores de LLM o Aden suporta?**

O Aden suporta mais de 100 provedores de LLM através da integração LiteLLM, incluindo OpenAI (GPT-4, GPT-4o), Anthropic (modelos Claude), Google Gemini, Mistral, Groq e muitos mais. Simplesmente configure a variável de ambiente da chave API apropriada e especifique o nome do modelo.

**P: O Aden é open-source?**

Sim, o Aden é totalmente open-source sob a Licença Apache 2.0. Incentivamos ativamente contribuições e colaboração da comunidade.

**P: O que torna o Aden diferente de outros frameworks de agentes?**

O Aden gera todo o seu sistema de agentes a partir de objetivos em linguagem natural usando um agente de codificação—você não codifica fluxos de trabalho nem define grafos manualmente. Quando os agentes falham, o framework captura automaticamente os dados de falha, evolui o grafo de agentes e reimplanta. Este loop de auto-aperfeiçoamento é único do Aden.

**P: O Aden suporta fluxos de trabalho com humano no loop?**

Sim, o Aden suporta totalmente fluxos de trabalho com humano no loop através de nós de intervenção que pausam a execução para entrada humana. Estes incluem timeouts configuráveis e políticas de escalonamento, permitindo colaboração perfeita entre especialistas humanos e agentes de IA.

---

<p align="center">
  Feito com 🔥 Paixão em San Francisco
</p>
