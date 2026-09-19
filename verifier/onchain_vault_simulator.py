"""
TrancheLock Onchain Vault State Machine & Validator
====================================================
Implements exact onchain invariants matching programs/tranchelock/src:
1. Reconstructs canonical 153-byte payload from onchain state
2. Cryptographically verifies Ed25519 oracle signature
3. Enforces milestone order (milestone_idx == current_tranche)
4. Enforces expiration timelock
5. Prevents replay attacks (updates tranche_status & current_tranche)
6. Enforces token balance accounting ($100 locked -> $50 released -> $50 released -> 0 remaining)
"""

from dataclasses import dataclass
from typing import List, Optional
import time
import struct
import base58
import nacl.signing

from .proof_schema import CanonicalProofPayload, CANONICAL_PAYLOAD_SIZE, pubkey_to_bytes

SOLANA_ED25519_PROGRAM_ID = base58.b58decode("Ed25519SigVerify111111111111111111111111111")


@dataclass
class SimulatedInstruction:
    program_id: bytes
    data: bytes
    accounts: Optional[List[bytes]] = None


def build_raw_ed25519_ix_data(
    signature: bytes,
    public_key: bytes,
    message: bytes,
    sig_ix_idx: int = 0xFFFF,
    pubkey_ix_idx: int = 0xFFFF,
    msg_ix_idx: int = 0xFFFF,
    override_msg_size: Optional[int] = None,
) -> bytes:
    """Build raw instruction data for Solana Ed25519 precompile."""
    num_signatures = 1
    padding = 0
    header_len = 16
    sig_offset = header_len
    pubkey_offset = sig_offset + len(signature)
    msg_offset = pubkey_offset + len(public_key)
    msg_size = override_msg_size if override_msg_size is not None else len(message)

    header = struct.pack(
        "<BBHHHHHHH",
        num_signatures,
        padding,
        sig_offset,
        sig_ix_idx,
        pubkey_offset,
        pubkey_ix_idx,
        msg_offset,
        msg_size,
        msg_ix_idx,
    )
    return header + signature + public_key + message


@dataclass
class TrancheVaultState:
    sponsor: bytes
    agent: bytes
    verifier_oracle: bytes
    token_mint: bytes
    milestone_spec_hashes: List[bytes]
    total_tranches: int
    current_tranche: int
    tranche_amounts: List[int]
    tranche_status: List[int]  # 0=Locked, 1=Released, 2=Refunded
    expires_at: int
    vault_balance: int
    agent_balance: int = 0
    sponsor_balance: int = 0


