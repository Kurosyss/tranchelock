import { Connection, PublicKey } from "@solana/web3.js";
import * as anchor from "@coral-xyz/anchor";
import idl from "../../target/idl/tranchelock.json";

export const PROGRAM_ID = new PublicKey("3SBmcsZqGHbLzxrBR2ZzrfSnufHFpzM6GHY6TiijebtM");
export const DEVNET_RPC_URL = "https://api.devnet.solana.com";

export interface OnchainMilestone {
  index: number;
  title: string;
  amount: string;
  amountBaseUnits: number;
  status: "VERIFIED & SETTLED" | "REFUNDED (CLAWBACK)" | "LOCKED";
  badgeVariant: "pass" | "fail" | "neutral";
  specHash: string;
  submissionHash?: string;
  proofId?: string;
  signature?: string;
  txSignature?: string;
}

export interface OnchainVaultRecord {
  id: string;
  sponsor: string;
  agent: string;
  oracle: string;
  mint: string;
  mintSymbol: string;
  totalAmount: string;
  totalAmountNum: number;
  releasedAmount: string;
  releasedAmountNum: number;
  remainingAmount: string;
  remainingAmountNum: number;
  lockedPct: string;
  releasedPct: string;
  status: "COMPLETED" | "ACTIVE" | "REFUNDED";
  badgeVariant: "pass" | "neutral" | "fail";
  expiresAt: string;
  expiresAtTimestamp: number;
  bump: number;
  vaultBump: number;
  currentTranche: number;
  totalTranches: number;
  tranchesReleased: number;
  tranchesTotal: number;
  token: string;
  timeAgo: string;
  milestoneName: string;
  initTx?: string;
  clawbackTx?: string;
  milestones: OnchainMilestone[];
}

