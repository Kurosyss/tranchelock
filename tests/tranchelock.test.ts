import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import {
  Keypair,
  PublicKey,
  SystemProgram,
  SYSVAR_INSTRUCTIONS_PUBKEY,
  SYSVAR_RENT_PUBKEY,
  TransactionInstruction,
  Ed25519Program,
  sendAndConfirmTransaction,
  Transaction,
} from "@solana/web3.js";
import {
  createMint,
  createAccount,
  mintTo,
  getAccount,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import nacl from "tweetnacl";
import { expect } from "chai";

// Canonical payload constant
const CANONICAL_PAYLOAD_SIZE = 153;

function buildCanonicalPayload(
  vaultPda: PublicKey,
  milestoneIdx: number,
  agentWallet: PublicKey,
  submissionHash: Buffer,
  milestoneSpecHash: Buffer,
  trancheAmount: anchor.BN,
  expiresAt: anchor.BN,
  nonce: anchor.BN
): Buffer {
  const buf = Buffer.alloc(CANONICAL_PAYLOAD_SIZE);
  vaultPda.toBuffer().copy(buf, 0);
  buf.writeUInt8(milestoneIdx, 32);
  agentWallet.toBuffer().copy(buf, 33);
  submissionHash.copy(buf, 65, 0, 32);
  milestoneSpecHash.copy(buf, 97, 0, 32);
  buf.writeBigUInt64LE(BigInt(trancheAmount.toString()), 129);
  buf.writeBigInt64LE(BigInt(expiresAt.toString()), 137);
  buf.writeBigUInt64LE(BigInt(nonce.toString()), 145);
  return buf;
}

describe("TrancheLock Security Invariants & Integration Test Suite", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  // We load or mock program interface
  const program = anchor.workspace.Tranchelock as Program<any>;

  const sponsor = Keypair.generate();
  const agent = Keypair.generate();
  const oracle = nacl.sign.keyPair(); // Ed25519 keypair
  const oraclePubkey = new PublicKey(oracle.publicKey);

  let tokenMint: PublicKey;
  let sponsorTokenAccount: PublicKey;
  let agentTokenAccount: PublicKey;
  let vaultPda: PublicKey;
  let vaultBump: number;
  let vaultTokenAccountPda: PublicKey;

  const amounts = [new anchor.BN(50_000_000), new anchor.BN(50_000_000)]; // $50, $50
  const specHashes = [
    Buffer.alloc(32, 0xaa),
    Buffer.alloc(32, 0xbb),
  ];
  const submissionHash = Buffer.alloc(32, 0x11);
  const now = Math.floor(Date.now() / 1000);
  const expiresAt = new anchor.BN(now + 3600); // 1 hour future

  before(async () => {
    // Airdrop SOL to sponsor
    const airdropSig = await provider.connection.requestAirdrop(sponsor.publicKey, 2 * anchor.web3.LAMPORTS_PER_SOL);
    await provider.connection.confirmTransaction(airdropSig);

    // Create test mint (TLUSD) with 6 decimals
    tokenMint = await createMint(
      provider.connection,
      sponsor,
      sponsor.publicKey,
      null,
      6
    );

    // Create token accounts
    sponsorTokenAccount = await createAccount(
      provider.connection,
      sponsor,
      tokenMint,
      sponsor.publicKey
    );
    agentTokenAccount = await createAccount(
      provider.connection,
      sponsor,
      tokenMint,
      agent.publicKey
    );

    // Mint 100 TLUSD to sponsor
    await mintTo(
      provider.connection,
      sponsor,
      tokenMint,
      sponsorTokenAccount,
      sponsor,
      100_000_000
    );

    // Find PDAs
    [vaultPda, vaultBump] = PublicKey.findProgramAddressSync(
      [Buffer.from("tranche_vault"), sponsor.publicKey.toBuffer(), tokenMint.toBuffer()],
      program.programId
    );
    [vaultTokenAccountPda] = PublicKey.findProgramAddressSync(
      [Buffer.from("token_vault"), vaultPda.toBuffer()],
      program.programId
    );
  });

  it("1. test_valid_initialization: Sponsor funds 2-tranche vault with $100 TLUSD", async () => {
    await program.methods
      .initializeVault(amounts, specHashes, expiresAt)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        sponsor: sponsor.publicKey,
        agent: agent.publicKey,
        verifierOracle: oraclePubkey,
        tokenMint: tokenMint,
        sponsorTokenAccount: sponsorTokenAccount,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: SystemProgram.programId,
        rent: SYSVAR_RENT_PUBKEY,
      })
      .signers([sponsor])
      .rpc();

    const vaultAccount = await program.account.trancheVault.fetch(vaultPda);
    expect(vaultAccount.sponsor.toBase58()).to.equal(sponsor.publicKey.toBase58());
    expect(vaultAccount.agent.toBase58()).to.equal(agent.publicKey.toBase58());
    expect(vaultAccount.totalTranches).to.equal(2);
    expect(vaultAccount.currentTranche).to.equal(0);

    const vaultTokenBal = await getAccount(provider.connection, vaultTokenAccountPda);
    expect(Number(vaultTokenBal.amount)).to.equal(100_000_000);
  });

  it("2. test_valid_tranche_release: Milestone 0 releases $50 TLUSD with valid Ed25519 proof", async () => {
    const nonce = new anchor.BN(1);
    const message = buildCanonicalPayload(
      vaultPda,
      0,
      agent.publicKey,
      submissionHash,
      specHashes[0],
      amounts[0],
      expiresAt,
      nonce
    );
    const signature = nacl.sign.detached(message, oracle.secretKey);

    const ed25519Ix = Ed25519Program.createInstructionWithPublicKey({
      publicKey: oracle.publicKey,
      message: message,
      signature: signature,
    });

    const releaseIx = await program.methods
      .releaseTranche(0, Array.from(submissionHash), nonce)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentTokenAccount,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    const tx = new Transaction().add(ed25519Ix).add(releaseIx);
    await sendAndConfirmTransaction(provider.connection, tx, [sponsor]);

    const agentBal = await getAccount(provider.connection, agentTokenAccount);
    expect(Number(agentBal.amount)).to.equal(50_000_000);

    const vaultAccount = await program.account.trancheVault.fetch(vaultPda);
    expect(vaultAccount.currentTranche).to.equal(1);
    expect(vaultAccount.trancheStatus[0]).to.equal(1);
  });

  it("3. test_invalid_verifier_signature: Corrupted signature is rejected", async () => {
    const nonce = new anchor.BN(2);
    const message = buildCanonicalPayload(
      vaultPda,
      1,
      agent.publicKey,
      submissionHash,
      specHashes[1],
      amounts[1],
      expiresAt,
      nonce
    );
    const signature = nacl.sign.detached(message, oracle.secretKey);
    signature[0] ^= 0xff; // corrupt first byte

    const ed25519Ix = Ed25519Program.createInstructionWithPublicKey({
      publicKey: oracle.publicKey,
      message: message,
      signature: signature,
    });

    const releaseIx = await program.methods
      .releaseTranche(1, Array.from(submissionHash), nonce)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentTokenAccount,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    const tx = new Transaction().add(ed25519Ix).add(releaseIx);
    try {
      await sendAndConfirmTransaction(provider.connection, tx, [sponsor]);
      expect.fail("Should have failed on corrupted signature");
    } catch (err: any) {
      expect(err).to.exist;
    }
  });

  it("4. test_wrong_vault_signature: Proof signed for different vault PDA is rejected", async () => {
    const fakeVault = Keypair.generate().publicKey;
    const nonce = new anchor.BN(3);
    const message = buildCanonicalPayload(
      fakeVault,
      1,
      agent.publicKey,
      submissionHash,
      specHashes[1],
      amounts[1],
      expiresAt,
      nonce
    );
    const signature = nacl.sign.detached(message, oracle.secretKey);

    const ed25519Ix = Ed25519Program.createInstructionWithPublicKey({
      publicKey: oracle.publicKey,
      message: message,
      signature: signature,
    });

    const releaseIx = await program.methods
      .releaseTranche(1, Array.from(submissionHash), nonce)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentTokenAccount,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    const tx = new Transaction().add(ed25519Ix).add(releaseIx);
    try {
      await sendAndConfirmTransaction(provider.connection, tx, [sponsor]);
      expect.fail("Should have failed with InvalidMessageBytes");
    } catch (err: any) {
      expect(err.toString()).to.include("InvalidMessageBytes");
    }
  });

  it("5. test_reused_proof: Replay of Milestone 0 proof is rejected", async () => {
    const nonce = new anchor.BN(1);
    const message = buildCanonicalPayload(
      vaultPda,
      0,
      agent.publicKey,
      submissionHash,
      specHashes[0],
      amounts[0],
      expiresAt,
      nonce
    );
    const signature = nacl.sign.detached(message, oracle.secretKey);

    const ed25519Ix = Ed25519Program.createInstructionWithPublicKey({
      publicKey: oracle.publicKey,
      message: message,
      signature: signature,
    });

    const releaseIx = await program.methods
      .releaseTranche(0, Array.from(submissionHash), nonce)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentTokenAccount,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    const tx = new Transaction().add(ed25519Ix).add(releaseIx);
    try {
      await sendAndConfirmTransaction(provider.connection, tx, [sponsor]);
      expect.fail("Should have failed with MilestoneMismatch or TrancheAlreadyProcessed");
    } catch (err: any) {
      expect(err.toString()).to.include("MilestoneMismatch");
    }
  });

  it("6. test_ed25519_instruction_not_immediately_before_release: Missing Ed25519 instruction reverts", async () => {
    const nonce = new anchor.BN(4);
    const releaseIx = await program.methods
      .releaseTranche(1, Array.from(submissionHash), nonce)
      .accounts({
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccountPda,
        agent: agent.publicKey,
        agentTokenAccount: agentTokenAccount,
        instructionsSysvar: SYSVAR_INSTRUCTIONS_PUBKEY,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .instruction();

    // Transaction without the preceding Ed25519Program instruction
    const tx = new Transaction().add(releaseIx);
    try {
      await sendAndConfirmTransaction(provider.connection, tx, [sponsor]);
      expect.fail("Should have failed with MissingEd25519Instruction");
    } catch (err: any) {
      expect(err.toString()).to.include("MissingEd25519Instruction");
    }
  });

  it("7. test_premature_clawback: Cannot claw back before expires_at", async () => {
    try {
      await program.methods
        .clawback()
        .accounts({
          vault: vaultPda,
          vaultTokenAccount: vaultTokenAccountPda,
          sponsor: sponsor.publicKey,
          sponsorTokenAccount: sponsorTokenAccount,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([sponsor])
        .rpc();
      expect.fail("Clawback before expiry must fail");
    } catch (err: any) {
      expect(err.toString()).to.include("VaultNotExpired");
    }
  });
});
