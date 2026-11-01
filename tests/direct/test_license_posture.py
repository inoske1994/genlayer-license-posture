import json

CONTRACT = "contracts/license_posture.py"
COMMIT = "0" * 40
OWNER = "acme"
REPO = "widget"
RECORD = "acme/widget@" + COMMIT

RIDERS = ("NONCOMMERCIAL", "NO_REDISTRIBUTION", "NO_MODIFICATION", "FIELD_OF_USE", "SCALE_OR_TIME_LIMIT")

MIT_TEXT = """MIT License

Copyright (c) 2026 Acme

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

RIDER_TEXT = """MIT License

Copyright (c) 2026 Acme

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software, to use and modify it for non-commercial purposes only.
Commercial use requires a separate written license from Acme.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

RIDER_QUOTE = "to use and modify it for non-commercial purposes only"
BOGUS_QUOTE = "this sentence is not in the license file at all"


def _riders(**overrides):
    values = {name: "" for name in RIDERS}
    values.update(overrides)
    return values


def _verify(claimed, family=True):
    supported = {name: True for name in claimed}
    return {"family_supported": family, "riders_supported": supported}


def _install(direct_vm, text, extract, verify, status=200):
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r".*raw\.githubusercontent\.com/acme/widget/.*",
        {"method": "GET", "status": status, "body": text},
    )
    direct_vm.mock_llm(r"(?s).*Task 1\. Identify the license family.*", json.dumps(extract))
    direct_vm.mock_llm(r"(?s).*checking one claim about a license file.*", json.dumps(verify))


def _open(contract):
    return contract.open(OWNER, REPO, COMMIT)


def test_clean_license_has_no_riders(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)
    assert record_id == RECORD

    _install(direct_vm, MIT_TEXT, {"family": "MIT", "riders": _riders()}, _verify([]))
    assert contract.review(record_id) == "NO_RIDERS"

    record = json.loads(contract.get(record_id))
    assert record["family"] == "MIT"
    assert record["path"] == "LICENSE"
    assert record["status"] == "ok"
    assert record["reviewed"] is True
    assert set(record["riders"].values()) == {""}
    assert len(record["digest"]) == 64