// Canonical onchain Devnet vaults produced by deployment, vertical slice, and security suites
export const KNOWN_DEVNET_VAULTS: OnchainVaultRecord[] = [
  {
    id: "GbkWd144roWeT7uE1KxEJVQ2Wvk3ZV84vLp6hUii6Kno",
    sponsor: "9cxHstyCEHRAazJJuL3FrpMH6LJsKSPLP5Vouo4yWYwV",
    agent: "3a5rCTRmQ9B74GnietwFSfqKJirEHjqZdEaCMQeSnksP",
    oracle: "HyiP6tqPGE9wX6oBNPeS8eBhhsEpKar4VzQphRWVGf5W",
    mint: "7oKiSro2j98G3NigDYzb6EfisnnAxhg3DTTio6yf6xjW",
    mintSymbol: "TLUSD",
    totalAmount: "$100.00",
    totalAmountNum: 100,
    releasedAmount: "$100.00",
    releasedAmountNum: 100,
    remainingAmount: "$0.00",
    remainingAmountNum: 0,
    lockedPct: "0%",
    releasedPct: "100%",
    status: "COMPLETED",
    badgeVariant: "pass",
    expiresAt: "2026-09-20 10:18:53 UTC",
    expiresAtTimestamp: 1789985933,
    bump: 254,
    vaultBump: 255,
    currentTranche: 2,
    totalTranches: 2,
    timeAgo: "Live Vertical Slice",
    milestoneName: "Top-K Frequency Algorithm & Edge-Case Protection",
    initTx: "593zXLeLpX7mV21iHS5DgvMH45CKyyFGWNgPLUwSuduwo9b8oFXEvCQb6EhM43Xrvb7YGgNB5FNVapXCX12LbDFJ",
    milestones: [
      {
        index: 0,
        title: "Milestone 01: Core Frequency Top-K Parser",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "VERIFIED & SETTLED",
        badgeVariant: "pass",
        specHash: "599965850c0c655d49e6f3df3e48eb2292f763dbd769c362973d404e5414ab2b",
        submissionHash: "49bf07f8d8bfe3e46c7ad168c4cf33e9ec49bca0f07fae4b953d34ea9efb8ef1",
        proofId: "proof-m1-49bf07f8",
        signature: "84725d2b78d2b7579124be30357ea1b5a2bf2a4208e923b72c41c7b5fa3245bb16e133d9f2dfb1f73602187f872c0ca267794025ad51c5f3b7d188701eec950a",
        txSignature: "3zUnyYkd8xLySWti5jhZL9xhw6yqx1U6gTHB1bXaPBcnAWvVGFxsoQ3t4C6Ap39Msx6c6NyDsBn23Apati9Zq8bM",
      },
      {
        index: 1,
        title: "Milestone 02: Edge-Case Immunity & Negative N Guards",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "VERIFIED & SETTLED",
        badgeVariant: "pass",
        specHash: "5845f1cf81751c1c1f061fbb98ea75c401aa99c836ec2ce963c6cf7b02db16db",
        submissionHash: "3c8d0a8a3a291f03ce3e08f23fcfb648fa3910c22fa3dc9027878d6faae7c6ae",
        proofId: "proof-m2-3c8d0a8a",
        signature: "ca07843d04768ea9c81938b8160472e3895e634cb38d4517036a18d17961205307525381ce5b2110e0513e4bfa95e4e83c74384d505165d496a77d29fc2f5509",
        txSignature: "HqSU1zEPg4tSQDQHNAWaKm11DoqdyeYBkNC9Yk6MPtVwTsNU1TaosoRr1ocnxSpCCJVxnudfNUVdGcHbg4wBXrg",
      },
    ],
  },
  {
    id: "HJiemexnyXfLZyyJZFPRg2j9aMvfoR3igriekLuKR5sY",
    sponsor: "9cxHstyCEHRAazJJuL3FrpMH6LJsKSPLP5Vouo4yWYwV",
    agent: "Dp8F2NcgHRTVneQ8KMypBXNUTmBJwR1EkQwoPnidsApQ",
    oracle: "9xczJCg66CWUw4gKczasRNwUkKpRDGigHeBqsDXZtUWp",
    mint: "BiaT2pWXRMx1eaUBujDt1sJ5PvE3CjdE3Y6GLbhZNvG7",
    mintSymbol: "TLUSD",
    totalAmount: "$100.00",
    totalAmountNum: 100,
    releasedAmount: "$100.00",
    releasedAmountNum: 100,
    remainingAmount: "$0.00",
    remainingAmountNum: 0,
    lockedPct: "0%",
    releasedPct: "100%",
    status: "COMPLETED",
    badgeVariant: "pass",
    expiresAt: "2026-09-20 12:21:35 UTC",
    expiresAtTimestamp: 1789993295,
    bump: 254,
    vaultBump: 255,
    currentTranche: 2,
    totalTranches: 2,
    timeAgo: "Live Invariant Audit",
    milestoneName: "Adversarial Invariant Security Suite Verification",
    initTx: "a4uG4HajWZJEQzUECs65M5u2zkKYpajm3fsXR4EEaRjdGgTASt2BT4esCajNQdixjNVK6Y4WAtoeZ9Jnpw7FkBj",
    milestones: [
      {
        index: 0,
        title: "Milestone 01: Core Security Settlement",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "VERIFIED & SETTLED",
        badgeVariant: "pass",
        specHash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        txSignature: "5kV9SeygdaJfgF9zWdYNukFJ4BHs5wTkQsRsmvNxZP1fzPwjdK4GZrben9ZyyGsKJLVKzho2gv3DqnZcLZ21y8Ae",
      },
      {
        index: 1,
        title: "Milestone 02: Full Lifecycle Final Settlement",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "VERIFIED & SETTLED",
        badgeVariant: "pass",
        specHash: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        txSignature: "VVNcVTEhz89BDCkW5cDmjLTCkHkoDsBuT2kdLjnXVRegmVRPMTmb4oKrM3bUWbAwu4zyMUu5WUySprQPvvZLUDt",
      },
    ],
  },
  {
    id: "2hFQURPDkj8ArChh2MDDaqbmTWHnHzupqwU7h42D2iaj",
    sponsor: "9cxHstyCEHRAazJJuL3FrpMH6LJsKSPLP5Vouo4yWYwV",
    agent: "Dp8F2NcgHRTVneQ8KMypBXNUTmBJwR1EkQwoPnidsApQ",
    oracle: "9xczJCg66CWUw4gKczasRNwUkKpRDGigHeBqsDXZtUWp",
    mint: "C3wQS7py8UJ7Chn9RErteLEAurtDdQuXTQHhYzjxeSVk",
    mintSymbol: "TLUSD",
    totalAmount: "$100.00",
    totalAmountNum: 100,
    releasedAmount: "$50.00",
    releasedAmountNum: 50,
    remainingAmount: "$0.00",
    remainingAmountNum: 0,
    lockedPct: "0%",
    releasedPct: "50%",
    status: "REFUNDED",
    badgeVariant: "neutral",
    expiresAt: "2026-09-19 12:21:27 UTC (Expired)",
    expiresAtTimestamp: 1789906887,
    bump: 254,
    vaultBump: 255,
    currentTranche: 1,
    totalTranches: 2,
    timeAgo: "Live Timelock Audit",
    milestoneName: "Timelock Clawback Lifecycle & Refund Protection",
    initTx: "4KemauuHewEq7iVGPYzTGFqbe2iQdBEMTEAmSFU5NW4GMfKi7C3koBkJHJzAZeyjhQ7cem8JMz4KGLRxE2Bq7Rb8",
    clawbackTx: "5dtJWT2ge7Trv2m7mo1NBhoaub1gaHeEo4u7oDoRwUw4EavBJ5vjKAMmCvNZ76in1oZmYqNrXfcBLwXToS53ZQz5",
    milestones: [
      {
        index: 0,
        title: "Milestone 01: Pre-Expiry Completed Work",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "VERIFIED & SETTLED",
        badgeVariant: "pass",
        specHash: "1111111111111111111111111111111111111111111111111111111111111111",
        txSignature: "3VR2xihTZRkRPQ2umwQzet97SnjYyv4o4VY4oXmn6hHapnjxHMjeey1AeBHcjtvV2PAfzRCVprLTgSec9dgh3cz6",
      },
      {
        index: 1,
        title: "Milestone 02: Unreleased Tranche (Clawed Back by Sponsor)",
        amount: "$50.00",
        amountBaseUnits: 50_000_000,
        status: "REFUNDED (CLAWBACK)",
        badgeVariant: "neutral",
        specHash: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
  },
  {
    id: "8g2XngoERjPxxidj4Y77fZUBD9D75ozfPwYsPXKHYqK9",
    sponsor: "9cxHstyCEHRAazJJuL3FrpMH6LJsKSPLP5Vouo4yWYwV",
    agent: "C9Xvz1Kbi2LnHT419qBPHejfF1D7SP49HGGCwUiY3Mg6",
    oracle: "HyiP6tqPGE9wX6oBNPeS8eBhhsEpKar4VzQphRWVGf5W",
    mint: "BSjnNyWYh4j5MbeiNfGjTFQLeyvdEqTcn1G4rfFYHVB3",
    mintSymbol: "TLUSD",
    totalAmount: "$100.00",
    totalAmountNum: 100,
    releasedAmount: "$0.00",
    releasedAmountNum: 0,
    remainingAmount: "$100.00",
    remainingAmountNum: 100,
    lockedPct: "100%",
    releasedPct: "0%",
    status: "ACTIVE",
    badgeVariant: "neutral",
    expiresAt: "2026-09-20 18:00:00 UTC",
    expiresAtTimestamp: 1790013600,
    bump: 254,
    vaultBump: 255,
    currentTranche: 0,
    totalTranches: 2,
    timeAgo: "Active Onchain Escrow",
    milestoneName: "Distributed Consensus Event Loop Verification",
    milestones: [
      {
        index: 0,
        title: "Milestone 01: Core Ingestion Protocol",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "LOCKED",
        badgeVariant: "neutral",
        specHash: "11aa22bb33cc44dd55ee66ff77aa88bb99cc00dd11ee22ff33aa44bb55cc66dd",
      },
      {
        index: 1,
        title: "Milestone 02: Resilient State Replication",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "LOCKED",
        badgeVariant: "neutral",
        specHash: "22bb33cc44dd55ee66ff77aa88bb99cc00dd11ee22ff33aa44bb55cc66dd77ee",
      },
    ],
  },
  {
    id: "DXjEQb34RxdJRotsTMRYGBn5b957iSb78v33c68wCtqy",
    sponsor: "9cxHstyCEHRAazJJuL3FrpMH6LJsKSPLP5Vouo4yWYwV",
    agent: "FLZgZ2qtVVo3roGSXKG8AYaLC7wK8EdofhHWMiyuGrLK",
    oracle: "HyiP6tqPGE9wX6oBNPeS8eBhhsEpKar4VzQphRWVGf5W",
    mint: "FQ13YHkhBNNbee6qauAt6G4Z4fdHqJ1K4n53uXVfRB9m",
    mintSymbol: "TLUSD",
    totalAmount: "$100.00",
    totalAmountNum: 100,
    releasedAmount: "$0.00",
    releasedAmountNum: 0,
    remainingAmount: "$100.00",
    remainingAmountNum: 100,
    lockedPct: "100%",
    releasedPct: "0%",
    status: "ACTIVE",
    badgeVariant: "neutral",
    expiresAt: "2026-09-20 18:00:00 UTC",
    expiresAtTimestamp: 1790013600,
    bump: 254,
    vaultBump: 255,
    currentTranche: 0,
    totalTranches: 2,
    timeAgo: "Active Onchain Escrow",
    milestoneName: "Memory Safe Concurrency Harness",
    milestones: [
      {
        index: 0,
        title: "Milestone 01: Leak-Free Allocator Architecture",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "LOCKED",
        badgeVariant: "neutral",
        specHash: "33cc44dd55ee66ff77aa88bb99cc00dd11ee22ff33aa44bb55cc66dd77ee88ff",
      },
      {
        index: 1,
        title: "Milestone 02: High-Pressure Soak Validation",
        amount: "+$50.00",
        amountBaseUnits: 50_000_000,
        status: "LOCKED",
        badgeVariant: "neutral",
        specHash: "44dd55ee66ff77aa88bb99cc00dd11ee22ff33aa44bb55cc66dd77ee88ff99aa",
      },
    ],
  },
].map((v) => ({
  ...v,
  tranchesReleased: v.currentTranche,
  tranchesTotal: v.totalTranches,
  token: v.mintSymbol,
})) as OnchainVaultRecord[];

export interface ProtocolMetrics {
  tvl: string;
  capitalSettled: string;
  activeEscrows: number;
  completedEscrows: number;
  verifiedTranches: number;
  settlementToken: string;
  tokenMint: string;
}

export function getProtocolMetrics(vaults: OnchainVaultRecord[] = KNOWN_DEVNET_VAULTS): ProtocolMetrics {
  let tvlTotal = 0;
  let settledTotal = 0;
  let activeCount = 0;
  let completedCount = 0;
  let verifiedTranchesCount = 0;

  for (const v of vaults) {
    tvlTotal += v.totalAmountNum;
    settledTotal += v.releasedAmountNum;
    if (v.status === "ACTIVE") activeCount++;
    if (v.status === "COMPLETED") completedCount++;
    verifiedTranchesCount += v.currentTranche;
  }

  return {
    tvl: `$${tvlTotal.toFixed(2)}`,
    capitalSettled: `$${settledTotal.toFixed(2)}`,
    activeEscrows: activeCount,
    completedEscrows: completedCount,
    verifiedTranches: verifiedTranchesCount,
    settlementToken: "TLUSD",
    tokenMint: "7oKiSro2j98G3NigDYzb6EfisnnAxhg3DTTio6yf6xjW",
  };
}

export async function fetchLiveVaultAccount(pubkeyStr: string): Promise<any | null> {
  try {
    const conn = new Connection(DEVNET_RPC_URL, "confirmed");
    const pubkey = new PublicKey(pubkeyStr);
    const acc = await conn.getAccountInfo(pubkey);
    if (!acc) return null;
    const coder = new anchor.BorshAccountsCoder(idl as any);
    return coder.decode("TrancheVault", acc.data);
  } catch (err) {
    console.error("Failed to fetch live vault account:", err);
    return null;
  }
}
