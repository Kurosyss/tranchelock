use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use crate::state::TrancheVault;
use crate::errors::TrancheError;

#[derive(Accounts)]
pub struct Clawback<'info> {
    #[account(
        mut,
        seeds = [b"tranche_vault", vault.sponsor.as_ref(), vault.token_mint.as_ref()],
        bump = vault.bump,
        has_one = sponsor,
    )]
    pub vault: Account<'info, TrancheVault>,

    #[account(
        mut,
        seeds = [b"token_vault", vault.key().as_ref()],
        bump = vault.vault_bump,
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub sponsor: Signer<'info>,

    #[account(
        mut,
        token::mint = vault.token_mint,
        token::authority = sponsor,
    )]
    pub sponsor_token_account: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn clawback(ctx: Context<Clawback>) -> Result<()> {
    let clock = Clock::get()?;
    let vault = &mut ctx.accounts.vault;

    // 1. Guard against premature clawback
    require!(clock.unix_timestamp > vault.expires_at, TrancheError::VaultNotExpired);

    // 2. Compute refundable balance (sum of unreleased tranches)
    let mut refundable_amount: u64 = 0;
    for i in 0..vault.total_tranches as usize {
        if vault.tranche_status[i] == 0 {
            refundable_amount = refundable_amount
                .checked_add(vault.tranche_amounts[i])
                .ok_or(ProgramError::ArithmeticOverflow)?;
            vault.tranche_status[i] = 2; // Refunded
        }
    }

    require!(refundable_amount > 0, TrancheError::NoFundsToClawback);

    // 3. Transfer unreleased tokens back to sponsor using PDA signer seeds
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
        to: ctx.accounts.sponsor_token_account.to_account_info(),
        authority: vault.to_account_info(),
    };
    let cpi_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        cpi_accounts,
        signer_seeds,
    );
    token::transfer(cpi_ctx, refundable_amount)?;

    msg!(
        "TrancheLock: Timelock clawback executed! Returned {} base units to sponsor {}",
        refundable_amount,
        sponsor_key
    );

    Ok(())
}
