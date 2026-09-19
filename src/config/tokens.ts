/**
 * TrancheLock Solana Token Configuration
 * =====================================
 * Allowlisted token mints:
 * - Official Circle Devnet USDC: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
 * - Local / Automated testing token: TLUSD (TrancheUSD)
 */

export interface TokenConfig {
  mint: string;
  symbol: string;
  name: string;
  decimals: number;
  isOfficialUsdc: boolean;
  explorerUrl: string;
}

export const DEVNET_TLUSD: TokenConfig = {
  mint: "7oKiSro2j98G3NigDYzb6EfisnnAxhg3DTTio6yf6xjW",
  symbol: "TLUSD",
  name: "TrancheUSD (Devnet Test Mint)",
  decimals: 6,
  isOfficialUsdc: false,
  explorerUrl: "https://explorer.solana.com/address/7oKiSro2j98G3NigDYzb6EfisnnAxhg3DTTio6yf6xjW?cluster=devnet",
};

export const OFFICIAL_DEVNET_USDC: TokenConfig = {
  mint: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
  symbol: "USDC",
  name: "Circle Devnet USDC",
  decimals: 6,
  isOfficialUsdc: true,
  explorerUrl: "https://explorer.solana.com/address/4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU?cluster=devnet",
};

export const ACTIVE_TOKEN: TokenConfig = DEVNET_TLUSD;
