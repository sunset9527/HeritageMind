"""检索模块测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.retriever import MultiSourceRetriever


class TestKeywordExtraction:

    def test_jieba_segmentation(self):
        retriever = MultiSourceRetriever()
        keywords = retriever._extract_keywords("景泰蓝的制作流程是什么")
        assert len(keywords) > 1
        assert "景泰蓝" in keywords

    def test_short_query(self):
        retriever = MultiSourceRetriever()
        keywords = retriever._extract_keywords("苏绣")
        assert len(keywords) >= 1

    def test_stopword_filtering(self):
        retriever = MultiSourceRetriever()
        keywords = retriever._extract_keywords("什么是龙泉青瓷")
        assert "是" not in keywords
        assert "什么" not in keywords


class TestKeywordSearch:

    def test_exact_match(self):
        retriever = MultiSourceRetriever()
        docs = retriever.retrieve("景泰蓝", top_k=3)
        assert len(docs) > 0

    def test_fuzzy_question(self):
        retriever = MultiSourceRetriever()
        docs = retriever.retrieve("苏绣有哪些针法特点", top_k=3)
        assert len(docs) > 0

    def test_new_craft_retrieval(self):
        retriever = MultiSourceRetriever()
        docs = retriever.retrieve("剪纸", top_k=3)
        assert len(docs) > 0


class TestQueryRewriter:

    def test_rule_rewrite(self):
        from src.retrieval.query_rewriter import QueryRewriter
        rw = QueryRewriter(use_llm=False)
        results = rw.rewrite("景泰蓝怎么做")
        assert len(results) >= 1
