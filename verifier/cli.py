"""
CLI Interface for TrancheLock Verifier Oracle
Invoked by scripts/devnet_vertical_slice.ts to run the genuine verifier pipeline:
private test suite -> sandbox -> deterministic evidence -> Gemini criteria -> Ed25519 signature
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parent / "verifywork-poc"))

from verifier.service import TrancheVerifierService
from verifier.proof_schema import compute_spec_hash


def main():
    parser = argparse.ArgumentParser(description="TrancheLock Verifier Oracle CLI")
    parser.add_argument("--vault-pda", required=True, help="TrancheVault PDA address")
    parser.add_argument("--milestone-idx", type=int, required=True, help="Milestone index (0..3)")
    parser.add_argument("--agent-wallet", required=True, help="Agent wallet address")
    parser.add_argument("--code-path", type=str, required=True, help="Path to agent code submission")
    parser.add_argument("--test-path", type=str, required=True, help="Path to private test harness")
    parser.add_argument("--amount", type=int, required=True, help="Tranche amount in base units")
    parser.add_argument("--expires-at", type=int, required=True, help="Unix expiry timestamp")
    parser.add_argument("--nonce", type=int, default=1001, help="Unique anti-replay nonce")
    parser.add_argument("--criteria", nargs="*", default=["Code passes all tests and requirements"], help="Acceptance criteria")

    args = parser.parse_args()

    code_file = Path(args.code_path)
    test_file = Path(args.test_path)

    if not code_file.exists():
        print(json.dumps({"error": f"Code file not found: {code_file}"}))
        sys.exit(1)
    if not test_file.exists():
        print(json.dumps({"error": f"Test file not found: {test_file}"}))
        sys.exit(1)

    spec_hash = compute_spec_hash(test_file)
    verifier = TrancheVerifierService()

    result = verifier.verify_milestone_and_sign(
        vault_pda_str=args.vault_pda,
        milestone_idx=args.milestone_idx,
        agent_wallet_str=args.agent_wallet,
        code_source_path=code_file,
        private_test_path=test_file,
        expected_spec_hash_bytes=spec_hash,
        tranche_amount=args.amount,
        expires_at=args.expires_at,
        nonce=args.nonce,
        acceptance_criteria=args.criteria,
    )

    output = {
        "status": result.get("status"),
        "verified": result.get("verified", False),
        "reasoning": result.get("reasoning", ""),
        "oracle_pubkey": verifier.oracle_pubkey_base58,
        "signature_hex": result.get("signature_hex"),
        "ed25519_instruction_data_hex": result.get("ed25519_instruction_data").hex() if result.get("ed25519_instruction_data") else None,
        "submission_hash_hex": result.get("submission_hash"),
        "milestone_spec_hash_hex": result.get("milestone_spec_hash"),
        "nonce": args.nonce,
    }

    # Print pure JSON to stdout
    print("\n__VERIFIER_JSON_OUTPUT_START__")
    print(json.dumps(output))
    print("__VERIFIER_JSON_OUTPUT_END__")


if __name__ == "__main__":
    main()
