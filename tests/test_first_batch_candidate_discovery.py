"""Candidate collection keeps transient network failures retryable."""


def test_upsert_candidate_record_replaces_prior_transient_failure():
    from tools.discover_first_batch_ihchina_candidates import upsert_candidate_record

    previous = [
        {"registry_document_key": "mct-first-batch-351", "status": "unresolved"},
        {"registry_document_key": "mct-first-batch-355", "status": "candidate"},
    ]
    refreshed = {
        "registry_document_key": "mct-first-batch-351",
        "status": "candidate",
        "project_detail_candidates": [{"url": "https://www.ihchina.cn/project_details/14261.html"}],
    }

    records = upsert_candidate_record(previous, refreshed)

    assert len(records) == 2
    assert records[0] == refreshed
    assert records[1] == previous[1]
