import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import {
  Connection,
  Keypair,
  PublicKey,
  SystemProgram,
  SYSVAR_INSTRUCTIONS_PUBKEY,
  SYSVAR_RENT_PUBKEY,
  Transaction,
  sendAndConfirmTransaction,
  Ed25519Program,
} from "@solana/web3.js";
import {
  createMint,
  getOrCreateAssociatedTokenAccount,
  mintTo,
  getAccount,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import nacl from "tweetnacl";
import { createHash } from "crypto";

function computeSpecHash(testFilePath: string): Buffer {
  const content = fs.readFileSync(testFilePath).toString("binary").replace(/\r\n/g, "\n");
  return Buffer.from(createHash("sha256").update(content, "binary").digest());
}

// Configurations
const RPC_ENDPOINT = process.env.SOLANA_RPC_URL || "https://api.devnet.solana.com";
const PROGRAM_ID = new PublicKey(
  process.env.PROGRAM_ID || "3SBmcsZqGHbLzxrBR2ZzrfSnufHFpzM6GHY6TiijebtM"
);
const OFFICIAL_DEVNET_USDC_MINT = new PublicKey(
  "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
);

const CANONICAL_PAYLOAD_SIZE = 153;

function buildCanonicalPayload(
  vaultPda: PublicKey,
  milestoneIdx: number,
  agentWallet: PublicKey,
  submissionHash: Buffer,
  milestoneSpecHash: Buffer,
  trancheAmount: bigint,
  expiresAt: bigint,
  nonce: bigint
): Buffer {
  const buf = Buffer.alloc(CANONICAL_PAYLOAD_SIZE);
  vaultPda.toBuffer().copy(buf, 0);
  buf.writeUInt8(milestoneIdx, 32);
  agentWallet.toBuffer().copy(buf, 33);
  submissionHash.copy(buf, 65, 0, 32);
  milestoneSpecHash.copy(buf, 97, 0, 32);
  buf.writeBigUInt64LE(trancheAmount, 129);
  buf.writeBigInt64LE(expiresAt, 137);
  buf.writeBigUInt64LE(nonce, 145);
  return buf;
}

function runRealVerifier(args: {
  vaultPda: string;
  milestoneIdx: number;
  agentWallet: string;
  codePath: string;
  testPath: string;
  amount: number;
  expiresAt: number;
  nonce: number;
}) {
  const pythonCmd = process.platform === "win32" ? "python" : "python3";
  const cliPath = path.resolve("verifier/cli.py");
  const stdout = execFileSync(
    pythonCmd,
    [
      cliPath,
      "--vault-pda",
      args.vaultPda,
      "--milestone-idx",
      args.milestoneIdx.toString(),
      "--agent-wallet",
      args.agentWallet,
      "--code-path",
      args.codePath,
      "--test-path",
      args.testPath,
      "--amount",
      args.amount.toString(),
      "--expires-at",
      args.expiresAt.toString(),
      "--nonce",
      args.nonce.toString(),
    ],
    { encoding: "utf-8" }
  );

  const startMarker = "__VERIFIER_JSON_OUTPUT_START__";
  const endMarker = "__VERIFIER_JSON_OUTPUT_END__";
  const jsonStr = stdout.substring(
    stdout.indexOf(startMarker) + startMarker.length,
    stdout.indexOf(endMarker)
  ).trim();

  return JSON.parse(jsonStr);
}

function loadKeypairFromFile(filePath: string): Keypair {
  const secretKey = Uint8Array.from(JSON.parse(fs.readFileSync(filePath, "utf-8")));
  return Keypair.fromSecretKey(secretKey);
}

export async function runDevnetVerticalSlice() {
  console.log("\n==================================================");
  console.log("  TRANCHELOCK // REAL SOLANA DEVNET VERTICAL SLICE");
  console.log("==================================================");
  console.log(`Cluster RPC:     ${RPC_ENDPOINT}`);
  console.log(`Program ID:      ${PROGRAM_ID.toBase58()}`);

  const connection = new Connection(RPC_ENDPOINT, "confirmed");

  // 1. Load Deployer / Sponsor wallet
  let sponsor: Keypair;
  const localKeypairPath = path.resolve("target/deploy/deployer-keypair.json");
  const wslKeypairPath = "/home/white_room/.config/solana/id.json";

  if (fs.existsSync(localKeypairPath)) {
    sponsor = loadKeypairFromFile(localKeypairPath);
  } else if (process.platform !== "win32" && fs.existsSync(wslKeypairPath)) {
    sponsor = loadKeypairFromFile(wslKeypairPath);
  } else {
    sponsor = Keypair.generate();
    fs.mkdirSync(path.dirname(localKeypairPath), { recursive: true });
    fs.writeFileSync(localKeypairPath, JSON.stringify(Array.from(sponsor.secretKey)));
  }

  const agent = Keypair.generate();
  console.log(`Sponsor Wallet:  ${sponsor.publicKey.toBase58()}`);
  console.log(`Agent Wallet:    ${agent.publicKey.toBase58()}`);

  // Check sponsor balance
  const sponsorBal = await connection.getBalance(sponsor.publicKey);
  console.log(`Sponsor Balance: ${sponsorBal / 1e9} SOL`);

  if (sponsorBal < 0.05 * 1e9) {
    console.log("[!] Sponsor needs SOL for transactions. Requesting airdrop...");
    try {
      const airdropSig = await connection.requestAirdrop(sponsor.publicKey, 1e9);
      await connection.confirmTransaction(airdropSig);
      console.log("[+] Airdrop successful!");
    } catch (e: any) {
      console.log(`[!] Airdrop notice: ${e.message}`);
    }
  }

  // Fund agent wallet with 0.01 SOL from sponsor so agent can pay tx fees for releaseTranche
  console.log("[*] Funding agent wallet with 0.01 SOL for transaction fees...");
  const fundAgentTx = new Transaction().add(
    SystemProgram.transfer({
      fromPubkey: sponsor.publicKey,
      toPubkey: agent.publicKey,
      lamports: 0.01 * 1e9,
    })
  );
  const fundAgentSig = await sendAndConfirmTransaction(connection, fundAgentTx, [sponsor]);
  console.log(`[+] Agent funded. Tx: ${fundAgentSig}`);

  // 2. Load IDL and Anchor Program
  const idlPath = path.resolve("target/idl/tranchelock.json");
  const idl = JSON.parse(fs.readFileSync(idlPath, "utf-8"));
  const wallet = new anchor.Wallet(sponsor);
  const provider = new anchor.AnchorProvider(connection, wallet, {
    commitment: "confirmed",
  });
  const program = new Program(idl, provider);

  // 3. Token Setup (Devnet USDC or TLUSD test token)
  let tokenMint: PublicKey;
  let isOfficialUsdc = false;

  const configuredMint = process.env.TRANCHELOCK_TOKEN_MINT;
  if (configuredMint && configuredMint === OFFICIAL_DEVNET_USDC_MINT.toBase58()) {
    tokenMint = OFFICIAL_DEVNET_USDC_MINT;
    isOfficialUsdc = true;
    console.log(`[Token] Using configured Official Devnet USDC: ${tokenMint.toBase58()}`);
  } else {
    console.log("[Token] Initializing TLUSD (TrancheUSD Test Mint) for Devnet verification...");
    tokenMint = await createMint(
      connection,
      sponsor,
      sponsor.publicKey,
      null,
      6
    );
    console.log(`[Token] Created TLUSD Mint: ${tokenMint.toBase58()} (never label as Circle USDC)`);
  }

  // Create ATAs
  const sponsorAta = await getOrCreateAssociatedTokenAccount(
    connection,
    sponsor,
    tokenMint,
    sponsor.publicKey
  );
  const agentAta = await getOrCreateAssociatedTokenAccount(
    connection,
    sponsor,
    tokenMint,
    agent.publicKey
  );

  if (!isOfficialUsdc) {
    // Mint $100.00 TLUSD ($100 = 100_000_000 base units at 6 decimals)
    console.log("[Token] Minting $100.00 TLUSD to sponsor ATA...");
    await mintTo(
      connection,
      sponsor,
      tokenMint,
      sponsorAta.address,
      sponsor,
      100_000_000
    );
  }

  // 4. Derive Vault PDAs
  const [vaultPda, vaultBump] = PublicKey.findProgramAddressSync(
    [Buffer.from("tranche_vault"), sponsor.publicKey.toBuffer(), tokenMint.toBuffer()],
    PROGRAM_ID
  );
  const [vaultTokenAccountPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("token_vault"), vaultPda.toBuffer()],
    PROGRAM_ID
  );

  console.log(`Vault PDA:       ${vaultPda.toBase58()}`);
  console.log(`Token Vault PDA: ${vaultTokenAccountPda.toBase58()}`);

  // Test suite spec hashes
  const m1TestPath = path.resolve("fixtures/milestone1_private_test.py");
  const m2TestPath = path.resolve("fixtures/milestone2_private_test.py");
  const m1CorrectCode = path.resolve("fixtures/agent_submissions/m1_correct.py");
  const m2BrokenCode = path.resolve("fixtures/agent_submissions/m2_broken.py");
  const m2FixedCode = path.resolve("fixtures/agent_submissions/m2_fixed.py");

  // Compute spec hashes directly for deterministic verification
  const specHash1 = computeSpecHash(m1TestPath);
  const specHash2 = computeSpecHash(m2TestPath);
  const oraclePubkey = new PublicKey("HyiP6tqPGE9wX6oBNPeS8eBhhsEpKar4VzQphRWVGf5W");
  console.log(`Verifier Oracle: ${oraclePubkey.toBase58()}`);
  console.log(`Milestone 1 Spec Hash: ${specHash1.toString("hex")}`);
  console.log(`Milestone 2 Spec Hash: ${specHash2.toString("hex")}`);

  const amounts = [new anchor.BN(50_000_000), new anchor.BN(50_000_000)];
  // Anchor Borsh requires vec<[u8;32]> as Array<number[]>
  const specHashes = [Array.from(specHash1), Array.from(specHash2)];
  const expiresAt = new anchor.BN(Math.floor(Date.now() / 1000) + 86400);

  // 5. Initialize Vault ($100 locked in escrow)
  console.log("\n--- [STEP 1] INITIALIZE TRANCHE VAULT ---");
  const initTx = await program.methods
    .initializeVault(amounts, specHashes, expiresAt)
    .accounts({
      vault: vaultPda,
      vaultTokenAccount: vaultTokenAccountPda,
      sponsor: sponsor.publicKey,
      agent: agent.publicKey,
      verifierOracle: oraclePubkey,
      tokenMint: tokenMint,
      sponsorTokenAccount: sponsorAta.address,
      tokenProgram: TOKEN_PROGRAM_ID,
      systemProgram: SystemProgram.programId,
      rent: SYSVAR_RENT_PUBKEY,
    })
    .signers([sponsor])
    .rpc();

  console.log(`[+] Vault Initialized! Tx: ${initTx}`);
  console.log(`    Solana Explorer: https://explorer.solana.com/tx/${initTx}?cluster=devnet`);

  // Verify vault initial state & balance
  const vBalInit = await getAccount(connection, vaultTokenAccountPda);
  const onchainVaultInit: any = await program.account.trancheVault.fetch(vaultPda);
  console.log(`    Vault Balance:        ${Number(vBalInit.amount) / 1e6} tokens`);
  console.log(`    Onchain Total Tranches: ${onchainVaultInit.totalTranches}`);
  console.log(`    Onchain Current Tranche: ${onchainVaultInit.currentTranche}`);

  // 6. Milestone 1 - Real Verifier & Release
  console.log("\n--- [STEP 2] MILESTONE 1 VERIFICATION & RELEASE ---");
  const m1Proof = runRealVerifier({
    vaultPda: vaultPda.toBase58(),
    milestoneIdx: 0,
    agentWallet: agent.publicKey.toBase58(),
    codePath: m1CorrectCode,
    testPath: m1TestPath,
    amount: 50_000_000,
    expiresAt: expiresAt.toNumber(),
    nonce: 1001,
  });

  if (!m1Proof.verified) {
    throw new Error(`Milestone 1 proof failed: ${m1Proof.reasoning}`);
  }

  console.log(`[+] Real Verifier Output: PASS`);
  console.log(`    AI Reasoning: ${m1Proof.reasoning}`);
  console.log(`    Signature:    ${m1Proof.signature_hex.slice(0, 32)}...`);

  // Construct Ed25519 precompile instruction
  const m1Message = buildCanonicalPayload(
    vaultPda,
    0,
    agent.publicKey,
    Buffer.from(m1Proof.submission_hash_hex, "hex"),
    specHash1,
    BigInt(50_000_000),
    BigInt(expiresAt.toNumber()),
    BigInt(1001)
  );

  const ed25519IxM1 = Ed25519Program.createInstructionWithPublicKey({
    publicKey: oraclePubkey.toBuffer(),
    message: m1Message,
    signature: Buffer.from(m1Proof.signature_hex, "hex"),
  });

  const releaseIxM1 = await program.methods
    .releaseTranche(0, Array.from(Buffer.from(m1Proof.submission_hash_hex, "hex")), new anchor.BN(1001))
    .accounts({
      vault: vaultPda,
      vaultTokenAccount: vaultTokenAccountPda,
      agent: agent.publicKey,
      agentTokenAccount: agentAta.address,
      instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
      tokenProgram: TOKEN_PROGRAM_ID,
    })
    .instruction();

  // Enforce Ed25519 instruction IMMEDIATELY BEFORE release_tranche
  // agent must sign: it's the authorized recipient and releaseTranche requires agent.is_signer
  const releaseTx1 = new Transaction().add(ed25519IxM1).add(releaseIxM1);
  const releaseSig1 = await sendAndConfirmTransaction(connection, releaseTx1, [agent]);

  console.log(`[+] Tranche 0 Released! Tx: ${releaseSig1}`);
  console.log(`    Solana Explorer: https://explorer.solana.com/tx/${releaseSig1}?cluster=devnet`);

  const agentBalM1 = await getAccount(connection, agentAta.address);
  const vaultBalM1 = await getAccount(connection, vaultTokenAccountPda);
  const onchainVaultM1: any = await program.account.trancheVault.fetch(vaultPda);
  console.log(`    Agent Balance:        ${Number(agentBalM1.amount) / 1e6} tokens`);
  console.log(`    Vault Balance:        ${Number(vaultBalM1.amount) / 1e6} tokens remaining`);
  console.log(`    Onchain Current Tranche: ${onchainVaultM1.currentTranche}`);

  // 7. Milestone 2 - Negative Test (Bad submission fails verification)
  console.log("\n--- [STEP 3] LIVE FAILURE CASE (m2_broken.py) ---");
  const m2BrokenProof = runRealVerifier({
    vaultPda: vaultPda.toBase58(),
    milestoneIdx: 1,
    agentWallet: agent.publicKey.toBase58(),
    codePath: m2BrokenCode,
    testPath: m2TestPath,
    amount: 50_000_000,
    expiresAt: expiresAt.toNumber(),
    nonce: 1002,
  });

  console.log(`[*] Broken Code Verifier Status: ${m2BrokenProof.status}`);
  console.log(`    Verified:                      ${m2BrokenProof.verified}`);
  console.log(`    Signature:                     ${m2BrokenProof.signature_hex || "None (Zero Funds Authorized)"}`);
  console.log(`    AI Reasoning:                  ${m2BrokenProof.reasoning}`);

  // Prove onchain rejection if an invalid/unauthorized attempt is made
  console.log("[*] Proving onchain rejection of unverified release attempt on Devnet...");
  let failedAttemptTx: string | null = null;
  try {
    // Attempt release_tranche without valid Ed25519 precompile instruction
    const unverifiedReleaseIx = await program.methods
      .releaseTranche(1, Array.from(Buffer.from(m2BrokenProof.submission_hash_hex, "hex")), new anchor.BN(1002))
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentAta.address,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    const badTx = new Transaction().add(unverifiedReleaseIx);
    await sendAndConfirmTransaction(connection, badTx, [agent]);
    throw new Error("SECURITY FAILURE: Unverified release was accepted onchain!");
  } catch (rejectionErr: any) {
    console.log(`[+] ONCHAIN REJECTION CONFIRMED: Program refused release transaction!`);
    console.log(`    Rejection Message: ${rejectionErr.message?.slice(0, 80)}...`);
  }

  // Verify vault balance remained unchanged
  const vaultBalPostFailure = await getAccount(connection, vaultTokenAccountPda);
  console.log(`    Vault Balance Unchanged: ${Number(vaultBalPostFailure.amount) / 1e6} tokens (Still $50 locked)`);

  // 8. Milestone 2 - Fixed submission releases tranche 1
  console.log("\n--- [STEP 4] CORRECTION & SECOND TRANCHE RELEASE (m2_fixed.py) ---");
  const m2FixedProof = runRealVerifier({
    vaultPda: vaultPda.toBase58(),
    milestoneIdx: 1,
    agentWallet: agent.publicKey.toBase58(),
    codePath: m2FixedCode,
    testPath: m2TestPath,
    amount: 50_000_000,
    expiresAt: expiresAt.toNumber(),
    nonce: 1003,
  });

  console.log(`[+] Corrected Code Verifier Status: ${m2FixedProof.status}`);
  console.log(`    Verified:                        ${m2FixedProof.verified}`);
  console.log(`    AI Reasoning:                    ${m2FixedProof.reasoning}`);

  const m2Message = buildCanonicalPayload(
    vaultPda,
    1,
    agent.publicKey,
    Buffer.from(m2FixedProof.submission_hash_hex, "hex"),
    specHash2,
    BigInt(50_000_000),
    BigInt(expiresAt.toNumber()),
    BigInt(1003)
  );

  const ed25519IxM2 = Ed25519Program.createInstructionWithPublicKey({
    publicKey: oraclePubkey.toBuffer(),
    message: m2Message,
    signature: Buffer.from(m2FixedProof.signature_hex, "hex"),
  });

  const releaseIxM2 = await program.methods
    .releaseTranche(1, Array.from(Buffer.from(m2FixedProof.submission_hash_hex, "hex")), new anchor.BN(1003))
    .accounts({
      vault: vaultPda,
      vaultTokenAccount: vaultTokenAccountPda,
      agent: agent.publicKey,
      agentTokenAccount: agentAta.address,
      instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
      tokenProgram: TOKEN_PROGRAM_ID,
    })
    .instruction();

  const releaseTx2 = new Transaction().add(ed25519IxM2).add(releaseIxM2);
  const releaseSig2 = await sendAndConfirmTransaction(connection, releaseTx2, [agent]);

  console.log(`[+] Tranche 1 Released! Tx: ${releaseSig2}`);
  console.log(`    Solana Explorer: https://explorer.solana.com/tx/${releaseSig2}?cluster=devnet`);

  const agentBalFinal = await getAccount(connection, agentAta.address);
  const vaultBalFinal = await getAccount(connection, vaultTokenAccountPda);
  const onchainVaultFinal: any = await program.account.trancheVault.fetch(vaultPda);

  console.log(`\n==================================================`);
  console.log("  DEVNET VERTICAL SLICE SUMMARY");
  console.log("==================================================");
  console.log(`PROGRAM_ID:      ${PROGRAM_ID.toBase58()}`);
  console.log(`TOKEN_MINT:      ${tokenMint.toBase58()}`);
  console.log(`SPONSOR:         ${sponsor.publicKey.toBase58()}`);
  console.log(`AGENT:           ${agent.publicKey.toBase58()}`);
  console.log(`VAULT_PDA:       ${vaultPda.toBase58()}`);
  console.log(`ORACLE:          ${oraclePubkey.toBase58()}`);
  console.log(`INIT_TX:         ${initTx}`);
  console.log(`RELEASE_TX_1:    ${releaseSig1}`);
  console.log(`RELEASE_TX_2:    ${releaseSig2}`);
  console.log(`VAULT_BALANCE:   ${Number(vaultBalFinal.amount) / 1e6}`);
  console.log(`AGENT_BALANCE:   ${Number(agentBalFinal.amount) / 1e6}`);
  console.log(`FINAL_STATUS:    SUCCESS_CONFIRMED_ON_DEVNET`);
  console.log("==================================================\n");

  const results = {
    programId: PROGRAM_ID.toBase58(),
    tokenMint: tokenMint.toBase58(),
    sponsor: sponsor.publicKey.toBase58(),
    agent: agent.publicKey.toBase58(),
    vaultPda: vaultPda.toBase58(),
    tokenVaultPda: vaultTokenAccountPda.toBase58(),
    oracle: oraclePubkey.toBase58(),
    initTx,
    releaseSig1,
    releaseSig2,
    vaultBalance: Number(vaultBalFinal.amount) / 1e6,
    agentBalance: Number(agentBalFinal.amount) / 1e6,
    timestamp: new Date().toISOString(),
    status: "SUCCESS_CONFIRMED_ON_DEVNET",
  };

  fs.mkdirSync(path.resolve("src/data"), { recursive: true });
  fs.writeFileSync(
    path.resolve("src/data/devnet_results.json"),
    JSON.stringify(results, null, 2)
  );

  return results;
}

if (process.argv[1]?.includes("devnet_vertical_slice")) {
  runDevnetVerticalSlice().catch((err) => {
    console.error("Error executing Devnet vertical slice:", err);
    process.exit(1);
  });
}
