use anchor_lang::prelude::*;

#[account]
#[derive(Default)]
pub struct TrancheVault {
    /// Funder / sponsor who locks capital
    pub sponsor: Pubkey,
    /// Recipient autonomous agent wallet
    pub agent: Pubkey,
    /// Authorized offchain Ed25519 verifier oracle
    pub verifier_oracle: Pubkey,
    /// Token mint (e.g. Devnet USDC or TLUSD)
    pub token_mint: Pubkey,
    /// Milestone-specific private test suite hashes (Milestone 0..3)
    pub milestone_spec_hashes: [[u8; 32]; 4],
    /// Total number of tranches defined in this vault (1..=4)
    pub total_tranches: u8,
    /// Index of the next tranche to unlock (0, 1, 2, 3)
    pub current_tranche: u8,
    /// Base token amounts per tranche (e.g. 50_000_000 for $50 USDC)
    pub tranche_amounts: [u64; 4],
    /// Status per tranche: 0=Locked, 1=Released, 2=Refunded
    pub tranche_status: [u8; 4],
    /// Unix timestamp after which sponsor can claw back remaining funds
    pub expires_at: i64,
    /// PDA bump for TrancheVault
    pub bump: u8,
    /// PDA bump for the vault token account
    pub vault_bump: u8,
}

impl TrancheVault {
    pub const LEN: usize = 8 + // discriminator
        32 + // sponsor
        32 + // agent
        32 + // verifier_oracle
        32 + // token_mint
        (32 * 4) + // milestone_spec_hashes
        1 + // total_tranches
        1 + // current_tranche
        (8 * 4) + // tranche_amounts
        (1 * 4) + // tranche_status
        8 + // expires_at
        1 + // bump
        1; // vault_bump
}
