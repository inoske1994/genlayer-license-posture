# Design

## Shape of the record

One record per `owner/repo@commit`, stored as a JSON string in a `TreeMap`. The id is the key, and the id is also what `open` returns, so a caller never needs a second lookup to know what it just created.

```json
{
  "id": "hashicorp/terraform@a48fc90914ea12217e1d6ece085383f17715aa97",
  "owner": "hashicorp",
  "repo": "terraform",
  "commit": "a48fc90914ea12217e1d6ece085383f17715aa97",
  "opened_by": "0x264465Ee4bCe6E6ba6be6c976dE8CfccA2148B09",
  "status": "ok",
  "posture": "RIDERS_PRESENT",
  "family": "BUSL_1_1",
  "path": "LICENSE",
  "digest": "fbeaa43dd8432f31ec2256da19a1ad8abcd9db2f87aa4bee3e0d087a4d2b4412",
  "text_length": 4950,
  "riders": { "FIELD_OF_USE": "...", "NONCOMMERCIAL": "", "...": "" },
  "reviewed": true
}
```

Storage is three fields: `records`, `order`, `review_count`. `order` is an append only `DynArray` of ids, which makes the whole set enumerable and gives `get_id(index)` and `count()`. Records themselves are never deleted or rewritten after `reviewed` becomes true, so the sequence of reviews is a history rather than a mutable cache.

`opened_by` is the address that created the record. It is not used for authorisation, because the observation should be reproducible by anyone, not owned by whoever asked first.

## Two writes, and why the split

`open` is deterministic. It validates inputs, rejects duplicates, and writes an empty record with `status: "pending"`. Nothing about it needs consensus, so it is cheap and cannot fail because a host is slow.

`review` is where the web and the model enter. Splitting them means a caller can retry a failed review without losing the record, and it means an outage during a review does not leave a half written entry behind. If consensus does not resolve, the record simply stays `pending` and can be reviewed later. This is not hypothetical: the first live deployment hit exactly that case, see [CONSENSUS.md](CONSENSUS.md).

## Input validation

`owner` and `repo` are lowercased, then restricted to alphanumerics plus `-`, `_` and `.`, length 1 to 39, and neither `.` nor `..`. `commit` must be exactly 40 lowercase hex characters. A branch name or tag is rejected on purpose: the contract's claim is about one immutable tree, and anything that can move is not a pin.

The URL is never built from unvalidated input, so path traversal and query injection are closed off before the fetch happens.

## Resolving the license file

Nine conventional paths are tried in a fixed order:

```
LICENSE, LICENSE.md, LICENSE.txt, license, license.md,
COPYING, LICENSE-MIT, LICENSE-APACHE, COPYING.md
```

The order is fixed in the contract rather than derived from anything, because every validator must walk the same list and land on the same file. The first path that answers 200 with non-empty normalized text wins and its name is stored.

Status handling is deliberate:

| Host answer | Contract outcome |
| --- | --- |
| 200 with a file over 64 KiB | `SOURCE_UNUSABLE`, `status: "too_large"` |
| 200 with a file that normalizes to nothing | treated as absent, keep looking |
| 404 | keep looking |
| any other status | `SOURCE_UNUSABLE`, `status: "http_<code>"` |

An error is never reported as "no license file". If GitHub returns 503 for the first path, the record says so instead of claiming the repository has no license. That distinction is the difference between a source that is absent and a source that was not read.

## Normalization and the digest

```
normalize(text) = " ".join(text.replace(NBSP, " ").split())
digest(text)    = sha256(normalize(text).encode("utf-8")).hexdigest()
```

Whitespace runs collapse to a single space and non-breaking spaces become ordinary spaces. Nothing else is touched: no case folding, no punctuation stripping, no line ending changes beyond what whitespace collapsing already does.

Two reasons for this specific rule. First, GitHub raw responses differ in trailing newlines and indentation between mirrors and CDN edges, and CRLF versus LF line endings would otherwise change the hash of identical text. Second, excerpts returned by a model arrive with collapsed whitespace, so comparing an excerpt to the text requires the text to be collapsed the same way. Normalizing once, before hashing, keeps the digest and the excerpt check consistent with each other.

The digest is stored so that a reader can verify the record without trusting the model at all. `scripts/digest_local.py` reproduces the stored digest off chain with no GenLayer dependency. For the two live records it returns exactly the on-chain values.

## Excerpts are the evidence

The model is asked for one excerpt of 20 to 120 characters per restriction it claims. The contract then:

1. normalizes the excerpt with the same function used for the text,
2. rejects it if it is under 16 characters after normalization,
3. rejects it if it is over 240 characters,
4. keeps it only if it is a substring of the normalized text.

A restriction whose excerpt survives all four steps is `grounded`. A restriction the model claimed but whose excerpt did not survive is recorded in a separate `claimed` map and keeps the record out of `NO_RIDERS`. That is what makes `INCONCLUSIVE` possible and why a fabricated quote can never produce a clean record.

## Posture derivation

Posture is computed by the contract from the payload, not returned by the model:

```
grounded_count > 0        -> RIDERS_PRESENT
grounded_count == 0 and an ungrounded claim exists -> INCONCLUSIVE
family == UNKNOWN         -> UNKNOWN_FAMILY
otherwise                 -> NO_RIDERS
status == missing         -> NO_LICENSE_FILE
status is anything else   -> SOURCE_UNUSABLE
```

The model never emits a posture string. It reports observations, and code turns observations into a decision. This keeps the vocabulary of decisions small, fixed, and reviewable in the source rather than in a prompt.

## Family vocabulary

22 values covering the common permissive, copyleft, Creative Commons, source available and proprietary cases. Anything the model cannot map to this list becomes `UNKNOWN`, which produces `UNKNOWN_FAMILY` rather than a guess. The list is a tuple in the source, so adding a family is a one line change and does not require prompt surgery.

## Downstream use

`get_posture(record_id)` returns a single string, and it is a view method. A consumer contract, a CI gate, or an agent can read it without touching the web and without paying for a model call. The intended pattern is:

1. a grant, bounty or marketplace contract requires a dependency list,
2. for each dependency it reads the posture of the pinned commit,
3. `NO_RIDERS` passes, `RIDERS_PRESENT` needs a human decision, and the other four postures block the payout rather than silently passing.

The contract does not implement that policy. It supplies the fact that the policy needs, in a form that cannot change after the fact.
