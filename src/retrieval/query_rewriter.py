"""
查询重写器 - 使用LLM将口语化问题改写为适合检索的关键词
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RewrittenQuery:
    """
    改写后的查询结果
    
    Attributes:
        original_query: 原始查询
        rewritten_query: 改写后的核心查询
        expanded_queries: 扩展查询列表（包含同义词、相关概念等）
    """
    original_query: str
    rewritten_query: str
    expanded_queries: List[str]


class QueryRewriter:
    """
    查询重写器
    
    使用DeepSeek LLM将用户的口语化问题改写为更适合检索的关键词和查询
    """
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的非遗知识检索查询优化专家。
你的任务是将用户的口语化问题改写为更适合信息检索的查询语句。

请遵循以下规则：
1. 提取问题的核心意图
2. 扩展相关关键词（同义词、上位词、下位词）
3. 添加非遗领域的专业术语
4. 生成3-5个扩展查询
5. 保持查询简洁明了

输出格式必须为JSON：
{
    "rewritten_query": "改写后的核心查询",
    "expanded_queries": ["扩展查询1", "扩展查询2", "扩展查询3"]
}"""
    
    # 用户提示模板
    USER_PROMPT_TEMPLATE = """请优化以下查询：

"{query}"

请输出JSON格式的结果。"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 1
    ):
        """
        初始化查询重写器
        
        Args:
            api_key: API密钥，默认从config读取
            base_url: API基础URL，默认从config读取
            model: 模型名称，默认从config读取
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.model = model or settings.deepseek_model
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """获取OpenAI客户端（懒加载）"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    def _clean_json_response(self, content: str) -> str:
        """
        清理LLM返回的内容，移除markdown代码块包裹
        
        Args:
            content: 原始内容
        
        Returns:
            清理后的内容
        """
        # 移除 ```json 和 ``` 包裹
        content = content.strip()
        
        # 处理 ```json\n...```
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        # 移除结尾的 ```
        if content.endswith("```"):
            content = content[:-3]
        
        return content.strip()
    
    def rewrite(self, query: str) -> RewrittenQuery:
        """
        重写查询
        
        Args:
            query: 原始查询文本
        
        Returns:
            RewrittenQuery对象
        """
        if not query or not query.strip():
            return RewrittenQuery(
                original_query=query,
                rewritten_query="",
                expanded_queries=[]
            )
        
        # 检查是否启用查询重写
        if not settings.query_rewriting_enabled:
            return RewrittenQuery(
                original_query=query,
                rewritten_query=query,
                expanded_queries=[query]
            )
        
        user_prompt = self.USER_PROMPT_TEMPLATE.format(query=query.strip())
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                content = response.choices[0].message.content
                
                # 清理JSON格式
                cleaned_content = self._clean_json_response(content)
                
                # 解析JSON
                result = json.loads(cleaned_content)
                
                rewritten_query = result.get("rewritten_query", query)
                expanded_queries = result.get("expanded_queries", [query])
                
                # 确保expanded_queries非空
                if not expanded_queries:
                    expanded_queries = [rewritten_query]
                
                return RewrittenQuery(
                    original_query=query,
                    rewritten_query=rewritten_query,
                    expanded_queries=expanded_queries
                )
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    # 回退到原查询
                    return RewrittenQuery(
                        original_query=query,
                        rewritten_query=query,
                        expanded_queries=[query]
                    )
            except Exception as e:
                logger.error(f"查询重写失败: {e}")
                if attempt == self.max_retries - 1:
                    return RewrittenQuery(
                        original_query=query,
                        rewritten_query=query,
                        expanded_queries=[query]
                    )
        
        # 兜底返回
        return RewrittenQuery(
            original_query=query,
            rewritten_query=query,
            expanded_queries=[query]
        )
    
    def rewrite_batch(self, queries: List[str]) -> List[RewrittenQuery]:
        """
        批量重写查询
        
        Args:
            queries: 查询列表
        
        Returns:
            RewrittenQuery对象列表
        """
        return [self.rewrite(q) for q in queries]


class SimpleQueryRewriter(QueryRewriter):
    """
    简化版查询重写器
    
    不依赖LLM，使用规则进行简单的查询扩展
    适用于API Key不可用或需要快速处理的场景
    """
    
    # 同义词词典（简化版）
    SYNONYMS = {
        "制作": ["制作", "制作技艺", "工序", "工艺流程", "制作方法"],
        "历史": ["历史", "起源", "发展历程", "演变", "传承"],
        "材料": ["材料", "原料", "用料", "成分"],
        "传承": ["传承", "传承人", "传承技艺", "代代相传"],
        "特色": ["特色", "特点", "特征", "独特之处"],
        "价值": ["价值", "意义", "重要性", "作用"],
        "技艺": ["技艺", "技术", "工艺", "技法"],
        "文化": ["文化", "文化内涵", "文化价值"],
    }
    
    def rewrite(self, query: str) -> RewrittenQuery:
        """
        使用规则进行查询扩展
        
        Args:
            query: 原始查询
        
        Returns:
            RewrittenQuery对象
        """
        if not query or not query.strip():
            return RewrittenQuery(
                original_query=query,
                rewritten_query="",
                expanded_queries=[]
            )
        
        # 基础清理
        cleaned_query = query.strip()
        
        # 简单扩展
        expanded = [cleaned_query]
        
        # 检查是否包含已知关键词
        for key, synonyms in self.SYNONYMS.items():
            if key in cleaned_query:
                for syn in synonyms[:2]:  # 每个关键词添加1-2个同义词
                    if syn != cleaned_query and syn not in expanded:
                        expanded.append(syn)
        
        # 限制扩展查询数量
        expanded = expanded[:5]
        
        return RewrittenQuery(
            original_query=query,
            rewritten_query=cleaned_query,
            expanded_queries=expanded if expanded else [cleaned_query]
        )
