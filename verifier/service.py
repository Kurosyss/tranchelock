"""
TrancheLock Verifier Oracle Service
====================================
Integrates:
1. Private milestone test suite integrity check (SHA-256)
2. Sandboxed pytest execution
3. Deterministic evidence extraction
4. Gemini criteria reasoning & audit generation
5. Canonical 153-byte Ed25519 signature authorization
"""

import sys
from pathlib import Path
import os
import textwrap

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parent / "verifywork-poc"))

from verifier.proof_schema import (
    CanonicalProofPayload,
    compute_submission_hash,
    compute_spec_hash,
    pubkey_to_bytes,
)
from verifier.signer import VerifierOracleSigner

import shutil

# Import Phase 1 engine components
from verify import run_in_sandbox, extract_objective_evidence, ai_interpret, SandboxResult


def detect_sandbox_environment() -> dict:
    """
    Detect genuine execution isolation mechanism:
    1. E2B: E2B Sandbox microVM (genuinely isolated ephemeral VM)
    2. DOCKER: Docker container run with --network none
    3. LOCAL_DEV: Local subprocess (development only; network isolation NOT OS-enforced)
    """
    if os.environ.get("E2B_API_KEY"):
        return {
            "type": "e2b",
            "network_isolated": True,
            "description": "E2B Ephemeral Sandbox (Hardware-Isolated MicroVM)",
        }
    if shutil.which("docker") and os.environ.get("USE_DOCKER_SANDBOX"):
        return {
            "type": "docker",
            "network_isolated": True,
            "description": "Docker Container with --network none (Zero Network Leakage Enforced)",
        }
    return {
        "type": "local_dev",
        "network_isolated": False,
        "description": "Local Subprocess (DEV ONLY - Network isolation NOT OS-enforced)",
    }


