use anchor_lang::prelude::*;
use anchor_lang::solana_program::sysvar::instructions::{
    load_current_index_checked, load_instruction_at_checked, ID as INSTRUCTIONS_SYSVAR_ID,
};
use anchor_lang::solana_program::ed25519_program::ID as ED25519_PROGRAM_ID;
use crate::errors::TrancheError;

/// Verify that the instruction immediately preceding release_tranche is a valid
/// Ed25519Program instruction that verified expected_pubkey's signature over expected_message.
pub fn verify_ed25519_ix(
    instructions_sysvar: &AccountInfo,
    expected_pubkey: &[u8; 32],
    expected_message: &[u8],
) -> Result<()> {
    // 1. Verify instructions sysvar account key
    require_keys_eq!(*instructions_sysvar.key, INSTRUCTIONS_SYSVAR_ID, TrancheError::InvalidSysvar);

    // 2. Get current instruction index
    let current_index = load_current_index_checked(instructions_sysvar)?;

    // 3. Ed25519 instruction MUST occur immediately before release_tranche (current_index - 1)
    require!(current_index > 0, TrancheError::MissingEd25519Instruction);
    let ed25519_index = (current_index - 1) as usize;

    let ed25519_ix = load_instruction_at_checked(ed25519_index, instructions_sysvar)?;

    // 4. Verify program ID is the native Ed25519 precompile
    require_keys_eq!(ed25519_ix.program_id, ED25519_PROGRAM_ID, TrancheError::InvalidEd25519ProgramId);

    // 5. Check instruction data structure
    let data = &ed25519_ix.data;
    require!(data.len() >= 16, TrancheError::InvalidEd25519InstructionData);

    let num_signatures = data[0];
    require!(num_signatures == 1, TrancheError::MultipleSignaturesNotAllowed);

    let _signature_offset = u16::from_le_bytes([data[2], data[3]]) as usize;
    let signature_ix_idx = u16::from_le_bytes([data[4], data[5]]);
    let public_key_offset = u16::from_le_bytes([data[6], data[7]]) as usize;
    let public_key_ix_idx = u16::from_le_bytes([data[8], data[9]]);
    let message_data_offset = u16::from_le_bytes([data[10], data[11]]) as usize;
    let message_data_size = u16::from_le_bytes([data[12], data[13]]) as usize;
    let message_ix_idx = u16::from_le_bytes([data[14], data[15]]);

    // 6. Enforce offsets point to this exact instruction (0xffff or index == ed25519_index)
    require!(
        signature_ix_idx == u16::MAX || signature_ix_idx as usize == ed25519_index,
        TrancheError::InvalidInstructionIndexOffset
    );
    require!(
        public_key_ix_idx == u16::MAX || public_key_ix_idx as usize == ed25519_index,
        TrancheError::InvalidInstructionIndexOffset
    );
    require!(
        message_ix_idx == u16::MAX || message_ix_idx as usize == ed25519_index,
        TrancheError::InvalidInstructionIndexOffset
    );

    // 7. Verify message length matches canonical size
    require_eq!(message_data_size, expected_message.len(), TrancheError::WrongMessageLength);

    // 8. Extract and verify public key
    require!(data.len() >= public_key_offset + 32, TrancheError::InvalidEd25519InstructionData);
    let pubkey_bytes = &data[public_key_offset..public_key_offset + 32];
    require!(pubkey_bytes == expected_pubkey, TrancheError::WrongOraclePublicKey);

    // 9. Extract and verify exact message bytes
    require!(data.len() >= message_data_offset + message_data_size, TrancheError::InvalidEd25519InstructionData);
    let message_bytes = &data[message_data_offset..message_data_offset + message_data_size];
    require!(message_bytes == expected_message, TrancheError::InvalidMessageBytes);

    Ok(())
}
