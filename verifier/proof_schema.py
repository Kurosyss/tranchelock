"""
TrancheLock Canonical Proof Schema
===================================
Defines the strict 153-byte binary payload for Ed25519 signature verification:
  - vault_pda:          32 bytes (Pubkey)
  - milestone_idx:       1 byte  (u8, 0-indexed)
  - agent_wallet:       32 bytes (Pubkey)
  - submission_hash:    32 bytes (SHA-256 of canonical source snapshot)
  - milestone_spec_hash:32 bytes (SHA-256 of milestone private test suite)
  - tranche_amount:      8 bytes (u64 little-endian, base token units)
  - expires_at:          8 bytes (i64 little-endian, unix timestamp)
  - nonce:               8 bytes (u64 little-endian, replay protection)
Total: 153 bytes fixed length.
"""

from dataclasses import dataclass
import hashlib
import struct
from pathlib import Path
from typing import Union
import base58

CANONICAL_PAYLOAD_SIZE = 153
FORMAT = "<32sB32s32s32sQqQ"


@dataclass(frozen=True)
class CanonicalProofPayload:
    vault_pda: bytes            # 32 bytes
    milestone_idx: int          # 1 byte (0..255)
    agent_wallet: bytes         # 32 bytes
    submission_hash: bytes      # 32 bytes
    milestone_spec_hash: bytes  # 32 bytes
    tranche_amount: int         # 8 bytes (u64)
    expires_at: int             # 8 bytes (i64)
    nonce: int                  # 8 bytes (u64)

    def serialize(self) -> bytes:
        """Deterministically serialize into exact 153-byte binary payload."""
        assert len(self.vault_pda) == 32, f"vault_pda must be 32 bytes, got {len(self.vault_pda)}"
        assert 0 <= self.milestone_idx <= 255, f"milestone_idx must be u8, got {self.milestone_idx}"
        assert len(self.agent_wallet) == 32, f"agent_wallet must be 32 bytes, got {len(self.agent_wallet)}"
        assert len(self.submission_hash) == 32, f"submission_hash must be 32 bytes, got {len(self.submission_hash)}"
        assert len(self.milestone_spec_hash) == 32, f"milestone_spec_hash must be 32 bytes, got {len(self.milestone_spec_hash)}"
        assert self.tranche_amount >= 0, "tranche_amount must be >= 0"

        packed = struct.pack(
            FORMAT,
            self.vault_pda,
            self.milestone_idx,
            self.agent_wallet,
            self.submission_hash,
            self.milestone_spec_hash,
            self.tranche_amount,
            self.expires_at,
            self.nonce,
        )
        assert len(packed) == CANONICAL_PAYLOAD_SIZE, f"Serialized payload must be {CANONICAL_PAYLOAD_SIZE} bytes"
        return packed

    @classmethod
    def deserialize(cls, data: bytes) -> "CanonicalProofPayload":
        if len(data) != CANONICAL_PAYLOAD_SIZE:
            raise ValueError(f"Payload size mismatch: expected {CANONICAL_PAYLOAD_SIZE}, got {len(data)}")
        (
            vault_pda,
            milestone_idx,
            agent_wallet,
            submission_hash,
            milestone_spec_hash,
            tranche_amount,
            expires_at,
            nonce,
        ) = struct.unpack(FORMAT, data)

        return cls(
            vault_pda=vault_pda,
            milestone_idx=milestone_idx,
            agent_wallet=agent_wallet,
            submission_hash=submission_hash,
            milestone_spec_hash=milestone_spec_hash,
            tranche_amount=tranche_amount,
            expires_at=expires_at,
            nonce=nonce,
        )


def pubkey_to_bytes(pubkey: Union[str, bytes]) -> bytes:
    """Normalize base58 string or bytes to 32-byte array."""
    if isinstance(pubkey, str):
        decoded = base58.b58decode(pubkey)
        if len(decoded) != 32:
            raise ValueError(f"Invalid pubkey length: {len(decoded)}")
        return decoded
    if isinstance(pubkey, bytes):
        if len(pubkey) != 32:
            raise ValueError(f"Invalid pubkey bytes length: {len(pubkey)}")
        return pubkey
    raise TypeError(f"Unsupported pubkey type: {type(pubkey)}")


def compute_submission_hash(source_path: Path) -> bytes:
    """
    Compute canonical SHA-256 hash of submission snapshot.
    If single file: sha256(file_content_normalized_newlines)
    If directory: sha256 of sorted list of (relpath + sha256(content))
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    if source_path.is_file():
        content = source_path.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(content).digest()

    hasher = hashlib.sha256()
    files = sorted([
        f for f in source_path.rglob("*")
        if f.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in f.parts)
    ], key=lambda p: p.as_posix())

    for f in files:
        rel_name = f.relative_to(source_path).as_posix().encode("utf-8")
        norm_content = f.read_bytes().replace(b"\r\n", b"\n")
        file_hash = hashlib.sha256(norm_content).digest()
        hasher.update(struct.pack("<H", len(rel_name)) + rel_name + file_hash)

    return hasher.digest()


def compute_spec_hash(test_suite_path: Path) -> bytes:
    """Compute SHA-256 hash of a milestone test suite file."""
    path = Path(test_suite_path)
    if not path.exists():
        raise FileNotFoundError(f"Test suite path does not exist: {path}")
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).digest()
