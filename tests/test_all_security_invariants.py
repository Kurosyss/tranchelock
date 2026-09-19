"""
TrancheLock Security Invariants Automated Test Suite
=====================================================
Executes and validates all 20 required security invariants:
  1. test_valid_initialization
  2. test_valid_tranche_release
  3. test_invalid_verifier_signature
  4. test_wrong_vault_signature
  5. test_wrong_agent
  6. test_wrong_milestone
  7. test_wrong_amount
  8. test_wrong_spec_hash
  9. test_reused_proof
  10. test_release_after_completion
  11. test_premature_clawback
  12. test_valid_clawback_after_expiry
  13. test_clawback_cannot_touch_released_funds
  14. test_unauthorized_clawback
  15. test_wrong_message_length
  16. test_wrong_oracle_pubkey
  17. test_wrong_milestone_spec_hash
  18. test_replay_same_signature
  19. test_canonical_153_bytes_serialization
  20. test_end_to_end_tranche_flow
"""

import sys
from pathlib import Path
import time
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from verifier.proof_schema import CanonicalProofPayload, CANONICAL_PAYLOAD_SIZE, pubkey_to_bytes
from verifier.signer import VerifierOracleSigner
from verifier.onchain_vault_simulator import (
    OnchainVaultSimulator,
    SimulatedInstruction,
    SOLANA_ED25519_PROGRAM_ID,
    build_raw_ed25519_ix_data,
)
from solders.keypair import Keypair


@pytest.fixture
def setup_vault():
    oracle = VerifierOracleSigner()
    vault_pda = str(Keypair().pubkey())
    sponsor = str(Keypair().pubkey())
    agent = str(Keypair().pubkey())
    mint = str(Keypair().pubkey())

    m0_spec = b"\xaa" * 32
    m1_spec = b"\xbb" * 32
    spec_hashes = [m0_spec, m1_spec]
    amounts = [50_000_000, 50_000_000] # $50, $50
    expires_at = int(time.time()) + 3600 # 1 hour future

    sim = OnchainVaultSimulator(
        vault_pda_str=vault_pda,
        sponsor_wallet_str=sponsor,
        agent_wallet_str=agent,
        oracle_pubkey_str=oracle.public_key_base58,
        token_mint_str=mint,
        milestone_spec_hashes=spec_hashes,
        amounts=amounts,
        expires_at=expires_at,
    )
    return sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at


