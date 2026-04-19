# Agent Usage Audit for Dataflows Error Handling Refactoring

**Generated**: 2026-03-15
**Purpose**: Document breaking change impacts when refactoring dataflows from string errors to exception-based error handling
**Scope**: All agent code using tradingagents.dataflows functions

---

## Executive Summary

This audit documents how TradingAgents agents use dataflows functions and identifies breaking changes when switching from string-based error returns to exception-based error handling.

**Key Findings**:
- 9 exported functions are used across 4 agent tool files
- All agent tools use `route_to_vendor()` to call dataflows functions
- Current error handling: String error returns from vendor implementations
- Zero error handling in agent tools (no try/except blocks)
- Breaking change: Agent tools will crash when vendors raise exceptions instead of returning error strings

**Critical Impact**: When dataflows functions switch to raising exceptions, agent tools will propagate these exceptions to LangChain tool calls, causing tool failures instead of returning error messages.

---

## Exported Functions Analysis

### Function Mapping from VENDOR_METHODS

| Function | Vendor Implementations | Category |
|-----------|------------------------|-----------|
| `get_stock_data` | alpha_vantage: get_alpha_vantage_stock<br>yfinance: get_YFin_data_online | core_stock_apis |
| `get_indicators` | alpha_vantage: get_alpha_vantage_indicator<br>yfinance: get_stock_stats_indicators_window | technical_indicators |
| `get_fundamentals` | alpha_vantage: get_alpha_vantage_fundamentals<br>yfinance: get_yfinance_fundamentals | fundamental_data |
| `get_balance_sheet` | alpha_vantage: get_alpha_vantage_balance_sheet<br>yfinance: get_yfinance_balance_sheet | fundamental_data |
| `get_cashflow` | alpha_vantage: get_alpha_vantage_cashflow<br>yfinance: get_yfinance_cashflow | fundamental_data |
| `get_income_statement` | alpha_vantage: get_alpha_vantage_income_statement<br>yfinance: get_yfinance_income_statement | fundamental_data |
| `get_news` | alpha_vantage: get_alpha_vantage_news<br>yfinance: get_news_yfinance | news_data |
| `get_global_news` | alpha_vantage: get_alpha_vantage_global_news<br>yfinance: get_global_news_yfinance | news_data |
| `get_insider_transactions` | alpha_vantage: get_alpha_vantage_insider_transactions<br>yfinance: get_yfinance_insider_transactions | news_data |

---

## Agent Tool Files Using Dataflows

### 1. tradingagents/agents/utils/core_stock_tools.py

**Imports**:
```python
from tradingagents.dataflows.interface import route_to_vendor
```

**Functions Used**:

#### `get_stock_data`
- **File**: `tradingagents/agents/utils/core_stock_tools.py:9-24`
- **Parameters**:
  - `symbol: str` - ticker symbol of company
  - `start_date: str` - Start date in yyyy-mm-dd format
  - `end_date: str` - End date in yyyy-mm-dd format
