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
DEFILLAMA_CHAINS_URL = "https://api.llama.fi/v2/chains"
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

        # Handle new API structure: tvl is now a list of historical data points
        tvl_data = data.get("tvl", [])
        if isinstance(tvl_data, list) and tvl_data:
            # Extract current TVL from the last historical data point
            current_tvl = tvl_data[-1].get("totalLiquidityUSD", 0)
        else:
            # Fallback for old API structure or empty data
            current_tvl = tvl_data if isinstance(tvl_data, int | float) else 0

        lines.extend((
            "## TVL Metrics",
            f"Current TVL: ${current_tvl:,.2f}" if current_tvl else "Current TVL: N/A",
        ))

        # Calculate TVL changes from historical data (new API doesn't provide change_1d/change_7d)
        tvl_change_1d = None
        tvl_change_7d = None
        if isinstance(tvl_data, list) and len(tvl_data) >= 2:
            # Find entries from ~1 day and ~7 days ago (86400s = 1 day)
            current_time = tvl_data[-1].get("date", 0)
            current_tvl_value = tvl_data[-1].get("totalLiquidityUSD", 0)

            for entry in reversed(tvl_data):
                time_diff = current_time - entry.get("date", 0)
                tvl_value = entry.get("totalLiquidityUSD", 0)
                if time_diff >= 86400 and tvl_change_1d is None and tvl_value > 0:
                    tvl_change_1d = ((current_tvl_value - tvl_value) / tvl_value) * 100
                if time_diff >= 86400 * 7 and tvl_change_7d is None and tvl_value > 0:
                    tvl_change_7d = ((current_tvl_value - tvl_value) / tvl_value) * 100
                    break

        lines.extend((
            f"TVL Change 24h: {tvl_change_1d:+.2f}%"
            if tvl_change_1d is not None
            else "TVL Change 24h: N/A",
            f"TVL Change 7d: {tvl_change_7d:+.2f}%"
            if tvl_change_7d is not None
            else "TVL Change 7d: N/A",
            "",
        ))

        # Use currentChainTvls (new API) or fall back to chainTvl (old API)
        chain_tvl = data.get("currentChainTvls") or data.get("chainTvl", {})
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


def get_crypto_chain_tvl(
    chain: Annotated[
        str, "Blockchain network name like ethereum, arbitrum, solana, polygon"
    ],
) -> str:
    """Fetch Total Value Locked (TVL) for a blockchain network.

    Retrieves TVL data for a specific blockchain/network from DeFiLlama.
    This is different from protocol TVL - it shows the total value locked
    across all DeFi protocols on that chain.

    Args:
        chain: Blockchain network name (e.g., 'ethereum', 'arbitrum', 'solana', 'polygon')

    Returns:
        Formatted string with chain TVL information including:
        - Chain name and TVL
        - Chain ID and token symbol
        - Comparison ranking among all chains

    Raises:
        VendorError: If the API request fails or chain is not found
    """
    defillama_logger.info("Fetching chain TVL data for: %s", chain)

    try:
        response = requests.get(DEFILLAMA_CHAINS_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        chains_data = response.json()

        if not chains_data:
            msg = "No chain data available from DeFiLlama"
            defillama_logger.warning(msg)
            return msg

        chain_lower = chain.lower().strip()
        target_chain = None

        for c in chains_data:
            if c.get("name", "").lower() == chain_lower:
                target_chain = c
                break

        if not target_chain:
            available = [c.get("name", "") for c in chains_data[:10]]
            msg = f"Chain not found: {chain}. Available chains include: {', '.join(available)}..."
            defillama_logger.warning(msg)
            return msg

        sorted_chains = sorted(
            [c for c in chains_data if c.get("tvl")],
            key=lambda x: x.get("tvl", 0),
            reverse=True,
        )
        rank = next(
            (
                i + 1
                for i, c in enumerate(sorted_chains)
                if c.get("name", "").lower() == chain_lower
            ),
            "N/A",
        )

        chain_name = target_chain.get("name", chain)
        tvl = target_chain.get("tvl", 0) or 0
        chain_id = target_chain.get("chainId", "N/A")
        token_symbol = target_chain.get("tokenSymbol", "N/A")
        gecko_id = target_chain.get("gecko_id", "N/A")

        lines = [
            f"# TVL Data for {chain_name}",
            "",
            "## Chain Overview",
            f"Name: {chain_name}",
            f"Chain ID: {chain_id}",
            f"Native Token: {token_symbol}",
            f"TVL Rank: #{rank}",
            "",
            "## TVL Metrics",
            f"Total Value Locked: ${tvl:,.2f}" if tvl else "Total Value Locked: N/A",
            "",
            "## Additional Info",
            f"CoinGecko ID: {gecko_id}",
        ]

        defillama_logger.debug("Retrieved chain TVL data for %s", chain)
        return "\n".join(lines)

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error fetching chain TVL for {chain}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_chain_tvl",
            vendor="defillama",
            params={"chain": chain},
            original_error=e,
        ) from e
    except Exception as e:
        error_msg = f"Error fetching chain TVL for {chain}"
        defillama_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_chain_tvl",
            vendor="defillama",
            params={"chain": chain},
            original_error=e,
        ) from e


__all__ = [
    "get_crypto_chain_tvl",
    "get_crypto_protocol_tvl",
    "get_crypto_protocol_yields",
]
