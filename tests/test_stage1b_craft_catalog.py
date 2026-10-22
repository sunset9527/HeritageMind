"""阶段 1B 的技艺 ID/名称必须来自同一份受控目录。"""

from types import SimpleNamespace

import pytest

from src.services.craft_catalog import CraftCatalog, CraftCatalogError, FALLBACK_CRAFTS


def test_catalog_prefers_active_projection_entries():
    projection = SimpleNamespace(
        encyclopedia_entries=lambda: [
            {"slug": "craft-jtl", "name": "景泰蓝制作技艺"},
            {"slug": "craft-sx", "name": "苏绣"},
        ]
    )

    catalog = CraftCatalog.from_projection(projection)

    assert catalog.as_api_items() == [
        {"id": "craft-jtl", "name": "景泰蓝制作技艺"},
        {"id": "craft-sx", "name": "苏绣"},
    ]
    assert all(item["id"] != "jingtailan" for item in catalog.as_api_items())


def test_catalog_falls_back_to_the_legacy_23_items():
    catalog = CraftCatalog.from_projection(None)

    assert len(catalog.as_api_items()) == 23
    assert catalog.as_api_items() == list(FALLBACK_CRAFTS)


def test_catalog_resolves_id_name_or_matching_pair():
    catalog = CraftCatalog.from_projection(None)

    assert catalog.resolve(craft_id="jingtailan") == ("jingtailan", "景泰蓝")
    assert catalog.resolve(craft_name=" 景泰蓝 ") == ("jingtailan", "景泰蓝")
    assert catalog.resolve(craft_id="jingtailan", craft_name="景泰蓝") == (
        "jingtailan",
        "景泰蓝",
    )


@pytest.mark.parametrize(
    ("craft_id", "craft_name"),
    [
        (None, None),
        ("unknown", None),
        (None, "不存在的技艺"),
        ("jingtailan", "苏绣"),
    ],
)
def test_catalog_rejects_missing_unknown_or_conflicting_values(craft_id, craft_name):
    catalog = CraftCatalog.from_projection(None)

    with pytest.raises(CraftCatalogError):
        catalog.resolve(craft_id=craft_id, craft_name=craft_name)
