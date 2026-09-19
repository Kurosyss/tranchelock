use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use crate::state::TrancheVault;
use crate::errors::TrancheError;
use crate::ed25519::verify_ed25519_ix;

#[derive(Accounts)]
#[instruction(milestone_idx: u8, submission_hash: [u8; 32], nonce: u64)]
pub struct ReleaseTranche<'info> {
    #[account(
        mut,
        seeds = [b"tranche_vault", vault.sponsor.as_ref(), vault.token_mint.as_ref()],
        bump = vault.bump,
        has_one = agent @ TrancheError::AgentMismatch,
    )]
    pub vault: Account<'info, TrancheVault>,

    #[account(
        mut,
        seeds = [b"token_vault", vault.key().as_ref()],
        bump = vault.vault_bump,
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    /// CHECK: Agent recipient wallet matching vault.agent
    pub agent: AccountInfo<'info>,

    #[account(
        mut,
        token::mint = vault.token_mint,
        token::authority = agent,
    )]
    pub agent_token_account: Account<'info, TokenAccount>,

    /// CHECK: Instructions sysvar for Ed25519 introspection
    pub instructions_sysvar: AccountInfo<'info>,

    pub token_program: Program<'info, Token>,
}

pub fn release_tranche(
    ctx: Context<ReleaseTranche>,
    milestone_idx: u8,
    submission_hash: [u8; 32],
    nonce: u64,
) -> Result<()> {
    let clock = Clock::get()?;
    let vault = &mut ctx.accounts.vault;

    // 1. Guard against expired vault
    require!(clock.unix_timestamp <= vault.expires_at, TrancheError::VaultExpired);

    // 2. Guard against out-of-order or completed releases
    require!(vault.current_tranche < vault.total_tranches, TrancheError::VaultAlreadyCompleted);
    require_eq!(milestone_idx, vault.current_tranche, TrancheError::MilestoneMismatch);
    require_eq!(vault.tranche_status[milestone_idx as usize], 0, TrancheError::TrancheAlreadyProcessed);

    let amount = vault.tranche_amounts[milestone_idx as usize];
    let spec_hash = vault.milestone_spec_hashes[milestone_idx as usize];

    // 3. Reconstruct exact canonical 153-byte payload:
    // [0..32]: vault PDA
    // [32]: milestone_idx (u8)
    // [33..65]: agent wallet
    // [65..97]: submission_hash
    // [97..129]: milestone_spec_hash
    // [129..137]: tranche_amount (u64 LE)
    // [137..145]: expires_at (i64 LE)
    // [145..153]: nonce (u64 LE)
    let mut expected_message = [0u8; 153];
    expected_message[0..32].copy_from_slice(vault.key().as_ref());
    expected_message[32] = milestone_idx;
    expected_message[33..65].copy_from_slice(vault.agent.as_ref());
    expected_message[65..97].copy_from_slice(&submission_hash);
    expected_message[97..129].copy_from_slice(&spec_hash);
    expected_message[129..137].copy_from_slice(&amount.to_le_bytes());
    expected_message[137..145].copy_from_slice(&vault.expires_at.to_le_bytes());
    expected_message[145..153].copy_from_slice(&nonce.to_le_bytes());

    // 4. Strict instruction introspection of the preceding Ed25519 instruction
    let oracle_pubkey_bytes: [u8; 32] = vault.verifier_oracle.to_bytes();
    verify_ed25519_ix(
        &ctx.accounts.instructions_sysvar,
        &oracle_pubkey_bytes,
        &expected_message,
    )?;

    // 5. Transfer tranche amount from vault to agent using PDA seeds
    let sponsor_key = vault.sponsor;
    let mint_key = vault.token_mint;
    let bump = vault.bump;
    let seeds = &[
        b"tranche_vault".as_ref(),
        sponsor_key.as_ref(),
        mint_key.as_ref(),
        &[bump],
    ];
    let signer_seeds = &[&seeds[..]];

    let cpi_accounts = Transfer {
        from: ctx.accounts.vault_token_account.to_account_info(),
        to: ctx.accounts.agent_token_account.to_account_info(),
        authority: vault.to_account_info(),
    };
    let cpi_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        cpi_accounts,
        signer_seeds,
    );
    token::transfer(cpi_ctx, amount)?;

    // 6. Update onchain milestone state (replay protection)
    vault.tranche_status[milestone_idx as usize] = 1; // Released
    vault.current_tranche += 1;

    msg!(
        "TrancheLock: Milestone {} released! Amount: {} base units to agent {}",
        milestone_idx,
        amount,
        vault.agent
    );

    Ok(())
}
