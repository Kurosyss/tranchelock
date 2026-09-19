use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};
use crate::state::TrancheVault;
use crate::errors::TrancheError;

#[derive(Accounts)]
#[instruction(amounts: Vec<u64>, milestone_spec_hashes: Vec<[u8; 32]>, expires_at: i64)]
pub struct InitializeVault<'info> {
    #[account(
        init,
        payer = sponsor,
        space = TrancheVault::LEN,
        seeds = [b"tranche_vault", sponsor.key().as_ref(), token_mint.key().as_ref()],
        bump
    )]
    pub vault: Account<'info, TrancheVault>,

    #[account(
        init,
        payer = sponsor,
        seeds = [b"token_vault", vault.key().as_ref()],
        bump,
        token::mint = token_mint,
        token::authority = vault,
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub sponsor: Signer<'info>,

    /// CHECK: Recipient autonomous agent wallet
    pub agent: AccountInfo<'info>,

    /// CHECK: Authorized offchain Ed25519 verifier oracle key
    pub verifier_oracle: AccountInfo<'info>,

    pub token_mint: Account<'info, Mint>,

    #[account(
        mut,
        token::mint = token_mint,
        token::authority = sponsor,
    )]
    pub sponsor_token_account: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn initialize_vault(
    ctx: Context<InitializeVault>,
    amounts: Vec<u64>,
    milestone_spec_hashes: Vec<[u8; 32]>,
    expires_at: i64,
) -> Result<()> {
    let clock = Clock::get()?;
    require!(expires_at > clock.unix_timestamp, TrancheError::ExpirationInPast);

    let n = amounts.len();
    require!(n >= 1 && n <= 4, TrancheError::InvalidTrancheCount);
    require_eq!(milestone_spec_hashes.len(), n, TrancheError::AmountsLengthMismatch);

    let mut total_amount: u64 = 0;
    let mut tranche_amounts = [0u64; 4];
    let mut spec_hashes = [[0u8; 32]; 4];

    for i in 0..n {
        tranche_amounts[i] = amounts[i];
        spec_hashes[i] = milestone_spec_hashes[i];
        total_amount = total_amount.checked_add(amounts[i]).ok_or(ProgramError::ArithmeticOverflow)?;
    }

    // Transfer total tokens from sponsor to vault token account
    let cpi_accounts = Transfer {
        from: ctx.accounts.sponsor_token_account.to_account_info(),
        to: ctx.accounts.vault_token_account.to_account_info(),
        authority: ctx.accounts.sponsor.to_account_info(),
    };
    let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts);
    token::transfer(cpi_ctx, total_amount)?;

    let vault = &mut ctx.accounts.vault;
    vault.sponsor = ctx.accounts.sponsor.key();
    vault.agent = ctx.accounts.agent.key();
    vault.verifier_oracle = ctx.accounts.verifier_oracle.key();
    vault.token_mint = ctx.accounts.token_mint.key();
    vault.milestone_spec_hashes = spec_hashes;
    vault.total_tranches = n as u8;
    vault.current_tranche = 0;
    vault.tranche_amounts = tranche_amounts;
    vault.tranche_status = [0u8; 4]; // all locked
    vault.expires_at = expires_at;
    vault.bump = ctx.bumps.vault;
    vault.vault_bump = ctx.bumps.vault_token_account;

    Ok(())
}
