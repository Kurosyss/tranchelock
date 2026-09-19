use anchor_lang::prelude::*;

#[error_code]
pub enum TrancheError {
    #[msg("Milestone count must be between 1 and 4")]
    InvalidTrancheCount,
    #[msg("Tranche amounts vector length must match total_tranches")]
    AmountsLengthMismatch,
    #[msg("Vault expiration must be in the future")]
    ExpirationInPast,
    #[msg("Vault is already completed; all tranches released")]
    VaultAlreadyCompleted,
    #[msg("Milestone index does not match current tranche")]
    MilestoneMismatch,
    #[msg("Vault has expired; releases are disabled")]
    VaultExpired,
    #[msg("Vault has not expired yet; clawback is premature")]
    VaultNotExpired,
    #[msg("Tranche was already released or refunded")]
    TrancheAlreadyProcessed,
    #[msg("Invalid instructions sysvar account")]
    InvalidSysvar,
    #[msg("Missing Ed25519 precompile instruction immediately before release")]
    MissingEd25519Instruction,
    #[msg("Invalid program ID for Ed25519 instruction")]
    InvalidEd25519ProgramId,
    #[msg("Invalid Ed25519 instruction data length")]
    InvalidEd25519InstructionData,
    #[msg("Multiple signatures not allowed in Ed25519 instruction")]
    MultipleSignaturesNotAllowed,
    #[msg("Wrong oracle public key in Ed25519 proof")]
    WrongOraclePublicKey,
    #[msg("Message length in Ed25519 instruction does not match canonical 153 bytes")]
    WrongMessageLength,
    #[msg("Invalid Ed25519 instruction index offset")]
    InvalidInstructionIndexOffset,
    #[msg("Proof message bytes do not match expected canonical milestone payload")]
    InvalidMessageBytes,
    #[msg("Proof was already used; replay detected")]
    ProofReplayDetected,
    #[msg("No funds available to claw back")]
    NoFundsToClawback,
    #[msg("Agent wallet mismatch")]
    AgentMismatch,
}
