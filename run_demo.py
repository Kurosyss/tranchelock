"""
TrancheLock End-to-End Reproducible Demo
=========================================
Runs the exact 12-step milestone-gated capital lifecycle:
  1. Sponsor initializes vault with $100 TLUSD on Solana
  2. Agent submits Milestone 1 implementation (m1_correct.py)
  3. Sandboxed pytest runs against private Milestone 1 test suite
  4. Tests pass -> Gemini evaluates criteria -> Ed25519 oracle signs canonical 153-byte proof
  5. $50 TLUSD releases to Agent wallet. Vault balance: $50 remaining.
  6. Agent submits flawed Milestone 2 implementation (m2_broken.py)
  7. Sandboxed tests fail (negative n & empty list unhandled)
  8. $0 releases. Zero signature authorized. Structured failure feedback generated.
  9. Agent fixes implementation (m2_fixed.py)
  10. Sandboxed tests pass -> Gemini verifies -> Oracle signs proof
  11. Remaining $50 TLUSD releases to Agent wallet. Vault balance: $0.
  12. Vault transitions to COMPLETED.
"""

import sys
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from verifier.proof_schema import compute_spec_hash, pubkey_to_bytes
from verifier.service import TrancheVerifierService
from verifier.onchain_vault_simulator import OnchainVaultSimulator
from solders.keypair import Keypair

# Terminal styling
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
PURPLE = "\033[35m"
RESET = "\033[0m"


def print_banner(text: str):
    print(f"\n{BOLD}{CYAN}{'='*75}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*75}{RESET}")


def print_step(step_num: int, title: str):
    print(f"\n{BOLD}{PURPLE}--- [STEP {step_num}] {title} ---{RESET}")


