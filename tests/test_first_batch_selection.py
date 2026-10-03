"""The first deep-research batch must be balanced without inventing a tenth medicine item."""


def test_select_first_batch_uses_all_nine_traditional_medicine_items_and_100_total():
    from src.services.first_batch_selection import RegistryProject, select_first_batch

    categories = [
        ("传统手工技艺", 11),
        ("传统戏剧", 10), ("传统医药", 9), ("民间美术", 10),
        ("民间文学", 10), ("民间舞蹈", 10), ("民间音乐", 10),
        ("民俗", 10), ("曲艺", 10), ("杂技与竞技", 10),
    ]
    projects = [
        RegistryProject(f"record-{category}-{index}", f"{category}-{index}", category)
        for category, count in categories
        for index in range(1, count + 1)
    ]

    selected = select_first_batch(projects)

    assert len(selected) == 100
    assert sum(item.category == "传统医药" for item in selected) == 9
    assert sum(item.category == "传统手工技艺" for item in selected) == 11
    assert all(item in selected for item in projects if item.category == "传统医药")
