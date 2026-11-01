# Consensus design

This document describes what validators check, why the design changed after the first live run, and what the design still does not cover.

## What is actually unstable here

A `review` call depends on two things that a single machine cannot be trusted with.

The web is unstable. GitHub raw responses can be rate limited, served from a cache with different trailing whitespace, or fail with a 5xx. If one validator sees the file and another sees an error, a contract that writes state anyway is writing a fact nobody agreed on.

The model is unstable. Two runs of the same prompt do not return the same JSON. Measured on this contract: for the same BUSL text, one run grounded three restriction families and another grounded two, and the choice of excerpt differed in wording and length even when the family agreed.

Anything that varies must therefore either sit outside consensus, be pinned by something deterministic, or be adjudicated in a way that does not require two open ended generations to match exactly.

## The deterministic layer

These steps produce identical values on every validator, so they can be compared exactly:

- the fixed order of the nine license paths,
- the HTTP status handling and the resulting `status` string,
- the whitespace normalization,
- the SHA-256 digest of the normalized text,
- whether a given excerpt is a substring of the normalized text,
- the mapping from grounded counts to a posture label.

Comparing digests is stronger than comparing file names or lengths. It says: my copy of the bytes at this commit is identical to yours, and every conclusion below is derived from the same text.

## First design, and the live failure

Version 1 put the whole decision vector under consensus. A validator was accepted only if its own extraction produced the same family, the same set of grounded restriction families, and the same set of claimed but ungrounded families as the leader. The reasoning was that anything the model decided should be agreed by all models.

That design returned `Undetermined` on the first live attempt, on `hashicorp/terraform`, after three leader rotations. All rotations ended without agreement, so the transaction finalized with no state change and the record stayed `pending`. The failure is on chain and is kept in this repository: transaction `0xbe326a66...3e017`, rotation count 3, consensus result `Undetermined`.

The transaction shows a healthy property and a real defect. Healthy: nothing was written. `get` afterwards returned `reviewed: false`, so a record can never hold a half agreed observation. Defect: requiring five independent models to produce the same free form answer is not a consensus rule, it is a coin flip with extra steps. Families differed in which restrictions they considered explicit, and any single differing bit forced another rotation.

## Current design: verify the claim, do not re-derive it

Version 2 keeps the leader as the only producer and turns validators into adjudicators. A validator does three things, in this order.

**1. Fetch independently and compare the source.** The validator walks the same nine paths, applies the same normalization, and computes its own digest. If the leader's `status`, `path` or `digest` differs, the validator rejects. This costs no model call and is exact. A leader that read a different file, or a different version of it, cannot pass.

**2. Check every excerpt against its own copy of the text.** For each restriction the leader grounded, the validator confirms the excerpt is a substring of the text it fetched itself. This is a pure string operation, also no model call. A leader that invents an excerpt, paraphrases, or stitches two sentences together fails here, and it fails deterministically.

**3. Ask one closed question about the leader's claims.** A single prompt shows the model the license text, the family the leader claimed, and each claimed restriction together with its excerpt. The model answers whether the text supports each claim:

```json
{"family_supported": true, "riders_supported": {"NONCOMMERCIAL": true}}
```

The validator accepts only if every answer is `true`. The model here is not asked "what is this license"; it is asked "is this specific claim about this specific passage correct". That is a judgement over given material rather than a free generation, which is why it converges across validators. In the live run, both reviews reached `Accepted` with rotation count 0.

### Why not `prompt_comparative`

GenLayer offers an equivalence principle that compares two model outputs against a stated principle, and it is the shortest path to a working non-deterministic contract. It compares two free generations for similarity. That is the thing that failed in version 1: it accepts differences in wording as long as the readings look compatible, and it cannot check a specific excerpt against a specific text. This contract needs a validator that can be exact about text and strict about claims, so it uses `gl.vm.run_nondet` with a custom validator instead.

## What each layer stops

| Attempted by a leader | Stopped by |
| --- | --- |
| Read a different file or a different commit | digest and path equality |
| Invent or paraphrase an excerpt | verbatim substring check |
| Quote a real sentence that does not impose the claimed restriction | adjudicating model |
| Mislabel the family | adjudicating model |
| Return a non-JSON or malformed payload | payload parser rejects, no state written |
| Claim success while the host errored | status equality, `SOURCE_UNUSABLE` recorded instead |
| Write a partial record after disagreement | `review` writes only after `run_nondet` returns |

Four of these are covered by direct mode tests: forged digest, prefix-invented excerpt, unsupported restriction, unsupported family.

## What the design still does not cover

The validator checks every claim the leader makes. It does not ask its own model to produce a reading from scratch, so it cannot detect a leader that under-reports. If a leader's model grounds two restrictions where another model would have grounded three, consensus will accept the two, and the record will be `RIDERS_PRESENT` with two excerpts rather than `INCONCLUSIVE`.

This is a real limitation, not a documentation gap. It is the price of a consensus rule that actually resolves. The honest reading of a record is:

> At this commit, the text hashes to this digest, and these excerpts were verified by validators as imposing these restrictions.

and not:

> No other restriction exists.

`NO_RIDERS` accordingly means "this reading grounded none", which is still a checkable statement because the digest lets anyone re-run the reading. The record is a witness with receipts, not a proof of absence.

The `claimed` map, which drives `INCONCLUSIVE`, is produced by the leader and is not cross-checked by validators. It is an honesty signal about the leader's own reading, not a consensus fact. A leader that lies about its own uncertainty can produce a cleaner posture than its model justified. Since the leader is chosen by the protocol rather than by the caller, and every restriction it does report is verified, this was accepted as a residual risk and documented rather than papered over.

## Determinism boundaries in one table

| Value | Deterministic | Under consensus |
| --- | --- | --- |
| HTTP response bytes | no | yes, via digest equality |
| `status`, `path`, `length` | derived | yes, compared exactly |
| `digest` | yes, given the bytes | yes, compared exactly |
| excerpt membership in text | yes, given bytes and excerpt | yes, compared exactly |
| `family` | no | yes, adjudicated |
| which restrictions are grounded | no | yes, adjudicated one by one |
| `claimed` | no | no, leader only |
| posture | yes, given the payload | yes, derived identically by all nodes |