def run_full_demo():
    print_banner("TRANCHELOCK // AUTONOMOUS AGENT CAPITAL SETTLEMENT DEMO")

    # 1. Setup Identities
    sponsor_kp = Keypair()
    agent_kp = Keypair()
    vault_pda = str(Keypair().pubkey())
    sponsor_wallet = str(sponsor_kp.pubkey())
    agent_wallet = str(agent_kp.pubkey())
    token_mint = "TLUSD_MINT_6DECIMALS"

    # Private test suites
    fixtures_dir = PROJECT_ROOT / "fixtures"
    m1_test = fixtures_dir / "milestone1_private_test.py"
    m2_test = fixtures_dir / "milestone2_private_test.py"

    m1_spec_hash = compute_spec_hash(m1_test)
    m2_spec_hash = compute_spec_hash(m2_test)

    # Verifier Oracle
    verifier = TrancheVerifierService()
    oracle_pubkey = verifier.oracle_pubkey_base58

    print(f"  Sponsor Wallet:  {sponsor_wallet}")
    print(f"  Agent Wallet:    {agent_wallet}")
    print(f"  Vault PDA:       {vault_pda}")
    print(f"  Verifier Oracle: {oracle_pubkey}")
    print(f"  Milestone 1 Hash:{m1_spec_hash.hex()[:16]}...")
    print(f"  Milestone 2 Hash:{m2_spec_hash.hex()[:16]}...")

    # Initialize Simulator / Onchain Program
    amounts = [50_000_000, 50_000_000] # $50, $50
    expires_at = int(time.time()) + 86400 # 24 hours

    # Step 1: Sponsor locks $100 USDC
    print_step(1, "SPONSOR INITIALIZES VAULT WITH $100.00 TLUSD ESCROW")
    sim = OnchainVaultSimulator(
        vault_pda_str=vault_pda,
        sponsor_wallet_str=sponsor_wallet,
        agent_wallet_str=agent_wallet,
        oracle_pubkey_str=oracle_pubkey,
        token_mint_str=str(Keypair().pubkey()),
        milestone_spec_hashes=[m1_spec_hash, m2_spec_hash],
        amounts=amounts,
        expires_at=expires_at,
    )
    print(f"  {GREEN}[OK]{RESET} Vault created on Solana.")
    print(f"  Locked Balance:  {BOLD}${sim.state.vault_balance / 1e6:.2f} TLUSD{RESET}")
    print(f"  Total Tranches:  {sim.state.total_tranches} (Tranche 0: $50.00, Tranche 1: $50.00)")
    print(f"  Agent Balance:   ${sim.state.agent_balance / 1e6:.2f}")

    # Step 2: Agent submits Milestone 1
    print_step(2, "AGENT SUBMITS MILESTONE 1 IMPLEMENTATION (m1_correct.py)")
    m1_submission = fixtures_dir / "agent_submissions" / "m1_correct.py"
    print(f"  Target File: {m1_submission}")

    # Step 3 & 4: Verifier runs tests & signs proof
    print_step(3, "VERIFIER EXECUTES SANDBOX & PRODUCES ED25519 PROOF")
    res1 = verifier.verify_milestone_and_sign(
        vault_pda_str=vault_pda,
        milestone_idx=0,
        agent_wallet_str=agent_wallet,
        code_source_path=m1_submission,
        private_test_path=m1_test,
        expected_spec_hash_bytes=m1_spec_hash,
        tranche_amount=amounts[0],
        expires_at=expires_at,
        nonce=1001,
        acceptance_criteria=[
            "Returns exactly n elements",
            "Elements ordered by frequency descending"
        ]
    )
    assert res1["verified"] is True
    print(f"  {GREEN}[OK]{RESET} Verifier Status: {res1['status']}")
    print(f"  Ed25519 Signature: {res1['signature_hex'][:24]}...")

    # Step 5: Onchain Solana verifies proof and releases $50
    print_step(5, "SOLANA VERIFIES ED25519 PROOF & DISBURSES TRANCHE 0 ($50.00 TLUSD)")
    tx_res1 = sim.release_tranche(
        milestone_idx=0,
        submission_hash=res1["submission_hash_bytes"],
        nonce=1001,
        signature=res1["signature_bytes"],
    )
    print(f"  {GREEN}[OK]{RESET} Transaction Confirmed!")
    print(f"  Released Amount:  {BOLD}+${tx_res1['amount_released'] / 1e6:.2f} TLUSD{RESET} -> Agent")
    print(f"  Vault Remaining:  ${tx_res1['vault_remaining'] / 1e6:.2f} TLUSD")
    print(f"  Agent Balance:    {BOLD}${tx_res1['agent_total'] / 1e6:.2f} TLUSD{RESET}")
    print(f"  Current Milestone:{sim.state.current_tranche} of {sim.state.total_tranches}")

    # Step 6: Agent submits flawed Milestone 2
    print_step(6, "AGENT SUBMITS FLAWED MILESTONE 2 (m2_broken.py)")
    m2_broken = fixtures_dir / "agent_submissions" / "m2_broken.py"
    print(f"  Target File: {m2_broken} (contains negative n bug)")

    # Step 7 & 8: Verifier rejects -> $0 released
    print_step(7, "VERIFIER DETECTS TEST FAILURES // ZERO FUNDS AUTHORIZED")
    res2 = verifier.verify_milestone_and_sign(
        vault_pda_str=vault_pda,
        milestone_idx=1,
        agent_wallet_str=agent_wallet,
        code_source_path=m2_broken,
        private_test_path=m2_test,
        expected_spec_hash_bytes=m2_spec_hash,
        tranche_amount=amounts[1],
        expires_at=expires_at,
        nonce=1002,
        acceptance_criteria=[
            "Returns [] when n<=0",
            "Returns [] when items is empty",
            "Returns all unique elements when n > unique elements"
        ]
    )
    assert res2["verified"] is False
    assert res2["signature"] is None
    print(f"  {RED}[FAILED]{RESET} Verifier Status: {res2['status']}")
    print(f"  {RED}[SECURITY]{RESET} Signature is NONE. Zero funds can leave the vault.")
    print(f"  Vault Remaining:  ${sim.state.vault_balance / 1e6:.2f} TLUSD (UNTOUCHED)")
    print(f"  Agent Balance:    ${sim.state.agent_balance / 1e6:.2f} TLUSD (UNCHANGED)")
    print(f"  Diagnostic Feedback returned to Agent: {res2['reasoning']}")

    # Step 9: Agent fixes code
    print_step(9, "AGENT RECEIVES DIAGNOSTIC & FIXES CODE (m2_fixed.py)")
    m2_fixed = fixtures_dir / "agent_submissions" / "m2_fixed.py"
    print(f"  Target File: {m2_fixed} (guards added for n<=0 and empty lists)")

    # Step 10: Verifier tests pass & signs proof
    print_step(10, "VERIFIER RE-EVALUATES PATCHED CODE // ALL TESTS GREEN")
    res3 = verifier.verify_milestone_and_sign(
        vault_pda_str=vault_pda,
        milestone_idx=1,
        agent_wallet_str=agent_wallet,
        code_source_path=m2_fixed,
        private_test_path=m2_test,
        expected_spec_hash_bytes=m2_spec_hash,
        tranche_amount=amounts[1],
        expires_at=expires_at,
        nonce=1003,
        acceptance_criteria=[
            "Returns [] when n<=0",
            "Returns [] when items is empty",
            "Returns all unique elements when n > unique elements"
        ]
    )
    assert res3["verified"] is True
    assert res3["signature_bytes"] is not None
    print(f"  {GREEN}[OK]{RESET} Verifier Status: {res3['status']}")
    print(f"  Ed25519 Signature: {res3['signature_hex'][:24]}...")

    # Step 11 & 12: Final release and completion
    print_step(11, "SOLANA RELEASES FINAL TRANCHE 1 ($50.00 TLUSD)")
    tx_res2 = sim.release_tranche(
        milestone_idx=1,
        submission_hash=res3["submission_hash_bytes"],
        nonce=1003,
        signature=res3["signature_bytes"],
    )
    print(f"  {GREEN}[OK]{RESET} Transaction Confirmed!")
    print(f"  Released Amount:  {BOLD}+${tx_res2['amount_released'] / 1e6:.2f} TLUSD{RESET} -> Agent")
    print(f"  Vault Remaining:  ${tx_res2['vault_remaining'] / 1e6:.2f} TLUSD")
    print(f"  Agent Final Total:{BOLD}${tx_res2['agent_total'] / 1e6:.2f} TLUSD{RESET}")

    print_step(12, "VAULT REACHES FINAL ONCHAIN STATE: COMPLETED")
    assert tx_res2["is_completed"] is True
    assert sim.state.vault_balance == 0
    assert sim.state.tranche_status == [1, 1]

    print_banner("DEMO FINISHED SUCCESSFULLY: ALL 12 STEPS VERIFIED & REPRODUCIBLE")


if __name__ == "__main__":
    run_full_demo()
