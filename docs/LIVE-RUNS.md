# Live runs

All transactions below are on GenLayer Studionet, chain `61999`. Deployer: `0x264465Ee4bCe6E6ba6be6c976dE8CfccA2148B09`. Every call cost 0 GEN and was submitted through Studio with execution mode `Normal (Full Consensus)`.

## Version 2, current

Contract: [`0xF0FefC4f5b64776F43404CfdFD8532941305f156`](https://explorer-studio.genlayer.com/address/0xF0FefC4f5b64776F43404CfdFD8532941305f156)

| Step | Transaction | Consensus | Result |
| --- | --- | --- | --- |
| Deploy | [`0x2aad5ac74a...68808c84`](https://explorer-studio.genlayer.com/tx/0x2aad5ac74ab35a79b138660d291a6aef7d610c2e1a62eeb832a47ced68808c84) | Finalized, Accepted, 5 validators, rotation 0 | contract created, code visible in calldata |
| `open` A | [`0xaf0b19adf4...bcf04ce4`](https://explorer-studio.genlayer.com/tx/0xaf0b19adf40d9eed63795c9177efb143e21de8990ea282c7b64febc0bcf04ce4) | Accepted, rotation 0 | returns `sindresorhus/is@e9c026c611c1160eaad50da00be4e676b626018f` |
| `review` A | [`0x3ecce293e7...ec40fe7f`](https://explorer-studio.genlayer.com/tx/0x3ecce293e7ab7a322d693a6dc7b5751f0909c8342e499c1215b2d0ffec40fe7f) | Accepted, rotation 0 | `NO_RIDERS` |
| `open` B | [`0xa856b934ff...3db939b4e`](https://explorer-studio.genlayer.com/tx/0xa856b934ff68ab097112858a22f5131bb024c8d23259ea78973065a3db939b4e) | Accepted, rotation 0 | returns `hashicorp/terraform@a48fc90914ea12217e1d6ece085383f17715aa97` |
| `review` B | [`0x7fbf40422f...e282178cc`](https://explorer-studio.genlayer.com/tx/0x7fbf40422fb8a8d89be7f210be34bf34531e1143b697a0c03ec8ebde282178cc) | Accepted, rotation 0 | `RIDERS_PRESENT` |
| `open` D | [`0x71491d1636...b05d6c7d`](https://explorer-studio.genlayer.com/tx/0x71491d1636b4bdaa6c8552fe379a8de515ed3e8e9628c06d758fb30bb05d6c7d) | Accepted, rotation 0 | returns `octocat/hello-world@7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` |
| `review` D | [`0x150231c34d...d95238a0c`](https://explorer-studio.genlayer.com/tx/0x150231c34d1d3a6c45a913d146dbac292b5199c21a5bba69cef7e72d95238a0c) | Accepted, rotation 0 | `NO_LICENSE_FILE` |

### Case A, MIT

Leader payload as shown in the equivalence principle output:

```json
{
  "status": "ok",
  "path": "license",
  "length": 1117,
  "digest": "6d0ffe243280b1c7634e32484daca6327008d11be972ce9d463af0a18049b20e",
  "family": "MIT",
  "riders": {"NONCOMMERCIAL": "", "NO_REDISTRIBUTION": "", "NO_MODIFICATION": "", "FIELD_OF_USE": "", "SCALE_OR_TIME_LIMIT": ""},
  "claimed": {"NONCOMMERCIAL": false, "NO_REDISTRIBUTION": false, "NO_MODIFICATION": false, "FIELD_OF_USE": false, "SCALE_OR_TIME_LIMIT": false}
}
```

Posture `NO_RIDERS`. Family and digest match an independent off chain computation.

### Case B, BUSL

```json
{
  "status": "ok",
  "path": "LICENSE",
  "length": 4950,
  "digest": "fbeaa43dd8432f31ec2256da19a1ad8abcd9db2f87aa4bee3e0d087a4d2b4412",
  "family": "BUSL_1_1",
  "riders": {
    "FIELD_OF_USE": "offering the Licensed Work to third parties on a hosted or embedded basis",
    "NONCOMMERCIAL": "",
    "NO_MODIFICATION": "",
    "NO_REDISTRIBUTION": "",
    "SCALE_OR_TIME_LIMIT": "Four years from the date the Licensed Work is published."
  },
  "claimed": {"FIELD_OF_USE": true, "NONCOMMERCIAL": false, "NO_MODIFICATION": false, "NO_REDISTRIBUTION": false, "SCALE_OR_TIME_LIMIT": true}
}
```

Posture `RIDERS_PRESENT`. Both excerpts are substring exact in the normalized file.

### Case D, no license file

```json
{"status": "missing", "path": "", "length": 0, "text": ""}
```

Posture `NO_LICENSE_FILE`. No model call was made: the nine paths all answered 404, so `leader_fn` returned before `exec_prompt`.

### Reproducing the digests

```
python scripts/digest_local.py sindresorhus is e9c026c611c1160eaad50da00be4e676b626018f
# path   license
# length 1117
# digest 6d0ffe243280b1c7634e32484daca6327008d11be972ce9d463af0a18049b20e

python scripts/digest_local.py hashicorp terraform a48fc90914ea12217e1d6ece085383f17715aa97
# path   LICENSE
# length 4950
# digest fbeaa43dd8432f31ec2256da19a1ad8abcd9db2f87aa4bee3e0d087a4d2b4412

python scripts/digest_local.py octocat hello-world 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d
# no license file at any of the nine conventional paths
```

Both digests match the values the validators agreed on. This is the point where the off chain check and the on chain record can be compared by anyone.

## Version 1, kept because one call failed

Contract: [`0x0A6D22E8138eCF1730055591dE45b5DAD29b6fc8`](https://explorer-studio.genlayer.com/address/0x0A6D22E8138eCF1730055591dE45b5DAD29b6fc8)

| Step | Transaction | Consensus | Result |
| --- | --- | --- | --- |
| Deploy | [`0xe64e4bd8df...03de1e42`](https://explorer-studio.genlayer.com/tx/0xe64e4bd8dfbfe46113fe199f626ec838793cc337a8d018314c39882703de1e42) | Finalized, Accepted, rotation 0 | contract created |
| `open` A | [`0xc194bbfd8c...bb38b38a6`](https://explorer-studio.genlayer.com/tx/0xc194bbfd8c2dbff78b63a7c7bb26a6841660e92dc338cf2afa595e1b387b38a6) | Accepted, rotation 0 | record created |
| `review` A | [`0xf374ded6d8...ff543c57`](https://explorer-studio.genlayer.com/tx/0xf374ded6d8952367a529f567883add9974729e9e3bd4b6c209dfab3bff543c57) | Accepted, rotation 0 | `NO_RIDERS` |
| `open` B | [`0x97130bf543...6da20716`](https://explorer-studio.genlayer.com/tx/0x97130bf54322b206cf6e97565c804b4cb459c451f6be257bdbbe9abb6da20716) | Accepted, rotation 0 | record created |
| `review` B | [`0xbe326a6692...1f63e017`](https://explorer-studio.genlayer.com/tx/0xbe326a669262b31d79ee8ecf7a776bff86575f63615951a50f1135581f63e017) | Finalized, **Undetermined**, rotation count **3** | nothing written |

The version 1 validator required the leader and every validator to produce the same family and the same set of grounded restrictions from their own independent generations. For BUSL text the models disagreed on which restrictions count as explicit and on which sentence to quote, so three leader rotations all failed to reach agreement, and the transaction finalized without state. Reading the record afterwards returned `status: "pending"`, `reviewed: false`.

Two things came out of that call. The fail safe behaviour was correct: no partial observation was stored, and the record remained reviewable. The consensus rule was wrong: it compared two free generations and required them to be identical, which is not something a five model network will do on open ended text.

Version 2 replaced that with independent verification of the leader's claims: fetch and compare the source digest, check every excerpt as a literal substring, then one closed question per claim. The same repository then produced `RIDERS_PRESENT` at rotation count 0 on the first attempt. The redesign is described in [CONSENSUS.md](CONSENSUS.md).

Note that the two versions produced different readings of the same file: version 1's leader grounded three restrictions for BUSL, version 2's leader grounded two. That is the limitation described in [LIMITS.md](LIMITS.md), observed rather than assumed.
