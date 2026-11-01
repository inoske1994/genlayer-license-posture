# LicensePosture

A GenLayer Intelligent Contract that records what a repository's license file actually says at a pinned commit, with the sentence that proves each restriction.

## The problem it solves

Every dependency audit starts with the same question: can we ship this code, and on what terms. Today that question is answered by reading a license file by hand, or by trusting an SPDX identifier that someone typed into a manifest years ago.

Both shortcuts break in practice. A package can declare `MIT` in `package.json` while the `LICENSE` file it ships adds a non-commercial condition. A project can change its license at a specific version, as HashiCorp, Elastic and Redis all did, and the change lives in one commit that no manifest records. Standard identifiers also have no way to express the mixed case that matters most: a permissive base license plus a rider that limits commercial use, hosting, or time.

An SPDX string is a label. A license file is text. This contract reads the text, pins it with a hash, and writes down which sentences impose which restrictions.

## What the contract does

Two write methods:

`open(owner, repo, commit)` creates an immutable empty record and returns its id, for example `hashicorp/terraform@a48fc90914ea12217e1d6ece085383f17715aa97`. Duplicate commits are rejected, so history stays append only.

`review(record_id)` runs the non-deterministic part. It resolves the license file at that exact commit, hashes the normalized text, asks a model for one license family and for any restriction families the text imposes, and keeps a restriction only when the model's excerpt appears verbatim in the text. The result is written into the record once, and only once.

Every record ends in one posture:

| Posture | Meaning |
| --- | --- |
| `NO_RIDERS` | The file resolves to a known family and no restriction family was grounded in the text |
| `RIDERS_PRESENT` | At least one restriction is grounded, and the record carries the excerpt for each one |
| `INCONCLUSIVE` | The model claimed a restriction but its excerpt could not be verified, so the record is not clean |
| `UNKNOWN_FAMILY` | The text is readable but does not match any family the contract knows |
| `NO_LICENSE_FILE` | None of the nine conventional license paths exists at that commit |
| `SOURCE_UNUSABLE` | The host answered with an error, or the file exceeds the size limit |

The distinction between the last two and `NO_RIDERS` is the point. Silence is never treated as a clean result. A missing file, a host outage, and a readable file with no restrictions are three different facts, and the contract stores them as three different things.

Read methods: `get`, `get_posture`, `get_id`, `count`. `get_posture` exists so that another contract or an off-chain agent can gate on a decision without re-reading the web.

## Why this needs consensus

The two inputs are exactly the two things a single machine cannot be trusted with: a web page that can change or fail, and a language model whose output varies between runs.

GenLayer lets the contract fetch inside a non-deterministic block and requires validators to agree before state changes. This contract uses that to make the observation reproducible: every validator fetches the same URL and independently computes the same SHA-256 over the same normalized text, so a record can only be written when the source bytes agree. The model only selects sentences, and validators check those sentences against their own copy of the text.

See [docs/CONSENSUS.md](docs/CONSENSUS.md) for the validator design, including one live attempt that failed and what changed because of it.

## Live runs on Studionet

Chain `61999`, contract `0xF0FefC4f5b64776F43404CfdFD8532941305f156`, deployer `0x264465Ee4bCe6E6ba6be6c976dE8CfccA2148B09`. Every call below used 0 GEN.