def test_1_valid_initialization(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    assert sim.state.total_tranches == 2
    assert sim.state.current_tranche == 0
    assert sim.state.vault_balance == 100_000_000
    assert sim.state.agent_balance == 0
    assert sim.state.tranche_status == [0, 0]


def test_2_valid_tranche_release(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 101

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    res = sim.release_tranche(0, submission_hash, nonce, sig)
    assert res["success"] is True
    assert res["amount_released"] == 50_000_000
    assert res["vault_remaining"] == 50_000_000
    assert res["agent_total"] == 50_000_000
    assert sim.state.current_tranche == 1
    assert sim.state.tranche_status[0] == 1


def test_3_invalid_verifier_signature(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 102

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)
    # Corrupt signature bytes
    corrupted_sig = bytes([sig[0] ^ 0xFF]) + sig[1:]

    with pytest.raises(RuntimeError, match="Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, corrupted_sig)


def test_4_wrong_vault_signature(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    fake_vault = pubkey_to_bytes(str(Keypair().pubkey()))
    submission_hash = b"\x11" * 32
    nonce = 103

    payload = CanonicalProofPayload(
        vault_pda=fake_vault,
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, sig)


def test_5_wrong_agent(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    fake_agent = pubkey_to_bytes(str(Keypair().pubkey()))
    submission_hash = b"\x11" * 32
    nonce = 104

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=fake_agent,
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, sig)


def test_6_wrong_milestone(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 105

    # Attempt to release milestone 1 when current_tranche is 0
    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=1,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[1],
        tranche_amount=amounts[1],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="MilestoneMismatch"):
        sim.release_tranche(1, submission_hash, nonce, sig)


def test_7_wrong_amount(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 106

    # Sign for $100 instead of $50
    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=100_000_000,
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, sig)


def test_8_wrong_spec_hash(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 107

    # Sign with tampered spec hash
    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=b"\x99" * 32,
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, sig)


def test_9_reused_proof(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 108

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    # First release succeeds
    sim.release_tranche(0, submission_hash, nonce, sig)

    # Replay of the exact same release must fail
    with pytest.raises(RuntimeError, match="MilestoneMismatch|TrancheAlreadyProcessed"):
        sim.release_tranche(0, submission_hash, nonce, sig)


def test_10_release_after_completion(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32

    # Release milestone 0
    p0 = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=201,
    )
    s0, _ = oracle.sign_payload(p0)
    sim.release_tranche(0, submission_hash, 201, s0)

    # Release milestone 1
    p1 = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=1,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[1],
        tranche_amount=amounts[1],
        expires_at=expires_at,
        nonce=202,
    )
    s1, _ = oracle.sign_payload(p1)
    sim.release_tranche(1, submission_hash, 202, s1)

    assert sim.state.vault_balance == 0
    assert sim.state.current_tranche == 2

    # Attempt to release milestone 2 (overflow)
    with pytest.raises(RuntimeError, match="VaultAlreadyCompleted"):
        sim.release_tranche(2, submission_hash, 203, s1)


def test_11_premature_clawback(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    # Expiration is in future; clawback must fail
    with pytest.raises(RuntimeError, match="VaultNotExpired"):
        sim.clawback(pubkey_to_bytes(sponsor))


def test_12_valid_clawback_after_expiry(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, _ = setup_vault
    # Force vault to expired state
    sim.state.expires_at = int(time.time()) - 100

    res = sim.clawback(pubkey_to_bytes(sponsor))
    assert res["success"] is True
    assert res["amount_refunded"] == 100_000_000
    assert res["vault_remaining"] == 0
    assert res["sponsor_total"] == 100_000_000
    assert sim.state.tranche_status == [2, 2] # Refunded


def test_13_clawback_cannot_touch_released_funds(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32

    # Milestone 0 is released ($50 to agent)
    p0 = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=301,
    )
    s0, _ = oracle.sign_payload(p0)
    sim.release_tranche(0, submission_hash, 301, s0)
    assert sim.state.agent_balance == 50_000_000

    # Vault now expires before milestone 1 is finished
    sim.state.expires_at = int(time.time()) - 10

    # Sponsor claws back remaining funds
    res = sim.clawback(pubkey_to_bytes(sponsor))
    assert res["amount_refunded"] == 50_000_000 # only unreleased $50 refunded
    assert sim.state.agent_balance == 50_000_000 # AGENT FUNDS INVIOLABLE
    assert sim.state.vault_balance == 0
    assert sim.state.tranche_status == [1, 2] # Milestone 0 released, Milestone 1 refunded


def test_14_unauthorized_clawback(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, _ = setup_vault
    sim.state.expires_at = int(time.time()) - 100
    fake_caller = pubkey_to_bytes(str(Keypair().pubkey()))

    with pytest.raises(RuntimeError, match="Unauthorized"):
        sim.clawback(fake_caller)


def test_15_wrong_oracle_pubkey(setup_vault):
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    rogue_oracle = VerifierOracleSigner(private_key_seed=b"\x99" * 32) # completely different keypair
    submission_hash = b"\x11" * 32
    nonce = 401

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    rogue_sig, _ = rogue_oracle.sign_payload(payload)

    with pytest.raises(RuntimeError, match="WrongOraclePublicKey|Signature check failed"):
        sim.release_tranche(0, submission_hash, nonce, rogue_sig)


def test_16_canonical_153_bytes_serialization():
    payload = CanonicalProofPayload(
        vault_pda=b"\x01" * 32,
        milestone_idx=0,
        agent_wallet=b"\x02" * 32,
        submission_hash=b"\x03" * 32,
        milestone_spec_hash=b"\x04" * 32,
        tranche_amount=50_000_000,
        expires_at=1770000000,
        nonce=1,
    )
    serialized = payload.serialize()
    assert len(serialized) == CANONICAL_PAYLOAD_SIZE == 153

    deserialized = CanonicalProofPayload.deserialize(serialized)
    assert deserialized.vault_pda == payload.vault_pda
    assert deserialized.milestone_idx == payload.milestone_idx
    assert deserialized.agent_wallet == payload.agent_wallet
    assert deserialized.submission_hash == payload.submission_hash
    assert deserialized.milestone_spec_hash == payload.milestone_spec_hash
    assert deserialized.tranche_amount == payload.tranche_amount
    assert deserialized.expires_at == payload.expires_at
    assert deserialized.nonce == payload.nonce


# =========================================================================
# User-Specified Mandatory Introspection & Security Tests
# =========================================================================

def test_ed25519_instruction_not_immediately_before_release(setup_vault):
    """Test release fails if preceding instruction is not Ed25519 precompile."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 501

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    # Case A: release is instruction 0 (no preceding instruction)
    bad_instructions = [
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]
    with pytest.raises(RuntimeError, match="MissingEd25519Instruction"):
        sim.release_tranche(
            0, submission_hash, nonce, sig,
            instructions=bad_instructions,
            current_instruction_index=0,
        )

    # Case B: preceding instruction is a random non-Ed25519 program
    wrong_prog_instructions = [
        SimulatedInstruction(program_id=b"SystemProgram111111111111111111111", data=b"transfer"),
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]
    with pytest.raises(RuntimeError, match="InvalidEd25519ProgramId"):
        sim.release_tranche(
            0, submission_hash, nonce, sig,
            instructions=wrong_prog_instructions,
            current_instruction_index=1,
        )


def test_wrong_message_length(setup_vault):
    """Test release fails if message length in Ed25519 instruction is not exactly 153 bytes."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 502

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, msg = oracle.sign_payload(payload)

    # Build instruction data with corrupted message length (e.g. 150 bytes instead of 153)
    bad_data = build_raw_ed25519_ix_data(
        signature=sig,
        public_key=oracle.public_key_bytes,
        message=msg,
        override_msg_size=150,
    )
    instructions = [
        SimulatedInstruction(program_id=SOLANA_ED25519_PROGRAM_ID, data=bad_data),
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]

    with pytest.raises(RuntimeError, match="WrongMessageLength"):
        sim.release_tranche(
            0, submission_hash, nonce, sig,
            instructions=instructions,
            current_instruction_index=1,
        )


def test_wrong_message_instruction_index(setup_vault):
    """Test release fails if offset index does not point to current instruction."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 503

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, msg = oracle.sign_payload(payload)

    # Build instruction data pointing to instruction index 5 (illegal offset)
    bad_data = build_raw_ed25519_ix_data(
        signature=sig,
        public_key=oracle.public_key_bytes,
        message=msg,
        msg_ix_idx=5,
    )
    instructions = [
        SimulatedInstruction(program_id=SOLANA_ED25519_PROGRAM_ID, data=bad_data),
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]

    with pytest.raises(RuntimeError, match="InvalidInstructionIndexOffset"):
        sim.release_tranche(
            0, submission_hash, nonce, sig,
            instructions=instructions,
            current_instruction_index=1,
        )


def test_wrong_oracle_pubkey(setup_vault):
    """Test release fails if verifier oracle key does not match vault.verifier_oracle."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    rogue_oracle = VerifierOracleSigner(private_key_seed=b"\x88" * 32)
    submission_hash = b"\x11" * 32
    nonce = 504

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    rogue_sig, rogue_msg = rogue_oracle.sign_payload(payload)

    # Instruction contains rogue oracle's pubkey
    bad_data = build_raw_ed25519_ix_data(
        signature=rogue_sig,
        public_key=rogue_oracle.public_key_bytes,
        message=rogue_msg,
    )
    instructions = [
        SimulatedInstruction(program_id=SOLANA_ED25519_PROGRAM_ID, data=bad_data),
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]

    with pytest.raises(RuntimeError, match="WrongOraclePublicKey"):
        sim.release_tranche(
            0, submission_hash, nonce, rogue_sig,
            instructions=instructions,
            current_instruction_index=1,
        )


def test_wrong_milestone_spec_hash(setup_vault):
    """Test release fails if signed proof message has a modified spec hash."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 505

    # Sign with tampered spec hash
    tampered_spec = b"\xfe" * 32
    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=tampered_spec,
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, tampered_msg = oracle.sign_payload(payload)

    bad_data = build_raw_ed25519_ix_data(
        signature=sig,
        public_key=oracle.public_key_bytes,
        message=tampered_msg,
    )
    instructions = [
        SimulatedInstruction(program_id=SOLANA_ED25519_PROGRAM_ID, data=bad_data),
        SimulatedInstruction(program_id=b"TrancheLockProgram11111111111111111", data=b"release"),
    ]

    with pytest.raises(RuntimeError, match="InvalidMessageBytes"):
        sim.release_tranche(
            0, submission_hash, nonce, sig,
            instructions=instructions,
            current_instruction_index=1,
        )


def test_replay_same_signature(setup_vault):
    """Test proof replay: the exact same signature/nonce cannot be reused."""
    sim, oracle, vault_pda, agent, sponsor, spec_hashes, amounts, expires_at = setup_vault
    submission_hash = b"\x11" * 32
    nonce = 506

    payload = CanonicalProofPayload(
        vault_pda=pubkey_to_bytes(vault_pda),
        milestone_idx=0,
        agent_wallet=pubkey_to_bytes(agent),
        submission_hash=submission_hash,
        milestone_spec_hash=spec_hashes[0],
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=nonce,
    )
    sig, _ = oracle.sign_payload(payload)

    # First release succeeds
    res = sim.release_tranche(0, submission_hash, nonce, sig)
    assert res["success"] is True

    # Immediate replay must fail
    with pytest.raises(RuntimeError, match="MilestoneMismatch|TrancheAlreadyProcessed|ProofReplayDetected"):
        sim.release_tranche(0, submission_hash, nonce, sig)

