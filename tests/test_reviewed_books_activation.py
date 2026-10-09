import json


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_activation_validates_then_keeps_a_recoverable_previous_projection(tmp_path):
    from src.services.reviewed_books_activation import activate_reviewed_candidate

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write(corpus / "catalog.json", {"corpus_id": "books-v1", "status": "active"})
    _write(corpus / "craft_metadata.json", {
        "corpus_id": "books-v1", "projects": [{"project_name": "旧项目"}],
    })
    candidate = tmp_path / "candidate.json"
    _write(candidate, {
        "corpus_id": "books-v1",
        "project_count": 1,
        "person_count": 1,
        "unlinked_person_numbers": [],
        "projects": [{
            "craft_id": "new-craft",
            "project_name": "新项目",
            "inheritors": [{
                "name": "甲",
                "evidence": [{
                    "book_title": "国家级非物质文化遗产项目代表性传承人大典 第1卷",
                    "page": 15,
                    "excerpt": "甲的传记。",
                }],
            }],
            "description": {"text": "", "evidence": []},
        }],
    })
    audit = tmp_path / "audit.json"
    _write(audit, {
        "status": "review_only_not_published",
        "national_main_list_items": 1219,
        "national_main_list_unique_names": 1218,
        "dedicated_volume_inheritor_profiles": 1,
        "inheritor_profiles_missing_biography": [],
        "inheritor_profiles_missing_book_project_name": [],
        "unlinked_inheritor_numbers": [],
        "ocr_main_list_audit": {
            "second": {"official_count": 510, "covered_count": 510, "missing_from_book": []},
            "third": {"official_count": 191, "covered_count": 191, "missing_from_book": []},
        },
    })
    backup = tmp_path / "backups" / "previous.json"

    result = activate_reviewed_candidate(corpus, candidate, audit, backup)

    assert result["project_count"] == 1
    assert json.loads(backup.read_text(encoding="utf-8"))["projects"][0]["project_name"] == "旧项目"
    assert json.loads((corpus / "craft_metadata.json").read_text(encoding="utf-8"))["projects"][0]["project_name"] == "新项目"


def test_activation_refuses_a_candidate_with_a_non_dedicated_inheritor_source(tmp_path):
    from src.services.reviewed_books_activation import validate_reviewed_candidate

    metadata = {
        "corpus_id": "books-v1", "project_count": 1, "person_count": 1,
        "unlinked_person_numbers": [],
        "projects": [{"project_name": "项目", "inheritors": [{
            "name": "甲", "evidence": [{"book_title": "第二批国家级非物质文化遗产名录简介"}],
        }]}],
    }
    audit = {
        "status": "review_only_not_published", "national_main_list_items": 1219,
        "national_main_list_unique_names": 1218, "dedicated_volume_inheritor_profiles": 1,
        "inheritor_profiles_missing_biography": [], "inheritor_profiles_missing_book_project_name": [],
        "unlinked_inheritor_numbers": [],
        "ocr_main_list_audit": {
            "second": {"official_count": 510, "covered_count": 510, "missing_from_book": []},
            "third": {"official_count": 191, "covered_count": 191, "missing_from_book": []},
        },
    }

    try:
        validate_reviewed_candidate(metadata, audit)
    except ValueError as error:
        assert "传承人大典" in str(error)
    else:
        raise AssertionError("应拒绝其他图书来源的人物")
