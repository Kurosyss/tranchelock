"""
TrancheLock Token Configuration & Allowlist
===========================================
Ensures compliant token handling:
- Never labels custom mints as Circle USDC
- Defaults to official Solana Devnet USDC: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
- Uses TLUSD (TrancheUSD) for local/sandbox testing
- Environment-configurable via TRANCHELOCK_TOKEN_MINT
"""

import os
from typing import Dict, Any

# Official Solana Devnet USDC mint (Circle Devnet USDC)
OFFICIAL_DEVNET_USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"

# Local/Testing token mint
LOCAL_TLUSD_MINT = "TLUSD1111111111111111111111111111111111111"

ALLOWLISTED_MINTS: Dict[str, Dict[str, Any]] = {
    OFFICIAL_DEVNET_USDC_MINT: {
        "symbol": "USDC",
        "name": "Circle Devnet USDC",
        "decimals": 6,
        "is_official_usdc": True,
    },
    LOCAL_TLUSD_MINT: {
        "symbol": "TLUSD",
        "name": "TrancheUSD (Test Token)",
        "decimals": 6,
        "is_official_usdc": False,
    },
}


def get_configured_mint() -> str:
    """Get active token mint from environment, defaulting to official Devnet USDC."""
    return os.environ.get("TRANCHELOCK_TOKEN_MINT", OFFICIAL_DEVNET_USDC_MINT)


def get_mint_info(mint_str: str) -> Dict[str, Any]:
    """Retrieve metadata for mint. Never claim a custom mint is Circle USDC."""
    if mint_str == OFFICIAL_DEVNET_USDC_MINT:
        return ALLOWLISTED_MINTS[OFFICIAL_DEVNET_USDC_MINT]
    return {
        "symbol": "TLUSD",
        "name": "TrancheUSD (Test Token)",
        "decimals": 6,
        "is_official_usdc": False,
    }
