def test_inheritor_seed_has_six_source_backed_profiles():
    from src.seed_v20_content import INHERITOR_SEED
    assert len(INHERITOR_SEED) == 6
    assert all(item["source_url"].startswith("https://www.ihchina.cn/") for item in INHERITOR_SEED)
    assert all(item["name"] and item["craft_name"] and item["evidence_text"] for item in INHERITOR_SEED)
