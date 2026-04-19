import os
from datetime import datetime

import chainlit as cl
from dotenv import load_dotenv

from default_config import DEFAULT_CONFIG
from graph.trading_graph import TradingAgentsGraph

load_dotenv()

cl.instrument_openai()

MAX_DEBATE_ROUNDS = 5


@cl.on_chat_start
async def on_chat_start():
    """
    Initialize the chat session with a welcome message and configuration options.
    """
    msg = cl.Message(
        content="""
# TradingAgents Web UI

Welcome to the TradingAgents Multi-Agents LLM Financial Trading Framework!

I'll help you run trading analyses using specialized AI agents:
- **Fundamentals Analyst**: Evaluates company financials
- **Sentiment Analyst**: Analyzes market sentiment
- **News Analyst**: Monitors global news and macro events
- **Technical Analyst**: Uses technical indicators
- **Research Team**: Bullish and bearish researchers
- **Trader Agent**: Makes trading decisions
- **Risk Management**: Evaluates portfolio risk
- **Portfolio Manager**: Final approval

Let's configure your analysis session.
"""
    )
    await msg.send()

    # Collect configuration from user
    ticker = await cl.AskActionMessage(
        content="Which ticker would you like to analyze?",
        actions=[
            cl.Action(name="NVDA", value="NVDA", label="🔵 NVDA"),
            cl.Action(name="AAPL", value="AAPL", label="⚪ AAPL"),
            cl.Action(name="GOOGL", value="GOOGL", label="🟡 GOOGL"),
            cl.Action(name="MSFT", value="MSFT", label="🔴 MSFT"),
            cl.Action(name="AMZN", value="AMZN", label="⚫ AMZN"),
            cl.Action(name="TSLA", value="TSLA", label="🟢 TSLA"),
            cl.Action(name="custom", value="custom", label="✏️ Enter custom ticker"),
        ],
    ).send()

    if ticker.get("value") == "custom":
        custom_ticker = await cl.AskUserMessage(
            content="Enter the ticker symbol:"
        ).send()
        ticker_symbol = custom_ticker.get("output").upper()
    else:
        ticker_symbol = ticker.get("value")

    # Ask for date
    date_response = await cl.AskUserMessage(
        content=("Enter analysis date (format: YYYY-MM-DD) or press Enter for today:"),
        timeout=60,
    ).send()

    if date_response.get("output").strip():
        try:
            analysis_date = (
                datetime.strptime(date_response.get("output"), "%Y-%m-%d")
                .replace(tzinfo=datetime.timezone.utc)
                .date()
            )
        except ValueError:
            await cl.Message(
                content="Invalid date format. Using today's date instead."
            ).send()
            analysis_date = datetime.now(tz=datetime.timezone.utc).date()
    else:
        analysis_date = datetime.now(tz=datetime.timezone.utc).date()

    # Ask for LLM provider
    llm_choice = await cl.AskActionMessage(
        content="Which LLM provider would you like to use?",
        actions=[
            cl.Action(name="openai", value="openai", label="🤖 OpenAI (GPT)"),
            cl.Action(name="google", value="google", label="🔍 Google (Gemini)"),
            cl.Action(
                name="anthropic", value="anthropic", label="🎨 Anthropic (Claude)"
            ),
            cl.Action(name="xai", value="xai", label="🚀 xAI (Grok)"),
            cl.Action(name="openrouter", value="openrouter", label="🌐 OpenRouter"),
            cl.Action(name="ollama", value="ollama", label="🦙 Ollama (Local)"),
        ],
    ).send()

    llm_provider = llm_choice.get("value")

    # Ask for debate rounds
    rounds_response = await cl.AskUserMessage(
        content="How many debate rounds would you like? (1-5, default: 1):", timeout=60
    ).send()

    try:
        max_debate_rounds = int(rounds_response.get("output"))
        if not 1 <= max_debate_rounds <= MAX_DEBATE_ROUNDS:
            max_debate_rounds = 1
    except (ValueError, TypeError):
        max_debate_rounds = 1

    # Store configuration in session
    cl.user_session.set("ticker", ticker_symbol)
    cl.user_session.set("date", analysis_date)
    cl.user_session.set("llm_provider", llm_provider)
    cl.user_session.set("max_debate_rounds", max_debate_rounds)

    await cl.Message(
        content=f"""
## Configuration Summary

- **Ticker**: {ticker_symbol}
- **Analysis Date**: {analysis_date}
- **LLM Provider**: {llm_provider}
- **Debate Rounds**: {max_debate_rounds}

Type 'run' to start the analysis, or ask me to change any configuration.
"""
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle user messages and trigger analysis.
    """
    content = message.content.lower().strip()

    if content == "run" or "start" in content or "analyze" in content:
        await run_analysis()
    elif content == "reset":
        await cl.Message(
            content="Resetting session. Starting new configuration..."
        ).send()
        await on_chat_start()
    elif content == "help":
        await show_help()
    else:
        await cl.Message(
            content="""
Available commands:
- `run` or `start` - Run the trading analysis
- `reset` - Reset configuration and start over
- `help` - Show this help message

Or you can just ask me to change the configuration (e.g., "Change ticker to AAPL").
"""
        ).send()


async def show_help():
    """
    Display help information.
    """
    help_msg = cl.Message(
        content=(
            "# TradingAgents Web UI Help\n\n"
            "## Commands\n\n"
            "- **run** or **start**: Run the trading analysis with current configuration\n"
            "- **reset**: Reset the session and reconfigure\n"
            "- **help**: Show this help message\n\n"
            "## Configuration\n\n"
            "You can also ask me to change specific settings:\n"
            '- "Change ticker to NVDA"\n'
            '- "Use OpenAI provider"\n'
            '- "Set debate rounds to 3"\n\n'
            "## About\n\n"
            "TradingAgents uses multiple specialized AI agents to analyze financial data\n"
            "and make trading decisions. Each agent provides unique insights that are\n"
            "synthesized to form a comprehensive trading recommendation.\n\n"
            "**⚠️ Disclaimer**: This framework is designed for research purposes only.\n"
            "It is not intended as financial, investment, or trading advice. Always do\n"
            "your own research before making investment decisions."
        )
    )
    await help_msg.send()


async def run_analysis():
    """
    Run the trading analysis with current session configuration.
    """
    ticker = cl.user_session.get("ticker")
    analysis_date = cl.user_session.get("date")
    llm_provider = cl.user_session.get("llm_provider")
    max_debate_rounds = cl.user_session.get("max_debate_rounds")

    # Validate API keys
    required_keys = {
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    if llm_provider in required_keys:
        api_key = os.getenv(required_keys[llm_provider])
        if not api_key:
            await cl.Message(
                content=(
                    f"❌ Error: {required_keys[llm_provider]} not found "
                    "in environment variables.\n\n"
                    "Please set the required API key before running analysis."
                ),
            ).send()
            return

    # Show configuration summary
    config_msg = cl.Message(
        content=f"""
## Starting Analysis

**Configuration:**
- Ticker: {ticker}
- Date: {analysis_date}
- LLM Provider: {llm_provider}
- Debate Rounds: {max_debate_rounds}

Initializing TradingAgents graph...
"""
    )
    await config_msg.send()

    try:
        # Configure TradingAgentsGraph
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = llm_provider
        config["max_debate_rounds"] = max_debate_rounds

        # Create TradingAgentsGraph
        ta = TradingAgentsGraph(debug=True, config=config)

        # Run analysis
        await cl.Message(
            content="Running analysis... This may take a few minutes."
        ).send()

        result, decision = ta.propagate(str(ticker), str(analysis_date))

        # Display results
        result_msg = cl.Message(
            content=f"""
## Analysis Complete

**Final Decision:** {decision}

**Full Results:**
```
{result}
```
"""
        )
        await result_msg.send()

        await cl.Message(
            content="""
The analysis is complete! You can:
- Run another analysis (type `reset`)
- Change configuration (e.g., "Change ticker to AAPL")
- View help (type `help`)
"""
        ).send()

    except (ValueError, RuntimeError, OSError) as e:
        error_msg = cl.Message(
            content=f"""
❌ **Error during analysis:**

```
{e!s}
```

Please check your API keys and configuration, then try again
or type `reset` to reconfigure.
"""
        )
        await error_msg.send()


if __name__ == "__main__":
    cl.run()
