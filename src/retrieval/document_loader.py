"""
非遗文档加载器 - 加载和处理非遗技艺相关文档
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from config import settings
from src.services.knowledge_manifest import ManifestValidationError, load_manifest

logger = logging.getLogger(__name__)

# 非遗技艺中文名 → 拼音ID 全量映射（23 种技艺，与 data/crafts 目录一一对应）
# 提升为模块级常量：供检索置顶/层级聚合等模块复用，避免多处维护同一份名单
CRAFT_NAME_TO_ID = {
    "景泰蓝": "jingtailan", "苏绣": "suxiu", "龙泉青瓷": "longquan_ci",
    "宜兴紫砂": "yixing_zisha", "芜湖铁画": "wuhu_tiehua", "蜀锦": "shujin",
    "剪纸": "jianzhi", "景德镇瓷器": "jingdezhen_ciqi", "南京云锦": "nanjing_yunjin",
    "东阳木雕": "dongyang_mudiao", "苗族蜡染": "miaozu_laran", "木版年画": "muban_nianhua",
    "缂丝": "kesi", "竹编": "zhubian", "玉雕": "yudiao",
    "漆器": "qiqi", "唐三彩": "tangsancai", "钧瓷": "junci",
    "汝瓷": "ruci", "泥人张": "nirenzhang", "皮影戏": "piyingxi",
    "壮锦": "zhuangjin", "京剧": "jingju",
}

# 反向映射：拼音ID → 中文名
CRAFT_ID_TO_NAME = {v: k for k, v in CRAFT_NAME_TO_ID.items()}


class HeritageDocumentLoader:
    """
    非遗文档加载器
    
    功能：
    1. 从文件系统加载文档
    2. 支持多种格式（txt, md, json）
    3. 文档预处理和清洗
    4. 文档元数据管理
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        初始化文档加载器
        
        Args:
            base_path: 文档基础路径
        """
        if base_path is None:
            base_path = settings.crafts_doc_path
        self.base_path = Path(base_path)
    
    def load_craft_documents(self) -> List[Dict[str, Any]]:
        """
        加载所有技艺文档（自动扫描目录下所有 .txt 文件）

        Returns:
            文档列表，每项包含 id, content, metadata
        """
        documents: List[Dict[str, Any]] = []
        if not self.base_path.exists():
            logger.warning(f"文档目录不存在：{self.base_path}")
        else:
            # 自动扫描所有 .txt 文件
            for file_path in sorted(self.base_path.glob("*.txt")):
                # 从文件名提取 craft_id（去掉 .txt 后缀，拼音化作为 id）
                craft_name = file_path.stem  # e.g. "景泰蓝"
                craft_id = self._name_to_id(craft_name)
                doc = self._load_single_document(file_path, craft_id)
                if doc:
                    documents.append(doc)

        documents.extend(self._load_published_curated_documents())

        logger.info(f"已加载{len(documents)}篇技艺文档")
        return documents

    def _load_published_curated_documents(self) -> List[Dict[str, Any]]:
        """Load only reviewed source-package documents alongside legacy craft files."""
        manifest_path = self.base_path.parent / "knowledge_sources" / "manifest.json"
        if not manifest_path.exists():
            return []
        try:
            manifest = load_manifest(manifest_path)
        except ManifestValidationError as error:
            logger.warning("来源化知识包无效，已跳过：%s", error)
            return []

        documents = []
        for item in manifest.documents:
            if item.status != "published":
                continue
            craft_id = self._name_to_id(item.craft_name)
            metadata = self._extract_metadata(item.content, craft_id)
            metadata.update({
                "document_key": item.document_key,
                "dataset_version": manifest.dataset_version,
                "publication_status": item.status,
                "source_name": item.source_name,
                "source_url": item.source_url,
                "accessed_at": item.accessed_at,
                "license_note": item.license_note,
            })
            documents.append({
                "id": f"curated:{item.document_key}",
                "content": item.content,
                "char_count": len(item.content),
                "metadata": metadata,
            })
        return documents

    @staticmethod
    def _name_to_id(name: str) -> str:
        """中文名称转拼音 ID（简易映射）"""
        return CRAFT_NAME_TO_ID.get(name, name.lower().replace(" ", "_"))
    
    def _load_single_document(
        self,
        file_path: Path,
        craft_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        加载单个文档
        
        Args:
            file_path: 文件路径
            craft_id: 技艺ID
        
        Returns:
            文档数据字典
        """
        try:
            if file_path.suffix == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif file_path.suffix == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif file_path.suffix == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    content = data.get("content", "")
            else:
                logger.warning(f"不支持的文件格式：{file_path.suffix}")
                return None
            
            # 预处理内容
            content = self._preprocess_content(content)
            
            # 提取元数据
            metadata = self._extract_metadata(content, craft_id)
            
            return {
                "id": craft_id,
                "content": content,
                "char_count": len(content),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"文档加载失败 {file_path}: {e}")
            return None
    
    def _preprocess_content(self, content: str) -> str:
        """
        预处理文档内容
        
        Args:
            content: 原始内容
        
        Returns:
            预处理后的内容
        """
        # 去除多余空白
        lines = content.split("\n")
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # 保留非空行
                processed_lines.append(line)
        
        # 合并为单个字符串
        content = "\n".join(processed_lines)
        
        # 去除多余的连续空行
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        
        return content
    
    def _extract_metadata(
        self,
        content: str,
        craft_id: str
    ) -> Dict[str, Any]:
        """
        从内容中提取元数据
        
        Args:
            content: 文档内容
            craft_id: 技艺ID
        
        Returns:
            元数据字典
        """
        metadata = {
            "craft_id": craft_id,
            "char_count": len(content),
            "line_count": content.count("\n") + 1
        }
        
        # 提取技艺名称（全量映射，修复原来仅 6 个中文名的缺漏：其余技艺曾回退为拼音ID）
        metadata["craft_name"] = CRAFT_ID_TO_NAME.get(craft_id, craft_id)
        
        # 提取关键词
        keywords = []
        keyword_sets = {
            "jingtailan": ["掐丝", "珐琅", "点蓝", "烧蓝", "磨光", "镀金"],
            "suxiu": ["刺绣", "绣针", "丝线", "针法", "绷面"],
            "longquan_ci": ["青瓷", "釉色", "烧制", "拉坯", "釉料"],
            "yixing_zisha": ["紫砂", "壶", "泥料", "成型", "窑"],
            "wuhu_tiehua": ["铁画", "锻造", "铁锤", "焊接", "退火"],
            "shujin": ["蜀锦", "织机", "丝绸", "图案", "花楼"]
        }
        
        if craft_id in keyword_sets:
            for kw in keyword_sets[craft_id]:
                if kw in content:
                    keywords.append(kw)
        
        metadata["keywords"] = keywords
        
        return metadata
    
    def load_documents_by_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """
        按类型加载文档
        
        Args:
            doc_type: 文档类型（craft/history/heritage）
        
        Returns:
            文档列表
        """
        all_docs = self.load_craft_documents()
        
        # 简单分类
        type_mapping = {
            "craft": ["jingtailan", "suxiu", "longquan_ci", "yixing_zisha", "wuhu_tiehua", "shujin"]
        }
        
        if doc_type in type_mapping:
            return [doc for doc in all_docs if doc["id"] in type_mapping[doc_type]]
        
        return all_docs
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文档
        
        Args:
            doc_id: 文档ID
        
        Returns:
            文档数据
        """
        documents = self.load_craft_documents()
        for doc in documents:
            if doc["id"] == doc_id:
                return doc
        return None
    
    def search_documents(
        self,
        keyword: str,
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        在文档中搜索关键词
        
        Args:
            keyword: 搜索关键词
            documents: 要搜索的文档列表，None时加载所有文档
        
        Returns:
            匹配的文档列表
        """
        if documents is None:
            documents = self.load_craft_documents()
        
        results = []
        keyword_lower = keyword.lower()
        
        for doc in documents:
            if keyword_lower in doc["content"].lower():
                # 计算匹配位置
                content = doc["content"]
                positions = []
                start = 0
                while True:
                    pos = content.lower().find(keyword_lower, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1
                
                results.append({
                    **doc,
                    "match_count": len(positions),
                    "match_positions": positions[:5]  # 只保留前5个位置
                })
        
        # 按匹配次数排序
        results.sort(key=lambda x: x["match_count"], reverse=True)
        
        return results
    
    def add_document(
        self,
        craft_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加新文档
        
        Args:
            craft_id: 技艺ID
            content: 文档内容
            metadata: 元数据
        
        Returns:
            是否添加成功
        """
        try:
            file_path = self.base_path / f"{craft_id}.txt"
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"文档已保存：{file_path}")
            return True
            
        except Exception as e:
            logger.error(f"文档保存失败：{e}")
            return False
    
    def delete_document(self, craft_id: str) -> bool:
        """
        删除文档
        
        Args:
            craft_id: 技艺ID
        
        Returns:
            是否删除成功
        """
        try:
            for suffix in [".txt", ".md", ".json"]:
                file_path = self.base_path / f"{craft_id}{suffix}"
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"文档已删除：{file_path}")
                    return True
            
            logger.warning(f"文档不存在：{craft_id}")
            return False
            
        except Exception as e:
            logger.error(f"文档删除失败：{e}")
            return False
    
    def get_document_summary(self) -> Dict[str, Any]:
        """
        获取文档库摘要
        
        Returns:
            摘要信息
        """
        documents = self.load_craft_documents()
        
        total_chars = sum(doc["char_count"] for doc in documents)
        all_keywords = []
        
        for doc in documents:
            all_keywords.extend(doc["metadata"].get("keywords", []))
        
        # 统计关键词频率
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        
        return {
            "total_documents": len(documents),
            "total_characters": total_chars,
            "crafts": [doc["metadata"]["craft_name"] for doc in documents],
            "top_keywords": sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        }