| Step | Transaction | Consensus | Result |
| --- | --- | --- | --- |
| Deploy v2 | [`0x2aad5ac7...808c84`](https://explorer-studio.genlayer.com/tx/0x2aad5ac74ab35a79b138660d291a6aef7d610c2e1a62eeb832a47ced68808c84) | Accepted, 5 validators, rotation 0 | contract address created |
| `open` A | [`0xaf0b19ad...f04ce4`](https://explorer-studio.genlayer.com/tx/0xaf0b19adf40d9eed63795c9177efb143e21de8990ea282c7b64febc0bcf04ce4) | Accepted, rotation 0 | record `sindresorhus/is@e9c026c6...` |
| `review` A | [`0x3ecce293...c40fe7f`](https://explorer-studio.genlayer.com/tx/0x3ecce293e7ab7a322d693a6dc7b5751f0909c8342e499c1215b2d0ffec40fe7f) | Accepted, rotation 0 | `NO_RIDERS`, family `MIT` |
| `open` B | [`0xa856b934...939b4e`](https://explorer-studio.genlayer.com/tx/0xa856b934ff68ab097112858a22f5131bb024c8d23259ea78973065a3db939b4e) | Accepted, rotation 0 | record `hashicorp/terraform@a48fc909...` |
| `review` B | [`0x7fbf4042...82178cc`](https://explorer-studio.genlayer.com/tx/0x7fbf40422fb8a8d89be7f210be34bf34531e1143b697a0c03ec8ebde282178cc) | Accepted, rotation 0 | `RIDERS_PRESENT`, family `BUSL_1_1` |
| `open` D | [`0x71491d16...05d6c7d`](https://explorer-studio.genlayer.com/tx/0x71491d1636b4bdaa6c8552fe379a8de515ed3e8e9628c06d758fb30bb05d6c7d) | Accepted, rotation 0 | record `octocat/hello-world@7fd1a60b...` |
| `review` D | [`0x150231c3...5238a0c`](https://explorer-studio.genlayer.com/tx/0x150231c34d1d3a6c45a913d146dbac292b5199c21a5bba69cef7e72d95238a0c) | Accepted, rotation 0 | `NO_LICENSE_FILE`, no model call |

The stored record for case B, read back from the contract after consensus:

```json
{
  "id": "hashicorp/terraform@a48fc90914ea12217e1d6ece085383f17715aa97",
  "status": "ok",
  "posture": "RIDERS_PRESENT",
  "family": "BUSL_1_1",
  "path": "LICENSE",
  "text_length": 4950,
  "digest": "fbeaa43dd8432f31ec2256da19a1ad8abcd9db2f87aa4bee3e0d087a4d2b4412",
  "riders": {
    "FIELD_OF_USE": "offering the Licensed Work to third parties on a hosted or embedded basis",
    "NONCOMMERCIAL": "",
    "NO_MODIFICATION": "",
    "NO_REDISTRIBUTION": "",
    "SCALE_OR_TIME_LIMIT": "Four years from the date the Licensed Work is published."
  },
  "reviewed": true
}
```

The digest above is reproducible off chain. `scripts/digest_local.py` fetches the same URL, applies the same normalization, and prints the same hash without any GenLayer dependency:

```
python scripts/digest_local.py hashicorp terraform a48fc90914ea12217e1d6ece085383f17715aa97
# fbeaa43dd8432f31ec2256da19a1ad8abcd9db2f87aa4bee3e0d087a4d2b4412
```

[docs/LIVE-RUNS.md](docs/LIVE-RUNS.md) has the full table including the earlier deployment that reached `Undetermined` and why it is kept in this repository.

## Try it in Studio

1. Open [studio.genlayer.com](https://studio.genlayer.com), paste `contracts/license_posture.py`, and deploy on a network with full consensus.
2. Call `open` with `sindresorhus`, `is`, `e9c026c611c1160eaad50da00be4e676b626018f`.
3. Call `review` with `sindresorhus/is@e9c026c611c1160eaad50da00be4e676b626018f`. It returns `NO_RIDERS` after roughly 30 to 120 seconds.
4. Repeat with `hashicorp`, `terraform`, `a48fc90914ea12217e1d6ece085383f17715aa97` to see a grounded rider, or with `octocat`, `hello-world`, `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` to see `NO_LICENSE_FILE`.

## Tests

```
pip install -r requirements-dev.txt
python scripts/prepare_test_sdk.py
python -m pytest tests/direct -q
```

18 direct mode tests, all green. They cover the four postures that depend on the model, the two that do not, input validation, the append only guarantees, and four validator rejections: a forged digest, an excerpt that is not in the text, a restriction the adjudicating model does not support, and a family the adjudicating model does not support.

Direct mode replaces the web and the model with mocks. It proves the contract logic and the validator rules, not that the network agrees. The live table above is the evidence for the network side, and the two kinds of evidence are kept separate on purpose.

## Layout

```
contracts/license_posture.py     the contract, single file, no imports beyond hashlib and json
docs/DESIGN.md                   state layout, postures, path resolution, normalization
docs/CONSENSUS.md                validator design, why it is shaped this way, what it does not cover
docs/LIMITS.md                   what this contract does not prove
docs/LIVE-RUNS.md                every transaction, including the failed design
tests/direct/                    direct mode tests
scripts/prepare_test_sdk.py      pins the GenVM test runner that gltest expects
scripts/digest_local.py          reproduces a record digest off chain
```

## Scope

This is a contract plus documentation plus tests. It is not a product: there is no frontend, no indexer, and no CLI. The intended consumer is another contract or a build pipeline that needs a verifiable answer to one question, and the answer is deliberately narrow. If you need a full dependency scanner with SPDX parsing, this is the wrong tool.

MIT licensed. Written for the GenLayer builder campaign, contribution type Intelligent Contracts.
