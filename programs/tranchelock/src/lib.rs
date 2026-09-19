use anchor_lang::prelude::*;

pub mod state;
pub mod errors;
pub mod ed25519;
pub mod instructions;

use instructions::*;

declare_id!("3SBmcsZqGHbLzxrBR2ZzrfSnufHFpzM6GHY6TiijebtM");

#[program]
pub mod tranchelock {
    use super::*;

    /// Initialize a multi-tranche escrow vault funded with SPL tokens (Devnet USDC / TLUSD)
    pub fn initialize_vault(
        ctx: Context<InitializeVault>,
        amounts: Vec<u64>,
        milestone_spec_hashes: Vec<[u8; 32]>,
        expires_at: i64,
    ) -> Result<()> {
        instructions::initialize_vault(ctx, amounts, milestone_spec_hashes, expires_at)
    }

    /// Release the current milestone tranche upon verified Ed25519 oracle proof
    pub fn release_tranche(
        ctx: Context<ReleaseTranche>,
        milestone_idx: u8,
        submission_hash: [u8; 32],
        nonce: u64,
    ) -> Result<()> {
        instructions::release_tranche(ctx, milestone_idx, submission_hash, nonce)
    }

    /// Refund unreleased tranches to the sponsor if vault expired without completion
    pub fn clawback(ctx: Context<Clawback>) -> Result<()> {
        instructions::clawback(ctx)
    }
}