- **Implementation**:
  ```python
  @tool
  def get_stock_data(symbol, start_date, end_date) -> str:
      return route_to_vendor("get_stock_data", symbol, start_date, end_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (CSV string or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

---

### 2. tradingagents/agents/utils/fundamental_data_tools.py

**Imports**:
```python
from tradingagents.dataflows.interface import route_to_vendor
```

**Functions Used**:

#### `get_fundamentals`
- **File**: `tradingagents/agents/utils/fundamental_data_tools.py:9-22`
- **Parameters**:
  - `ticker: str` - ticker symbol
  - `curr_date: str` - current date you are trading at, yyyy-mm-dd
- **Implementation**:
  ```python
  @tool
  def get_fundamentals(ticker, curr_date) -> str:
      return route_to_vendor("get_fundamentals", ticker, curr_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted report or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

#### `get_balance_sheet`
- **File**: `tradingagents/agents/utils/fundamental_data_tools.py:26-43`
- **Parameters**:
  - `ticker: str` - ticker symbol
  - `freq: str = "quarterly"` - reporting frequency: annual/quarterly
  - `curr_date: str | None = None` - current date you are trading at, yyyy-mm-dd
- **Implementation**:
  ```python
  @tool
  def get_balance_sheet(ticker, freq="quarterly", curr_date=None) -> str:
      return route_to_vendor("get_balance_sheet", ticker, freq, curr_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted report or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

#### `get_cashflow`
- **File**: `tradingagents/agents/utils/fundamental_data_tools.py:47-64`
- **Parameters**:
  - `ticker: str` - ticker symbol
  - `freq: str = "quarterly"` - reporting frequency: annual/quarterly
  - `curr_date: str | None = None` - current date you are trading at, yyyy-mm-dd
- **Implementation**:
  ```python
  @tool
  def get_cashflow(ticker, freq="quarterly", curr_date=None) -> str:
      return route_to_vendor("get_cashflow", ticker, freq, curr_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted report or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

#### `get_income_statement`
- **File**: `tradingagents/agents/utils/fundamental_data_tools.py:68-85`
- **Parameters**:
  - `ticker: str` - ticker symbol
  - `freq: str = "quarterly"` - reporting frequency: annual/quarterly
  - `curr_date: str | None = None` - current date you are trading at, yyyy-mm-dd
- **Implementation**:
  ```python
  @tool
  def get_income_statement(ticker, freq="quarterly", curr_date=None) -> str:
      return route_to_vendor("get_income_statement", ticker, freq, curr_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted report or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

---

### 3. tradingagents/agents/utils/news_data_tools.py

**Imports**:
```python
from tradingagents.dataflows.interface import route_to_vendor
```

**Functions Used**:

#### `get_news`
- **File**: `tradingagents/agents/utils/news_data_tools.py:9-24`
- **Parameters**:
  - `ticker: str` - Ticker symbol
  - `start_date: str` - Start date in yyyy-mm-dd format
  - `end_date: str` - End date in yyyy-mm-dd format
- **Implementation**:
  ```python
  @tool
  def get_news(ticker, start_date, end_date) -> str:
      return route_to_vendor("get_news", ticker, start_date, end_date)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted string or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

#### `get_global_news`
- **File**: `tradingagents/agents/utils/news_data_tools.py:28-43`
- **Parameters**:
  - `curr_date: str` - Current date in yyyy-mm-dd format
  - `look_back_days: int = 7` - Number of days to look back
  - `limit: int = 5` - Maximum number of articles to return
- **Implementation**:
  ```python
  @tool
  def get_global_news(curr_date, look_back_days=7, limit=5) -> str:
      return route_to_vendor("get_global_news", curr_date, look_back_days, limit)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted string or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

#### `get_insider_transactions`
- **File**: `tradingagents/agents/utils/news_data_tools.py:47-58`
- **Parameters**:
  - `ticker: str` - ticker symbol
- **Implementation**:
  ```python
  @tool
  def get_insider_transactions(ticker) -> str:
      return route_to_vendor("get_insider_transactions", ticker)
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted report or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

---

### 4. tradingagents/agents/utils/technical_indicators_tools.py

**Imports**:
```python
from tradingagents.dataflows.interface import route_to_vendor
```

**Functions Used**:

#### `get_indicators`
- **File**: `tradingagents/agents/utils/technical_indicators_tools.py:9-30`
- **Parameters**:
  - `symbol: str` - ticker symbol of company
  - `indicator: str` - technical indicator to get analysis and report of
  - `curr_date: str` - The current trading date you are trading on, YYYY-mm-dd
  - `look_back_days: int = 30` - how many days to look back
- **Implementation**:
  ```python
  @tool
  def get_indicators(symbol, indicator, curr_date, look_back_days=30) -> str:
      return route_to_vendor(
          "get_indicators", symbol, indicator, curr_date, look_back_days
      )
  ```
- **Error Handling**: None (direct pass-through)
- **Expected Return Type**: `str` (formatted dataframe or error string)
- **Breaking Change Impact**: HIGH - No try/except, will crash on exceptions

---

## Current Error Handling Patterns

### Dataflows Error Handling (Before Refactoring)

#### String Error Returns (Current Pattern)

Most vendor implementations return error messages as strings:

**Alpha Vantage Indicator Examples**:
```python
# alpha_vantage_indicator.py
return f"Error: Indicator {indicator} not implemented yet."
return f"Error: No data returned for {indicator}"
return f"Error: 'time' column not found in data for {indicator}"
return f"Error retrieving {indicator} data: {e!s}"
```

**Yahoo Finance Examples**:
```python
# y_finance.py
return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
return f"Error retrieving fundamentals for {ticker}: {e!s}"
return f"No balance sheet data found for symbol '{ticker}'"
return f"Error retrieving balance sheet for {ticker}: {e!s}"

# yfinance_news.py
return f"No news found for {ticker}"
return f"Error fetching news for {ticker}: {e!s}"
return f"Error fetching global news: {e!s}"
```

#### Exception Raises (Current Pattern)

Some validation errors raise exceptions:

**Alpha Vantage Common**:
```python
# alpha_vantage_common.py
raise ValueError(msg)  # For invalid parameters
raise AlphaVantageRateLimitError(msg)  # For rate limit exceeded
```

**Interface Routing**:
```python
# interface.py
raise ValueError(msg)  # For invalid method/category
raise RuntimeError(msg)  # When no vendor available
```

**Interface Fallback Handling**:
```python
# interface.py:route_to_vendor
try:
    return impl_func(*args, **kwargs)
except AlphaVantageRateLimitError:
    continue  # Only rate limits trigger fallback
```

**Key Observation**: `route_to_vendor()` only catches `AlphaVantageRateLimitError` for vendor fallback. All other exceptions (ValueError, RuntimeError, vendor exceptions) will propagate to callers.

### Agent Error Handling (Current Pattern)

#### Minimal Error Handling

**Search Results**:
- Only one try/except block in `tradingagents/agents/utils/memory.py`
- No try/except blocks around dataflows calls
- No error string checking in agent tools
- All agent tools use direct pass-through to `route_to_vendor()`

**Memory.py Exception Handling** (Not Related to Dataflows):
```python
# tradingagents/agents/utils/memory.py
try:
    recommendations = matcher.get_memories(current_situation, n_matches=2)
except Exception:
    pass
```

**Key Observation**: Agent tools have ZERO error handling for dataflows functions. They expect strings to be returned and pass them directly to LangChain.

---

## Breaking Change Impacts

### Impact Severity: CRITICAL

When dataflows functions switch from returning error strings to raising exceptions, the following breaking changes will occur:

### 1. Agent Tool Failures

**Current Behavior**:
```python
# Agent tool returns string (data or error message)
@tool
def get_stock_data(symbol, start_date, end_date) -> str:
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)
    # Returns: "CSV data..." or "Error: Invalid symbol..."
```

**After Refactoring (Breaking Change)**:
```python
# Agent tool will raise exceptions
@tool
def get_stock_data(symbol, start_date, end_date) -> str:
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)
    # Will raise: DataFetchError, VendorError, etc.
    # LangChain tool will report: Tool error, no string returned
```

**Impact**:
- LLM agents will see tool failures instead of error messages
- Agent tools will crash on all error conditions
- No graceful degradation or error message display
- LangChain will propagate exceptions to tool calling mechanism

### 2. route_to_vendor Exception Propagation

**Current Behavior**:
```python
# Only AlphaVantageRateLimitError triggers fallback
try:
    return impl_func(*args, **kwargs)
except AlphaVantageRateLimitError:
    continue  # Try next vendor
```

**After Refactoring**:
```python
# All other exceptions will propagate immediately
try:
    return impl_func(*args, **kwargs)
except AlphaVantageRateLimitError:
    continue
# DataFetchError, VendorError, NetworkError, etc. will propagate
# No fallback for these new exceptions
```

**Impact**:
- Vendor fallback only works for rate limits (AlphaVantageRateLimitError)
- New exception types (DataFetchError, VendorError, etc.) will not trigger fallback
- No automatic retry or vendor switching for other error types
- Agents will see immediate failures instead of fallback attempts

### 3. LangChain Tool Integration

**Current Behavior**:
```python
# Tool returns string (data or error)
@tool
def get_news(ticker, start_date, end_date) -> str:
    result = route_to_vendor("get_news", ticker, start_date, end_date)
    # result: "News data..." or "Error: No news found..."
    return result  # LLM reads this string
```

**After Refactoring (Breaking Change)**:
```python
# Tool raises exception on error
@tool
def get_news(ticker, start_date, end_date) -> str:
    result = route_to_vendor("get_news", ticker, start_date, end_date)
    # Raises: VendorError on API failure
    # LangChain reports: ToolExecutionException
    # LLM sees: "Tool get_news failed with error: ..." instead of error message
```

**Impact**:
- LLM cannot read error details from string returns
- LLM sees tool failure, not context about what failed
- No ability to log/display error messages to users
- Tool execution stops immediately on first error

### 4. Error Message Loss

**Current Behavior**:
```python
# Error messages returned as strings
return f"Error retrieving fundamentals for {ticker}: {e!s}"
# LLM reads: "Error retrieving fundamentals for AAPL: Invalid API key"
# LLM can understand and explain error to user
```

**After Refactoring (Breaking Change)**:
```python
# Exceptions raised with context
raise VendorError(
    f"Error retrieving fundamentals for {ticker}: {e!s}",
    function="get_fundamentals",
    vendor="yfinance",
)
# LLM sees: "Tool get_fundamentals raised VendorError"
# Error details buried in exception, not displayed
```

**Impact**:
- LLM loses detailed error context
- Error details not visible to users
- Debugging becomes harder
- No error message formatting for end users

---

## Required Changes for Error Handling Refactoring

### Phase 1: Dataflows Refactoring (Tasks 5-6)

1. **Replace String Error Returns with Exceptions**
   - Change all `return f"Error: ..."` to `raise VendorError(...)`
   - Add logging before raising exceptions
   - Include context (function, params, vendor) in exceptions

2. **Update route_to_vendor Fallback Logic**
   - Catch new exception types: `DataFetchError`, `VendorError`, `NetworkError`
   - Fallback on all data fetch errors, not just rate limits
   - Log fallback attempts with details

3. **Update Documentation**
   - Change docstrings from "Returns: str" to "Raises: DataFetchError, VendorError, etc."
   - Document exception types and their causes

### Phase 2: Agent Tool Updates (Not in Original Plan - Critical Addition)

**Required**: Update all agent tools to handle exceptions

#### Option A: Wrap route_to_vendor Calls (Recommended)

Add try/except blocks to convert exceptions to string messages:

```python
@tool
def get_stock_data(symbol, start_date, end_date) -> str:
    try:
        return route_to_vendor("get_stock_data", symbol, start_date, end_date)
    except Exception as e:
        # Convert exception to readable string for LLM
        return f"Error: {str(e)}"
```

**Pros**:
- Maintains backward compatibility with LLM expectations
- LLM can still read error messages
- Minimal changes to agent tools
- Works with existing LangChain tool integration

**Cons**:
- Loses exception type information
- Exceptions caught at wrong layer
- Error handling scattered across tools

#### Option B: Let Exceptions Propagate (Breaking)

Allow exceptions to propagate to LangChain:

```python
@tool
def get_stock_data(symbol, start_date, end_date) -> str:
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)
    # Raises: DataFetchError, VendorError, etc.
    # LangChain handles exceptions with tool error messages
```

**Pros**:
- Proper exception handling throughout stack
- Type-safe error handling
- Logging at correct layer
- Exception context preserved

**Cons**:
- BREAKING CHANGE for LLM integration
- LLM sees tool failures instead of error messages
- User experience degraded (no error display)
- May require LangChain tool configuration changes

#### Option C: Hybrid Approach (Best of Both Worlds)

Return structured responses that include error information:

```python
from typing import Dict, Union


@tool
def get_stock_data(symbol, start_date, end_date) -> Dict[str, Union[str, dict]]:
    try:
        data = route_to_vendor("get_stock_data", symbol, start_date, end_date)
        return {"status": "success", "data": data}
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "details": getattr(e, "__dict__", {}),
        }
```

**Pros**:
- Maintains error information
- LLM can parse and explain errors
- Structured error handling
- Future-proof for better error reporting

**Cons**:
- Major breaking change (return type change)
- Requires LLM prompt updates
- More complex error handling logic

---

## Recommended Action Plan

### Immediate (Required for Error Handling Refactoring)

1. **Audit Route-to-Vendor Fallback Logic**
   - Test current AlphaVantageRateLimitError handling
   - Verify fallback mechanism works correctly
   - Document current fallback behavior

2. **Plan Agent Tool Exception Handling Strategy**
   - Decide between Option A (wrap), Option B (propagate), or Option C (hybrid)
   - Consider LLM integration impact
   - Document chosen strategy in dataflows-improvements plan

3. **Update Breaking Change Documentation**
   - Add this audit to dataflows-improvements plan as Task 2 reference
   - Document required agent tool changes
   - Create migration checklist for agent tool updates

### For Error Handling Refactoring Tasks (Tasks 5-6)

1. **Add Agent Tool Updates to Plan**
   - Create new task: "Update agent tools to handle exceptions"
   - Define task in dataflows-improvements plan
   - Add to appropriate wave (likely Wave 3 after Tasks 5-6)

2. **Test Exception Propagation**
   - After Tasks 5-6, test agent tool behavior
   - Verify exception types propagate correctly
   - Check fallback logic works with new exceptions

3. **Document LLM Tool Error Handling**
   - Research LangChain tool exception handling
   - Document how LangChain displays tool errors
   - Determine if LangChain configuration needed

---

## Conclusion

### Critical Finding

**The error handling refactoring (Tasks 5-6) is a BREAKING CHANGE that will break agent functionality if agent tools are not updated.**

**Current State**:
- Dataflows return error strings
- Agent tools expect string returns
- No exception handling in agent tools
- LLM reads error messages from string returns

**After Tasks 5-6 (Without Agent Tool Updates)**:
- Dataflows raise exceptions
- Agent tools crash on all errors
- LLM sees tool failures
- No error messages displayed

### Required Next Steps

**Option 1**: Add agent tool exception handling task to dataflows-improvements plan
**Option 2**: Update agent tools as part of Tasks 5-6 (scope expansion)
**Option 3**: Modify exception raising in dataflows to maintain backward compatibility (not recommended)

**Recommendation**: Add agent tool exception handling as a new task in Wave 3 of the dataflows-improvements plan, executing after Tasks 5-6 are complete.

---

## Appendix A: Code Search Commands Used

```bash
# Find all dataflows imports in agents
grep -r "from tradingagents.dataflows" tradingagents/agents/ --include="*.py"

# Count imports
grep -r "from tradingagents.dataflows" tradingagents/agents/ --include="*.py" | wc -l

# Search for string error returns in dataflows
grep -r "return f\"Error" tradingagents/dataflows/ --include="*.py"

# Search for exception raises in dataflows
grep -r "raise.*Error" tradingagents/dataflows/ --include="*.py"

# Search for AlphaVantageRateLimitError usage
grep -r "AlphaVantageRateLimitError" tradingagents/dataflows/ --include="*.py"

# Search for route_to_vendor usage patterns
grep -r "route_to_vendor" tradingagents/agents/ --include="*.py" -A 1 -B 1

# Search for exception handling in dataflows
grep -r "except.*:" tradingagents/dataflows/ --include="*.py"
```

---

## Appendix B: File Locations Summary

### Agent Tool Files (4 files)
1. `tradingagents/agents/utils/core_stock_tools.py` - 1 function
2. `tradingagents/agents/utils/fundamental_data_tools.py` - 4 functions
3. `tradingagents/agents/utils/news_data_tools.py` - 3 functions
4. `tradingagents/agents/utils/technical_indicators_tools.py` - 1 function

**Total Functions**: 9 (matches VENDOR_METHODS count)

### Dataflows Interface File
- `tradingagents/dataflows/interface.py` - Contains VENDOR_METHODS mapping and route_to_vendor()

### Dataflows Vendor Files
- `tradingagents/dataflows/alpha_vantage_stock.py` - Alpha Vantage stock data
- `tradingagents/dataflows/alpha_vantage_indicator.py` - Alpha Vantage indicators
- `tradingagents/dataflows/y_finance.py` - Yahoo Finance fundamentals and stock data
- `tradingagents/dataflows/yfinance_news.py` - Yahoo Finance news data
- `tradingagents/dataflows/alpha_vantage_common.py` - Alpha Vantage utilities and AlphaVantageRateLimitError

---

**End of Audit Report**
