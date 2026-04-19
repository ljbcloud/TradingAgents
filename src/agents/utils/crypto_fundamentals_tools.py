from typing import Annotated

from langchain_core.tools import tool

from dataflows.interface import route_to_vendor


@tool
def get_crypto_token_info(
    symbol: Annotated[str, "cryptocurrency token symbol like BTC, ETH, SOL"],
) -> str:
    """
    Retrieve fundamental information about a cryptocurrency token.
    Uses the configured crypto fundamentals vendor (default: CoinGecko).
    Args:
        symbol (str): Cryptocurrency token symbol, e.g. BTC, ETH, SOL
    Returns:
        str: Token information including name, description, market cap,
             circulating supply, total supply, and other fundamental metrics.
    """
    return route_to_vendor("get_crypto_token_info", symbol)


@tool
def get_crypto_protocol_tvl(
    protocol: Annotated[str, "DeFi protocol name like uniswap, aave, lido"],
) -> str:
    """
    Retrieve Total Value Locked (TVL) data for a DeFi protocol.
    Uses the configured crypto fundamentals vendor (default: DefiLlama).
    Args:
        protocol (str): DeFi protocol name, e.g. uniswap, aave, lido
    Returns:
        str: TVL data including current TVL, historical TVL, chain breakdown,
             and protocol-specific metrics.
    """
    return route_to_vendor("get_crypto_protocol_tvl", protocol)


@tool
def get_crypto_protocol_yields(
    protocol: Annotated[str, "DeFi protocol name like uniswap, aave, lido"],
    limit: Annotated[int, "Maximum number of yield pools to return"] = 20,
) -> str:
    """
    Retrieve yield opportunities for a DeFi protocol.
    Uses the configured crypto fundamentals vendor (default: DefiLlama).
    Args:
        protocol (str): DeFi protocol name, e.g. uniswap, aave, lido
        limit (int): Maximum number of yield pools to return
    Returns:
        str: Yield data including APY/APR, pool names, tokens, TVL,
             and risk indicators for available yield opportunities.
    """
    return route_to_vendor("get_crypto_protocol_yields", protocol, limit)


@tool
def get_crypto_chain_tvl(
    chain: Annotated[
        str, "Blockchain network name like ethereum, arbitrum, solana, polygon"
    ],
) -> str:
    """
    Retrieve Total Value Locked (TVL) for a blockchain network.
    Uses the configured crypto fundamentals vendor (default: DefiLlama).
    Args:
        chain (str): Blockchain network name, e.g. ethereum, arbitrum, solana, polygon
    Returns:
        str: Chain TVL data including total value locked, chain ID, native token,
             and TVL ranking among all chains.
    """
    return route_to_vendor("get_crypto_chain_tvl", chain)
