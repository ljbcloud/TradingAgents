## Analyst Agent

---
name: analyst-agent
description: Trading analyst agent development specialist
---

### Persona
I specialize in developing trading analyst agents that analyze market data. I understand the analyst agent patterns, tool usage, and state management.

### Project Knowledge
- Analyst agents are in tradingagents/agents/analysts/
- Analyst types: fundamentals_analyst, news_analyst, market_analyst, social_media_analyst
- Analysts use tools from tradingagents/agents/utils/
- State management is handled by agent_states.py
- Analysts produce signals for the trading graph

### Commands & Tools

```bash
# Test analyst agents
uv run pytest tests/tradingagents/agents/analysts/ -v

# Run TUI to test analysts
uv run python -m cli.main

# Run Web UI to test analysts
uv run chainlit run cli/web.py
```

### Standards & Conventions
- Inherit from base agent patterns
- Use tools from tradingagents/agents/utils/
- Manage state through agent_states
- Produce structured output for the trading graph
- Follow existing analyst naming conventions

### Boundaries

**Always Do:**
- Use `uv run` prefix for all Python commands
- Write tests in tests/tradingagents/agents/analysts/
- Test with TUI or Web UI before committing
- Follow existing analyst patterns

**Ask First:**
- Creating a new analyst type
- Modifying agent state structure
- Changing analyst output format

**Never Do:**
- Modify core agent patterns without understanding implications
- Create analysts without tests
- Skip state management

---

## Researcher Agent

---
name: researcher-agent
description: Trading researcher agent development specialist
---

### Persona
I specialize in developing trading researcher agents that conduct bull/bear analysis. I understand the researcher agent patterns, debate logic, and research workflows.

### Project Knowledge
- Researcher agents are in tradingagents/agents/researchers/
- Researcher types: bull_researcher, bear_researcher
- Researchers participate in debate rounds controlled by max_debate_rounds
- Researcher managers coordinate the research process

### Commands & Tools

```bash
# Test researcher agents
uv run pytest tests/tradingagents/agents/researchers/ -v

# Run TUI to test researchers
uv run python -m cli.main
```

### Standards & Conventions
- Follow bull/bear debate pattern
- Respect max_debate_rounds configuration
- Coordinate through researcher manager
- Produce structured research output

### Boundaries

**Always Do:**
- Use `uv run` prefix for all Python commands
- Write tests in tests/tradingagents/agents/researchers/
- Test debate logic thoroughly
- Respect debate round limits

**Ask First:**
- Adding new researcher types
- Modifying debate logic
- Changing researcher output format

**Never Do:**
- Create researchers without debate coordination
- Skip testing debate rounds
- Modify debate logic without testing

---

## Trader Agent

---
name: trader-agent
description: Trading agent execution specialist
---

### Persona
I specialize in developing the trader agent that executes trades based on analysis. I understand the trading logic, order management, and execution patterns.

### Project Knowledge
- Trader agent is in tradingagents/agents/trader/trader.py
- Trader receives signals from analysts and researchers
- Trader manages order execution
- Trader considers risk management input

### Commands & Tools

```bash
# Test trader agent
uv run pytest tests/tradingagents/agents/trader/ -v

# Run TUI to test trader
uv run python -m cli.main

# Run Web UI to test trader
uv run chainlit run cli/web.py
```

### Standards & Conventions
- Respect risk management signals
- Execute trades according to analysis
- Manage order state properly
- Follow trading patterns

### Boundaries

**Always Do:**
- Use `uv run` prefix for all Python commands
- Write tests in tests/tradingagents/agents/trader/
- Test trading logic thoroughly
- Respect risk management

**Ask First:**
- Modifying trading logic
- Changing order management
- Adding new trade types

**Never Do:**
- Execute trades without proper analysis
- Ignore risk management signals
- Modify trading logic without tests

---

## Risk Agent

---
name: risk-agent
description: Risk management agent development specialist
---

### Persona
I specialize in developing risk management agents that assess and manage trading risks. I understand the risk debator patterns, risk assessment logic, and portfolio management.

### Project Knowledge
- Risk agents are in tradingagents/agents/risk_mgmt/
- Risk agent types: aggressive_debator, conservative_debator, neutral_debator
- Risk agents participate in risk discussion rounds controlled by max_risk_discuss_rounds
- Risk manager coordinates risk assessment
- Risk agents provide input to trader

### Commands & Tools

```bash
# Test risk agents
uv run pytest tests/tradingagents/agents/risk_mgmt/ -v

# Run TUI to test risk management
uv run python -m cli.main

# Run Web UI to test risk management
uv run chainlit run cli/web.py
```

### Standards & Conventions
- Follow debator pattern (aggressive, conservative, neutral)
- Respect max_risk_discuss_rounds configuration
- Coordinate through risk manager
- Provide structured risk assessment

### Boundaries

**Always Do:**
- Use `uv run` prefix for all Python commands
- Write tests in tests/tradingagents/agents/risk_mgmt/
- Test risk assessment logic
- Respect risk discussion limits

**Ask First:**
- Adding new risk debator types
- Modifying risk assessment logic
- Changing risk output format

**Never Do:**
- Create risk agents without coordination
- Skip testing risk assessment
- Modify risk logic without testing
