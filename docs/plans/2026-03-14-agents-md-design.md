# AGENTS.md Design Document

## Overview
Create hierarchical AGENTS.md files for TradingAgents project to guide internal developers and GitHub Copilot in working with the codebase effectively.

## Background
Based on GitHub's AGENTS.md best practices and the TradingAgents codebase structure, we need agent definitions that help developers work with the multi-agent LLM financial trading framework.

## File Structure
```
/AGENTS.md                          # Root-level (general, cross-cutting)
/docs/AGENTS.md                     # Documentation workflows
/tradingagents/AGENTS.md            # Core trading logic
/tradingagents/agents/AGENTS.md     # Agent development
/tradingagents/dataflows/AGENTS.md   # Data pipelines
/tradingagents/graph/AGENTS.md      # LangGraph logic
/cli/AGENTS.md                      # CLI interfaces
/tests/AGENTS.md                    # Testing
```

## Agent Definitions

### Root AGENTS.md

**Purpose:** Project overview, cross-cutting workflows, and directory navigation

**Key Agents:**
1. **project-agent** - Project structure and configuration
2. **lint-agent** - Code quality (ruff)
3. **config-agent** - Configuration management

**Commands:**
- `uv sync` - Install/update dependencies
- `ruff check .` - Lint checking
- `ruff check --fix .` - Fix lint issues
- `ruff format .` - Format code
- `uv run python main.py` - Run main entry point

**Project Knowledge:**
- DEFAULT_CONFIG patterns (llm_provider, data vendors, discussion settings)
- LLM providers: OpenAI, Google, Anthropic, xAI, OpenRouter, Ollama
- Data vendors: Alpha Vantage, Yahoo Finance
- Git workflow: feat:/fix:/docs:/chore:/test: commit format

### docs/AGENTS.md

**Purpose:** Documentation workflows and conventions

**Key Agents:**
1. **docs-agent** - Documentation generation
2. **plans-agent** - Plan document creation

**Knowledge:**
- Plan structure: `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Design doc patterns
- Markdown conventions

### tradingagents/AGENTS.md

**Purpose:** Core trading logic architecture

**Key Agents:**
1. **llm-agent** - LLM client usage
2. **config-agent** - Configuration patterns

**Knowledge:**
- LLM client patterns (base_client, provider-specific clients)
- Configuration management
- Package structure

### tradingagents/agents/AGENTS.md

**Purpose:** Agent development and patterns

**Key Agents:**
1. **analyst-agent** - Analyst agent development
2. **researcher-agent** - Researcher agent development
3. **trader-agent** - Trader agent development
4. **risk-agent** - Risk manager development

**Commands:**
- `uv run python -m cli.main` - TUI testing
- `uv run chainlit run cli/web.py` - Web UI testing

**Knowledge:**
- Agent types: Analysts (fundamentals, sentiment, news, technical), Researchers (bull/bear), Trader, Risk Management
- Agent state management (agent_states.py)
- Tool patterns (core_stock_tools, technical_indicators_tools, etc.)
- Agent conventions

### tradingagents/dataflows/AGENTS.md

**Purpose:** Data pipeline development

**Key Agents:**
1. **data-vendor-agent** - Data vendor integration
2. **data-pipeline-agent** - Data pipeline patterns

**Knowledge:**
- Data vendor patterns (Alpha Vantage, Yahoo Finance)
- Caching strategies
- API configuration
- Data pipeline patterns

### tradingagents/graph/AGENTS.md

**Purpose:** LangGraph and graph logic development

**Key Agents:**
1. **graph-agent** - LangGraph patterns
2. **signal-agent** - Signal processing

**Knowledge:**
- LangGraph patterns
- Signal processing logic
- Reflection mechanisms
- State transitions

### cli/AGENTS.md

**Purpose:** CLI interface development

**Key Agents:**
1. **tui-agent** - TUI development (cli/main.py)
2. **web-agent** - Web UI development (Chainlit)

**Commands:**
- `uv run python -m cli.main` - Run TUI
- `uv run chainlit run cli/web.py` - Run Web UI

**Knowledge:**
- TUI patterns
- Web UI patterns (Chainlit)
- CLI configuration
- Interface patterns

### tests/AGENTS.md

**Purpose:** Testing workflows and patterns

**Key Agents:**
1. **test-agent** - Test development

**Commands:**
- `uv run pytest` - Run all tests
- `uv run pytest -v` - Verbose output
- `uv run pytest --cov=tradingagents` - Coverage report

**Knowledge:**
- Pytest fixtures (tests/conftest.py)
- Test structure (mirrors source)
- Coverage requirements
- Test conventions

## AGENTS.md Template

Each agent should follow this structure:

```markdown
# <Agent Name>

---
name: <agent-name>
description: <brief description>
---

### Persona
<Who this agent is and what they specialize in>

### Project Knowledge
<Specific knowledge about this part of the codebase>

### Commands & Tools
<Exact commands with uv run prefix>

### Standards & Conventions
<Coding patterns and conventions>

### Boundaries
**Always Do:**
- <things to always do>

**Ask First:**
- <things to clarify before doing>

**Never Do:**
- <things to never do>
```

## Key Requirements

1. **All commands use `uv run` prefix** for virtual environment execution
2. **Executable commands come first** with exact syntax
3. **Clear boundaries** (Always Do / Ask First / Never Do)
4. **Real code examples** over descriptions
5. **Specific to subdirectory** context
6. **Cross-references** between related agents

## Success Criteria

- All 8 AGENTS.md files created
- Each file contains 2-4 relevant agents
- All commands use `uv run` prefix
- Clear boundaries defined for each agent
- Subdirectory-specific knowledge included
- Cross-references to related AGENTS.md files

## Next Steps

1. Create implementation plan using writing-plans skill
2. Implement all 8 AGENTS.md files
3. Test with Copilot interactions
4. Iterate based on feedback