class TrancheVerifierService:
    def __init__(self, private_key_seed: bytes = None):
        self.oracle_signer = VerifierOracleSigner(private_key_seed)
        self.oracle_pubkey_base58 = self.oracle_signer.public_key_base58
        self.sandbox_env = detect_sandbox_environment()

    def verify_milestone_and_sign(
        self,
        vault_pda_str: str,
        milestone_idx: int,
        agent_wallet_str: str,
        code_source_path: Path,
        private_test_path: Path,
        expected_spec_hash_bytes: bytes,
        tranche_amount: int,
        expires_at: int,
        nonce: int,
        acceptance_criteria: list[str],
    ) -> dict:
        """
        Execute full end-to-end verification pipeline.
        Returns signed release payload if and only if all tests pass.
        """
        print(f"\n{'='*70}")
        print(f"  TRANCHELOCK VERIFIER ORACLE // MILESTONE [{milestone_idx}]")
        print(f"  Vault:  {vault_pda_str}")
        print(f"  Agent:  {agent_wallet_str}")
        print(f"  Oracle: {self.oracle_pubkey_base58}")
        print(f"{'='*70}")

        # 1. Private test suite integrity check
        print("  [1/5] Verifying private test suite integrity...")
        actual_spec_hash = compute_spec_hash(private_test_path)
        if actual_spec_hash != expected_spec_hash_bytes:
            return {
                "status": "FAILED_SPEC_INTEGRITY",
                "verified": False,
                "reasoning": f"Milestone test suite hash mismatch! Expected {expected_spec_hash_bytes.hex()[:16]}..., got {actual_spec_hash.hex()[:16]}...",
                "signature": None,
                "ed25519_instruction_data": None,
            }
        print(f"        * Spec Hash: {actual_spec_hash.hex()[:16]}... OK")

        # 2. Compute canonical submission snapshot hash
        print("  [2/5] Computing canonical submission snapshot hash...")
        submission_hash = compute_submission_hash(code_source_path)
        print(f"        * Submission Hash: {submission_hash.hex()[:16]}...")

        # 3. Sandboxed execution
        print("  [3/5] Executing sandbox runner with private test harness...")
        print(f"        * Sandbox Engine: {self.sandbox_env['description']}")
        if os.environ.get("REQUIRE_NETWORK_ISOLATION", "").lower() in ("true", "1") and not self.sandbox_env["network_isolated"]:
            return {
                "status": "FAILED_SECURITY_POLICY",
                "verified": False,
                "reasoning": f"Security policy violation: Production requires verified network isolation. Current environment: {self.sandbox_env['type']}",
                "signature": None,
                "ed25519_instruction_data": None,
            }

        import tempfile
        import uuid

        work_dir = Path(tempfile.gettempdir()) / f"tranche_verify_m{milestone_idx}_{uuid.uuid4().hex[:8]}"
        work_dir.mkdir(exist_ok=True, parents=True)

        import shutil
        try:
            # Copy submission code into sandbox
            dest_code = work_dir / "submission.py"
            shutil.copy2(code_source_path, dest_code)

            # Copy private test harness into sandbox
            dest_test = work_dir / "test_suite.py"
            shutil.copy2(private_test_path, dest_test)

            test_cmd = [
                sys.executable, "-m", "pytest",
                "test_suite.py",
                "-v",
                "--tb=short",
                "--no-header",
            ]

            sandbox: SandboxResult = run_in_sandbox(dest_code, work_dir, test_cmd)
            evidence = extract_objective_evidence(sandbox)
            for e in evidence:
                print(f"        * {e}")

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        # 4. Gemini Criteria Mapping & Audit Explanation
        print("  [4/5] Gemini 3.5 evaluating criteria & generating audit reasoning...")
        ai_result = ai_interpret(acceptance_criteria, evidence, sandbox)
        reasoning = ai_result.get("reasoning", "")
        print(f"        * AI Reasoning: {reasoning}")

        # 5. Security Authorization & Ed25519 Signing
        print("  [5/5] Evaluating authorization policy...")
        tests_passed = sandbox.exit_code == 0 and not sandbox.timed_out and not sandbox.error

        if not tests_passed:
            print(f"        [!] Tests failed (exit_code={sandbox.exit_code}). ZERO FUNDS AUTHORIZED.")
            return {
                "status": "FAIL",
                "verified": False,
                "sandbox_exit_code": sandbox.exit_code,
                "evidence": evidence,
                "reasoning": reasoning,
                "signature": None,
                "ed25519_instruction_data": None,
                "submission_hash": submission_hash.hex(),
            }

        print("        [+] 100% tests PASSED. Authorizing milestone release.")

        # Construct canonical 153-byte payload
        vault_bytes = pubkey_to_bytes(vault_pda_str)
        agent_bytes = pubkey_to_bytes(agent_wallet_str)

        payload = CanonicalProofPayload(
            vault_pda=vault_bytes,
            milestone_idx=milestone_idx,
            agent_wallet=agent_bytes,
            submission_hash=submission_hash,
            milestone_spec_hash=actual_spec_hash,
            tranche_amount=tranche_amount,
            expires_at=expires_at,
            nonce=nonce,
        )

        signature, message = self.oracle_signer.sign_payload(payload)
        ix_data = self.oracle_signer.build_solana_ed25519_instruction_data(signature, message)

        print(f"        [+] Ed25519 Signature generated: {signature.hex()[:16]}...")
        print(f"        [+] Solana precompile instruction data prepared: {len(ix_data)} bytes")

        return {
            "status": "PASS",
            "verified": True,
            "sandbox_exit_code": sandbox.exit_code,
            "evidence": evidence,
            "reasoning": reasoning,
            "signature_hex": signature.hex(),
            "signature_bytes": signature,
            "ed25519_instruction_data": ix_data,
            "submission_hash": submission_hash.hex(),
            "submission_hash_bytes": submission_hash,
            "milestone_spec_hash": actual_spec_hash.hex(),
            "nonce": nonce,
        }
