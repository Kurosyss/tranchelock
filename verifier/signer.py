"""
TrancheLock Verifier Oracle Signer
===================================
Produces canonical Ed25519 cryptographic proofs that can be verified:
1. Offchain via PyNaCl / cryptography
2. Onchain via Solana's native Ed25519SigVerify precompile
"""

import os
from pathlib import Path
from typing import Tuple
import base58
import nacl.signing
import struct

from .proof_schema import CanonicalProofPayload, CANONICAL_PAYLOAD_SIZE


class VerifierOracleSigner:
    """Ed25519 Keypair Manager and Proof Signer for TrancheLock."""

    def __init__(self, private_key_seed: bytes = None):
        if private_key_seed is None:
            # Check environment or generate a stable test key
            env_seed = os.environ.get("TRANCHELOCK_ORACLE_SEED", "")
            if env_seed:
                private_key_seed = bytes.fromhex(env_seed)
            else:
                # Default deterministic seed for repeatable testing
                private_key_seed = hashlib_seed("tranchelock-oracle-dev-seed-2026")

        self.signing_key = nacl.signing.SigningKey(private_key_seed)
        self.verify_key = self.signing_key.verify_key
        self.public_key_bytes = self.verify_key.encode()
        self.public_key_base58 = base58.b58encode(self.public_key_bytes).decode("ascii")

    def sign_payload(self, payload: CanonicalProofPayload) -> Tuple[bytes, bytes]:
        """
        Sign canonical proof payload.
        Returns: (signature_bytes [64 bytes], canonical_message_bytes [153 bytes])
        """
        message_bytes = payload.serialize()
        signed = self.signing_key.sign(message_bytes)
        signature = signed.signature  # 64 bytes
        assert len(signature) == 64
        return signature, message_bytes

    def verify_signature(self, signature: bytes, message: bytes) -> bool:
        """Verify an Ed25519 signature against this oracle's public key."""
        try:
            self.verify_key.verify(message, signature)
            return True
        except Exception:
            return False

    def build_solana_ed25519_instruction_data(self, signature: bytes, message: bytes) -> bytes:
        """
        Construct raw instruction data for Solana's native Ed25519Program:
        Layout:
          Header (16 bytes):
            num_signatures: u8 = 1
            padding: u8 = 0
            signature_offset: u16
            signature_instruction_index: u16 = 0xffff (current instruction)
            public_key_offset: u16
            public_key_instruction_index: u16 = 0xffff
            message_data_offset: u16
            message_data_size: u16
            message_instruction_index: u16 = 0xffff
          Data:
            signature: 64 bytes
            public_key: 32 bytes
            message: N bytes (153 bytes for TrancheLock)
        """
        num_signatures = 1
        padding = 0

        header_len = 16
        sig_offset = header_len
        pubkey_offset = sig_offset + 64
        msg_offset = pubkey_offset + 32
        msg_size = len(message)

        # 0xFFFF indicates data is in the current instruction
        SAME_INSTRUCTION = 0xFFFF

        header = struct.pack(
            "<BBHHHHHHH",
            num_signatures,
            padding,
            sig_offset,
            SAME_INSTRUCTION,
            pubkey_offset,
            SAME_INSTRUCTION,
            msg_offset,
            msg_size,
            SAME_INSTRUCTION,
        )

        return header + signature + self.public_key_bytes + message


def hashlib_seed(seed_text: str) -> bytes:
    import hashlib
    return hashlib.sha256(seed_text.encode("utf-8")).digest()
