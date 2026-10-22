"""维护任务在 API embedding 模式首次调用时也必须正确分支。"""


class _EmbeddingsEndpoint:
    def create(self, *, model, input):
        return type("Response", (), {"data": [type("Item", (), {"embedding": [len(input)]})()]})()


class _ApiClient:
    embeddings = _EmbeddingsEndpoint()


def test_embed_documents_initializes_backend_before_selecting_api_branch(monkeypatch):
    import src.retrieval.embeddings as module

    def create_model():
        module._embedding_backend = "api"
        return _ApiClient()

    monkeypatch.setattr(module, "get_embedding_model", create_model)
    module._embedding_backend = None
    manager = module.EmbeddingManager()

    assert manager.embed_documents(["甲", "乙乙"]) == [[1], [2]]


def test_embed_query_initializes_backend_before_selecting_api_branch(monkeypatch):
    import src.retrieval.embeddings as module

    def create_model():
        module._embedding_backend = "api"
        return _ApiClient()

    monkeypatch.setattr(module, "get_embedding_model", create_model)
    module._embedding_backend = None
    manager = module.EmbeddingManager()

    assert manager.embed_query("景泰蓝") == [3]