def test_grounded_rider_is_recorded(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(
        direct_vm,
        RIDER_TEXT,
        {"family": "MIT", "riders": _riders(NONCOMMERCIAL=RIDER_QUOTE)},
        _verify(["NONCOMMERCIAL"]),
    )
    assert contract.review(record_id) == "RIDERS_PRESENT"
    record = json.loads(contract.get(record_id))
    assert record["riders"]["NONCOMMERCIAL"] == RIDER_QUOTE


def test_unverifiable_quote_never_becomes_a_clean_record(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(
        direct_vm,
        RIDER_TEXT,
        {"family": "MIT", "riders": _riders(NONCOMMERCIAL=BOGUS_QUOTE)},
        _verify([]),
    )
    assert contract.review(record_id) == "INCONCLUSIVE"
    record = json.loads(contract.get(record_id))
    assert set(record["riders"].values()) == {""}


def test_unknown_family_is_reported(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(
        direct_vm,
        "All rights reserved. This file is not a known license.",
        {"family": "SOMETHING_ELSE", "riders": _riders()},
        _verify([]),
    )
    assert contract.review(record_id) == "UNKNOWN_FAMILY"


def test_missing_license_file_stops_before_the_model(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r".*raw\.githubusercontent\.com/acme/widget/.*",
        {"method": "GET", "status": 404, "body": ""},
    )
    assert contract.review(record_id) == "NO_LICENSE_FILE"

    record = json.loads(contract.get(record_id))
    assert record["status"] == "missing"
    assert record["family"] == ""
    assert record["reviewed"] is True


def test_server_error_is_unusable_source(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(direct_vm, "", {"family": "MIT", "riders": _riders()}, _verify([]), status=503)
    assert contract.review(record_id) == "SOURCE_UNUSABLE"
    record = json.loads(contract.get(record_id))
    assert record["status"] == "http_503"


def test_oversized_file_is_unusable_source(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(direct_vm, "a" * 70000, {"family": "MIT", "riders": _riders()}, _verify([]))
    assert contract.review(record_id) == "SOURCE_UNUSABLE"
    assert json.loads(contract.get(record_id))["status"] == "too_large"


def test_input_validation(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("owner"):
        contract.open("bad owner", REPO, COMMIT)
    with direct_vm.expect_revert("repo"):
        contract.open(OWNER, "bad/repo", COMMIT)
    with direct_vm.expect_revert("commit"):
        contract.open(OWNER, REPO, "abc123")
    with direct_vm.expect_revert("commit"):
        contract.open(OWNER, REPO, "A" * 40)


def test_one_record_per_commit(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _open(contract)
    with direct_vm.expect_revert("already exists"):
        contract.open("ACME", "Widget", COMMIT)


def test_review_runs_once(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)
    _install(direct_vm, MIT_TEXT, {"family": "MIT", "riders": _riders()}, _verify([]))
    contract.review(record_id)
    with direct_vm.expect_revert("already reviewed"):
        contract.review(record_id)


def test_unknown_record_is_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("unknown record"):
        contract.review("nobody/nothing@" + COMMIT)
    assert contract.get_posture("nobody/nothing@" + COMMIT) == ""


def test_index_and_count(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _open(contract)
    direct_vm.sender = direct_bob
    contract.open(OWNER, "gadget", COMMIT)

    assert contract.count() == 2
    assert contract.get_id(0) == RECORD
    assert contract.get_id(1) == "acme/gadget@" + COMMIT
    assert contract.get_id(2) == ""
    assert contract.get_id(-1) == ""


def _install_verify_only(direct_vm, text, verify):
    """Replace mocks for a validator-only run: the validator fetches the text and asks
    the verification question. No extraction mock is registered on purpose."""
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r".*raw\.githubusercontent\.com/acme/widget/.*",
        {"method": "GET", "status": 200, "body": text},
    )
    direct_vm.mock_llm(r"(?s).*checking one claim about a license file.*", json.dumps(verify))


def _reviewed_record(direct_vm, contract):
    record_id = _open(contract)
    _install(direct_vm, MIT_TEXT, {"family": "MIT", "riders": _riders()}, _verify([]))
    contract.review(record_id)
    return json.loads(contract.get(record_id))


def test_validator_accepts_a_genuine_leader(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _reviewed_record(direct_vm, contract)
    assert direct_vm.run_validator() is True


def test_validator_rejects_a_forged_digest(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record = _reviewed_record(direct_vm, contract)

    forged = json.dumps({
        "status": "ok", "path": "LICENSE", "text": "", "length": record["text_length"],
        "digest": "f" * 64, "family": "MIT", "riders": _riders(), "claimed": _riders(),
    }, sort_keys=True)
    assert direct_vm.run_validator(leader_result=forged) is False


def test_validator_rejects_a_quote_that_is_not_in_the_text(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record = _reviewed_record(direct_vm, contract)

    forged = json.dumps({
        "status": "ok", "path": "LICENSE", "text": "", "length": record["text_length"],
        "digest": record["digest"], "family": "MIT",
        "riders": _riders(NONCOMMERCIAL="a fabricated restriction sentence that is absent"),
        "claimed": _riders(),
    }, sort_keys=True)
    assert direct_vm.run_validator(leader_result=forged) is False


def test_validator_rejects_a_rider_the_model_does_not_support(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record_id = _open(contract)

    _install(
        direct_vm,
        RIDER_TEXT,
        {"family": "MIT", "riders": _riders(NONCOMMERCIAL=RIDER_QUOTE)},
        _verify(["NONCOMMERCIAL"]),
    )
    contract.review(record_id)
    record = json.loads(contract.get(record_id))

    _install_verify_only(
        direct_vm, RIDER_TEXT, {"family_supported": True, "riders_supported": {"NONCOMMERCIAL": False}}
    )
    forged = json.dumps({
        "status": "ok", "path": "LICENSE", "text": "", "length": record["text_length"],
        "digest": record["digest"], "family": "MIT",
        "riders": _riders(NONCOMMERCIAL=RIDER_QUOTE), "claimed": _riders(),
    }, sort_keys=True)
    assert direct_vm.run_validator(leader_result=forged) is False


def test_validator_rejects_a_family_the_model_does_not_support(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    record = _reviewed_record(direct_vm, contract)

    _install_verify_only(direct_vm, MIT_TEXT, {"family_supported": False, "riders_supported": {}})
    forged = json.dumps({
        "status": "ok", "path": "LICENSE", "text": "", "length": record["text_length"],
        "digest": record["digest"], "family": "GPL_3_0", "riders": _riders(), "claimed": _riders(),
    }, sort_keys=True)
    assert direct_vm.run_validator(leader_result=forged) is False


def test_validator_rejects_leader_error(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _reviewed_record(direct_vm, contract)
    assert direct_vm.run_validator(leader_error=RuntimeError("model unavailable")) is False
