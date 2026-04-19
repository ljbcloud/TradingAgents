"""Radon validation LangGraph node factory."""

from radon.interface import validate_trade


def create_radon_validation_node():
    def radon_validation_node(state) -> dict:
        asset_type = state.get("asset_type", "stock")

        if asset_type == "crypto":
            return {
                "radon_validation_result": "SKIP",
                "radon_validation_details": {},
            }

        try:
            result = validate_trade(state)
            return {
                "radon_validation_result": result.get("radon_validation_result", ""),
                "radon_validation_details": result.get("radon_validation_details", {}),
            }
        except Exception:
            return {
                "radon_validation_result": "ERROR",
                "radon_validation_details": {},
            }

    return radon_validation_node
