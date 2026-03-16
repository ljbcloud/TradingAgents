"""
DeFiLlama API vendor implementation for DeFi protocol data.

Provides functions to retrieve Total Value Locked (TVL) and yield data
for DeFi protocols using the free DeFiLlama API (no authentication required).
"""

from operator import itemgetter
from typing import Annotated

import requests

from .exceptions import VendorError
from .logging_config import get_logger

defillama_logger = get_logger("defillama")

DEFILLAMA_TVL_BASE_URL = "https://api.llama.fi"
DEFILLAMA_YIELDS_BASE_URL = "https://yields.llama.fi"
REQUEST_TIMEOUT = 30


def get_crypto_protocol_tvl(
    protocol: Annotated[str, "DeFi protocol name like aave, uniswap, lido, curve"],
) -> str:
    """Fetch Total Value Locked (TVL) data for a DeFi protocol.

    Retrieves comprehensive TVL metrics including current TVL, historical data,
    and chain-by-chain breakdown from DeFiLlama.

    Args:
        protocol: DeFi protocol slug name (e.g., 'aave', 'uniswap', 'lido', 'curve')

    Returns:
        Formatted string with protocol TVL information including:
        - Protocol name and symbol
        - Current TVL and chain breakdown
        - TVL change metrics
        - Protocol category and description

    Raises:
        VendorError: If the API request fails or protocol is not found
    """
    defillama_logger.info("Fetching TVL data for protocol: %s", protocol)

    try:
        url = f"{DEFILLAMA_TVL_BASE_URL}/protocol/{protocol.lower().strip()}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        if not data:
            msg = f"No TVL data found for protocol: {protocol}"
            defillama_logger.warning(msg)
            return msg

        lines = [f"# TVL Data for {data.get('name', protocol)}", ""]

        lines.extend((
            "## Protocol Info",
            f"Name: {data.get('name', 'N/A')}",
            f"Symbol: {data.get('symbol', 'N/A')}",
            f"Category: {data.get('category', 'N/A')}",
            f"Description: {data.get('description', 'N/A')[:200]}..."
            if data.get("description")
            else "Description: N/A",
            "",
        ))

        current_tvl = data.get("tvl", 0)
        lines.extend((
            "## TVL Metrics",
            f"Current TVL: ${current_tvl:,.2f}" if current_tvl else "Current TVL: N/A",
        ))

        tvl_change_1d = data.get("change_1d", 0)
        tvl_change_7d = data.get("change_7d", 0)
        lines.extend((
            f"TVL Change 24h: {tvl_change_1d:+.2f}%",
            f"TVL Change 7d: {tvl_change_7d:+.2f}%",
            "",
        ))

        chain_tvl = data.get("chainTvl", {})
        if chain_tvl:
            lines.append("## TVL by Chain")
            sorted_chains = sorted(chain_tvl.items(), key=itemgetter(1), reverse=True)
            for chain, tvl in sorted_chains[:10]:
                lines.append(f"{chain}: ${tvl:,.2f}")
            lines.append("")

        lines.extend((
            "## Additional Info",
            f"Twitter: {data.get('twitter', 'N/A')}",
            f"Gecko ID: {data.get('gecko_id', 'N/A')}",
        ))

        defillama_logger.debug("Retrieved TVL data for %s", protocol)
        return "\n".join(lines)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            error_msg = f"Protocol not found: {protocol}"
        else:
            error_msg = f"HTTP error fetching TVL for {protocol}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_protocol_tvl",
            vendor="defillama",
            params={"protocol": protocol},
            original_error=e,
        ) from e
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error fetching TVL for {protocol}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_protocol_tvl",
            vendor="defillama",
            params={"protocol": protocol},
            original_error=e,
        ) from e
    except Exception as e:
        error_msg = f"Error fetching TVL for {protocol}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_protocol_tvl",
            vendor="defillama",
            params={"protocol": protocol},
            original_error=e,
        ) from e


def get_crypto_protocol_yields(
    protocol: Annotated[str, "DeFi protocol name like aave, uniswap, lido, curve"],
    limit: Annotated[int, "maximum number of pools to return"] = 20,
) -> str:
    """Fetch staking/farming yield data for a DeFi protocol.

    Retrieves yield information for pools associated with a specific DeFi protocol
    from DeFiLlama's yields API.

    Args:
        protocol: DeFi protocol slug name (e.g., 'aave', 'uniswap', 'lido', 'curve')
        limit: Maximum number of pools to return (default: 20)

    Returns:
        Formatted string with protocol yield information including:
        - Pool names and chains
        - APY (Annual Percentage Yield)
        - TVL per pool
        - Reward tokens and base vs reward APY breakdown

    Raises:
        VendorError: If the API request fails
    """
    defillama_logger.info("Fetching yield data for protocol: %s", protocol)

    try:
        url = f"{DEFILLAMA_YIELDS_BASE_URL}/pools"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        if not data or "data" not in data:
            msg = "No yield data available from DeFiLlama"
            defillama_logger.warning(msg)
            return msg

        protocol_lower = protocol.lower().strip()
        protocol_pools = [
            pool
            for pool in data["data"]
            if pool.get("project", "").lower() == protocol_lower
        ]

        if not protocol_pools:
            msg = f"No yield pools found for protocol: {protocol}"
            defillama_logger.warning(msg)
            return msg

        protocol_pools.sort(key=lambda x: x.get("tvlUsd", 0) or 0, reverse=True)

        lines = [
            f"# Yield Data for {protocol}",
            f"# Total pools found: {len(protocol_pools)}",
            "",
        ]

        for i, pool in enumerate(protocol_pools[:limit], 1):
            pool_name = pool.get("pool", "Unknown")
            chain = pool.get("chain", "Unknown")
            symbol = pool.get("symbol", "N/A")
            apy = pool.get("apy", 0) or 0
            apy_base = pool.get("apyBase", 0) or 0
            apy_reward = pool.get("apyReward", 0) or 0
            tvl_usd = pool.get("tvlUsd", 0) or 0
            reward_tokens = pool.get("rewardTokens", []) or []
            stablecoin = pool.get("stablecoin", False)

            lines.extend((
                f"## Pool {i}: {symbol}",
                f"Pool ID: {pool_name}",
                f"Chain: {chain}",
                f"Stablecoin: {'Yes' if stablecoin else 'No'}",
                "",
                "### Yield Metrics",
                f"Total APY: {apy:.2f}%",
                f"Base APY: {apy_base:.2f}%",
                f"Reward APY: {apy_reward:.2f}%",
                f"TVL: ${tvl_usd:,.2f}",
            ))

            if reward_tokens:
                lines.append(f"Reward Tokens: {', '.join(reward_tokens[:5])}")

            lines.append("")

        defillama_logger.debug(
            "Retrieved %d yield pools for %s",
            min(len(protocol_pools), limit),
            protocol,
        )
        return "\n".join(lines)

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error fetching yields for {protocol}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_protocol_yields",
            vendor="defillama",
            params={"protocol": protocol, "limit": limit},
            original_error=e,
        ) from e
    except Exception as e:
        error_msg = f"Error fetching yields for {protocol}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_protocol_yields",
            vendor="defillama",
            params={"protocol": protocol, "limit": limit},
            original_error=e,
        ) from e


__all__ = [
    "get_crypto_protocol_tvl",
    "get_crypto_protocol_yields",
]