class OnchainVaultSimulator:
    def __init__(
        self,
        vault_pda_str: str,
        sponsor_wallet_str: str,
        agent_wallet_str: str,
        oracle_pubkey_str: str,
        token_mint_str: str,
        milestone_spec_hashes: List[bytes],
        amounts: List[int],
        expires_at: int,
    ):
        self.vault_pda = pubkey_to_bytes(vault_pda_str)
        self.sponsor = pubkey_to_bytes(sponsor_wallet_str)
        self.agent = pubkey_to_bytes(agent_wallet_str)
        self.oracle = pubkey_to_bytes(oracle_pubkey_str)
        self.token_mint = pubkey_to_bytes(token_mint_str)

        total_amount = sum(amounts)
        assert len(amounts) == len(milestone_spec_hashes)
        assert 1 <= len(amounts) <= 4

        self.state = TrancheVaultState(
            sponsor=self.sponsor,
            agent=self.agent,
            verifier_oracle=self.oracle,
            token_mint=self.token_mint,
            milestone_spec_hashes=milestone_spec_hashes,
            total_tranches=len(amounts),
            current_tranche=0,
            tranche_amounts=amounts,
            tranche_status=[0] * len(amounts),
            expires_at=expires_at,
            vault_balance=total_amount,
            agent_balance=0,
            sponsor_balance=0,
        )

        # Nonce tracking for replay protection
        self.used_nonces = set()

    def release_tranche(
        self,
        milestone_idx: int,
        submission_hash: bytes,
        nonce: int,
        signature: bytes,
        instructions: Optional[List[SimulatedInstruction]] = None,
        current_instruction_index: Optional[int] = None,
    ) -> dict:
        """
        Executes onchain release_tranche validation with strict instruction introspection.
        Matches programs/tranchelock/src/instructions/release_tranche.rs and
        programs/tranchelock/src/ed25519.rs line-by-line.
        """
        now = int(time.time())

        # 1. Expiration check
        if now > self.state.expires_at:
            raise RuntimeError("VaultExpired: Releases disabled after expiration")

        # 2. Replay & Milestone Order checks
        if self.state.current_tranche >= self.state.total_tranches:
            raise RuntimeError("VaultAlreadyCompleted: All tranches released")

        if milestone_idx != self.state.current_tranche:
            raise RuntimeError(f"MilestoneMismatch: Expected {self.state.current_tranche}, got {milestone_idx}")

        if self.state.tranche_status[milestone_idx] != 0:
            raise RuntimeError("TrancheAlreadyProcessed: Tranche was already released or refunded")

        if nonce in self.used_nonces:
            raise RuntimeError("ProofReplayDetected: Nonce already used")

        # 3. Canonical 153-byte Message Reconstruction
        amount = self.state.tranche_amounts[milestone_idx]
        spec_hash = self.state.milestone_spec_hashes[milestone_idx]

        payload = CanonicalProofPayload(
            vault_pda=self.vault_pda,
            milestone_idx=milestone_idx,
            agent_wallet=self.agent,
            submission_hash=submission_hash,
            milestone_spec_hash=spec_hash,
            tranche_amount=amount,
            expires_at=self.state.expires_at,
            nonce=nonce,
        )
        expected_message = payload.serialize()
        assert len(expected_message) == CANONICAL_PAYLOAD_SIZE

        # 4. Synthesize instructions if none provided
        if instructions is None:
            raw_ix_data = build_raw_ed25519_ix_data(signature, self.oracle, expected_message)
            instructions = [
                SimulatedInstruction(program_id=SOLANA_ED25519_PROGRAM_ID, data=raw_ix_data),
                SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
            ]
            current_instruction_index = 1

        # 5. Strict Instructions Sysvar Introspection (matching ed25519.rs)
        if current_instruction_index is None or current_instruction_index == 0:
            raise RuntimeError("MissingEd25519Instruction: Missing Ed25519 precompile instruction immediately before release")

        ed25519_index = current_instruction_index - 1
        if ed25519_index >= len(instructions):
            raise RuntimeError("MissingEd25519Instruction: Invalid instruction index")

        ed25519_ix = instructions[ed25519_index]

        # 5a. Verify Program ID
        if ed25519_ix.program_id != SOLANA_ED25519_PROGRAM_ID:
            raise RuntimeError("InvalidEd25519ProgramId: Invalid program ID for Ed25519 instruction")

        # 5b. Verify data structure length
        data = ed25519_ix.data
        if len(data) < 16:
            raise RuntimeError("InvalidEd25519InstructionData: Invalid Ed25519 instruction data length")

        # 5c. Exactly one signature
        num_signatures = data[0]
        if num_signatures != 1:
            raise RuntimeError("MultipleSignaturesNotAllowed: Multiple signatures not allowed in Ed25519 instruction")

        sig_offset, sig_ix_idx, pubkey_offset, pubkey_ix_idx, msg_offset, msg_size, msg_ix_idx = struct.unpack_from("<HHHHHHH", data, 2)

        # 5d. Instruction index offsets must point to current instruction
        if sig_ix_idx not in (0xFFFF, ed25519_index) or pubkey_ix_idx not in (0xFFFF, ed25519_index) or msg_ix_idx not in (0xFFFF, ed25519_index):
            raise RuntimeError("InvalidInstructionIndexOffset: Invalid Ed25519 instruction index offset")

        # 5e. Message length check
        if msg_size != len(expected_message):
            raise RuntimeError("WrongMessageLength: Message length in Ed25519 instruction does not match canonical 153 bytes")

        # 5f. Verify public key
        if len(data) < pubkey_offset + 32:
            raise RuntimeError("InvalidEd25519InstructionData: Public key out of bounds")
        pubkey_bytes = data[pubkey_offset:pubkey_offset + 32]
        if pubkey_bytes != self.oracle:
            raise RuntimeError("WrongOraclePublicKey: Wrong oracle public key in Ed25519 proof")

        # 5g. Verify message bytes
        if len(data) < msg_offset + msg_size:
            raise RuntimeError("InvalidEd25519InstructionData: Message out of bounds")
        msg_bytes = data[msg_offset:msg_offset + msg_size]
        if msg_bytes != expected_message:
            raise RuntimeError("InvalidMessageBytes: Proof message bytes do not match expected canonical milestone payload")

        # 5h. Cryptographic Ed25519 signature check
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        try:
            verify_key.verify(expected_message, signature)
        except Exception:
            raise RuntimeError("Signature check failed: Invalid signature bytes")

        # 6. Token Transfer & State Updates
        assert self.state.vault_balance >= amount, "Insufficient vault balance"
        self.state.vault_balance -= amount
        self.state.agent_balance += amount
        self.state.tranche_status[milestone_idx] = 1  # Released
        self.state.current_tranche += 1
        self.used_nonces.add(nonce)

        return {
            "success": True,
            "milestone_idx": milestone_idx,
            "amount_released": amount,
            "vault_remaining": self.state.vault_balance,
            "agent_total": self.state.agent_balance,
            "is_completed": self.state.current_tranche == self.state.total_tranches,
        }

    def clawback(self, caller: bytes) -> dict:
        """
        Executes onchain clawback validation.
        Matches programs/tranchelock/src/instructions/clawback.rs exactly.
        """
        if caller != self.state.sponsor:
            raise RuntimeError("Unauthorized: Only sponsor can claw back")

        now = int(time.time())
        if now <= self.state.expires_at:
            raise RuntimeError("VaultNotExpired: Cannot claw back before expires_at")

        refundable = 0
        for i in range(self.state.total_tranches):
            if self.state.tranche_status[i] == 0:
                refundable += self.state.tranche_amounts[i]
                self.state.tranche_status[i] = 2  # Refunded

        if refundable == 0:
            raise RuntimeError("NoFundsToClawback: No unreleased funds remaining")

        assert self.state.vault_balance >= refundable
        self.state.vault_balance -= refundable
        self.state.sponsor_balance += refundable

        return {
            "success": True,
            "amount_refunded": refundable,
            "vault_remaining": self.state.vault_balance,
            "sponsor_total": self.state.sponsor_balance,
        }
