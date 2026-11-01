# Limits

Everything below is a real boundary of the contract, not a roadmap item dressed up as one.

## It reads one file at one commit

Only the nine conventional paths are tried. A repository that puts its license inside a subdirectory, in `README.md`, in a `NOTICE` file, or only in package metadata will come back `NO_LICENSE_FILE`. That is a statement about those nine paths, not about the project's licensing.

Dual licensing is not detected. A repository with both `LICENSE-MIT` and `LICENSE-APACHE` returns whichever path appears first in the fixed order, and the record describes that file only. The presence of a second license file is not recorded.

## It does not parse the license

The contract does not implement SPDX matching, template diffing, or a clause level reader. It asks a model to name a family from a fixed list of 22 and to quote sentences. Consequences:

- a custom license that is legally MIT plus one extra sentence will likely be labelled `PROPRIETARY` or `UNKNOWN`, with the extra sentence grounded as a rider if the model quotes it,
- a family label is an approximation for a human reviewer, not a legal determination,
- a heavily modified version of a known license may be labelled as that license.

## The record reflects one reading

Validators verify every restriction the leader reports. They do not re-derive an independent reading, so a leader that grounds fewer restrictions than another model would produces a record with fewer restrictions, and consensus accepts it. This is explained in [CONSENSUS.md](CONSENSUS.md) and it is the main reason `NO_RIDERS` should be read as "this reading grounded none" rather than "no restriction exists".

The `claimed` map that drives `INCONCLUSIVE` is not cross-checked by validators at all.

## Digest is over normalized text

`digest` is SHA-256 over the text after whitespace collapsing. Two files that differ only in whitespace produce the same digest. Files that differ in any other character do not. This is intentional, since excerpt comparison needs the same normalization, but it means the digest is not a byte level commitment to the raw file. If you need byte equality, hash the raw body yourself against the URL in the record.

## Trust in the host

The contract trusts `raw.githubusercontent.com` to serve the content of the named commit. If GitHub serves different bytes to different validators, consensus does not resolve and nothing is written, which is fail safe but not a fix. If GitHub serves wrong bytes consistently, the record faithfully describes wrong bytes: the digest will still match what everyone fetched.

## Cost and latency

`review` makes one web request per candidate path until one succeeds, then one model call on the leader and one model call per validator. In the live runs, a review took roughly 30 to 60 seconds and 0 GEN on Studionet. On a paid network, expect model and storage costs; the contract does not batch, cache, or reuse earlier reviews of the same repository at a different commit.

## No re-review, no revocation

A record is written once. There is no method to re-review a commit, for example because the model behaved better later, and no method to revoke a record that turned out to be wrong. Correcting the past would require a new deployment. This was a deliberate choice: an observation that can be rewritten by whoever holds a key is worth less than one that cannot.

## Not legal advice

The contract reports text. It does not decide whether your use is permitted, whether a license is enforceable, or whether a rider applies to your distribution model. A `RIDERS_PRESENT` record is a prompt to read the excerpt, not a verdict.

## What has and has not been shown

Shown, with links in [LIVE-RUNS.md](LIVE-RUNS.md): Studionet deployments, three reviews reaching consensus with rotation count 0, one earlier attempt reaching `Undetermined` with no state written.

Not shown: behaviour on a paid network, behaviour under adversarial validators, behaviour when GitHub serves inconsistent content, and any measurement at a scale beyond three records. Direct mode tests are mocks and prove contract logic only.
