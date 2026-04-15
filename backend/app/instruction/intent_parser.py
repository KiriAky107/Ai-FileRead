"""
意图解析器模块

解析用户自然语言指令，识别意图和参数
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntentParser:
    """意图解析器"""

    # 意图类型定义
    INTENT_EXTRACT = "extract"           # 信息提取
    INTENT_FILL_TABLE = "fill_table"    # 填表
    INTENT_SUMMARIZE = "summarize"       # 摘要总结
    INTENT_QUESTION = "question"         # 问答
    INTENT_SEARCH = "search"              # 搜索
    INTENT_COMPARE = "compare"            # 对比分析
    INTENT_TRANSFORM = "transform"        # 格式转换
    INTENT_EDIT = "edit"                  # 编辑文档
    INTENT_UNKNOWN = "unknown"            # 未知

    # 意图关键词映射
    INTENT_KEYWORDS = {
        INTENT_EXTRACT: ["提取", "抽取", "获取", "找出", "查找", "识别", "找到"],
        INTENT_FILL_TABLE: ["填表", "填写", "填充", "录入", "导入到表格", "填写到"],
        INTENT_SUMMARIZE: ["总结", "摘要", "概括", "概述", "归纳", "提炼", "分析", "聊聊"],
        INTENT_QUESTION: ["问答", "回答", "解释", "什么是", "为什么", "如何", "怎样", "多少", "几个"],
        INTENT_SEARCH: ["搜索", "查找", "检索", "查询", "找"],
        INTENT_COMPARE: ["对比", "比较", "差异", "区别", "不同"],
        INTENT_TRANSFORM: ["转换", "转化", "变成", "转为", "导出"],
        INTENT_EDIT: ["修改", "编辑", "调整", "改写", "润色", "优化"],
    }

    # 实体模式定义
    ENTITY_PATTERNS = {
        "number": [r"\d+", r"[一二三四五六七八九十百千万]+"],
        "date": [r"\d{4}年", r"\d{1,2}月", r"\d{1,2}日"],
        "percentage": [r"\d+(\.\d+)?%", r"\d+(\.\d+)?‰"],
        "currency": [r"\d+(\.\d+)?万元", r"\d+(\.\d+)?亿元", r"\d+(\.\d+)?元"],
    }

    def __init__(self):
        self.intent_history: List[Dict[str, Any]] = []

    async def parse(self, text: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        解析自然语言指令

        Args:
            text: 用户输入的自然语言
            context: 执行上下文（包含对话历史等）

        Returns:
            (意图类型, 参数字典)
        """
        text = text.strip()
        if not text:
            return self.INTENT_UNKNOWN, {}

        # 检查对话历史中的上下文
        conversation_history = []
        if context and context.get("conversation_history"):
            conversation_history = context.get("conversation_history", [])
            logger.info(f"解析时使用对话历史: {len(conversation_history)} 条消息")

        # 记录历史
        self.intent_history.append({"text": text, "intent": None})

        # 识别意图（考虑对话上下文）
        intent = self._recognize_intent_with_context(text, conversation_history)

        # 提取参数
        params = self._extract_params(text, intent)

        # 更新历史
        if self.intent_history:
            self.intent_history[-1]["intent"] = intent

        logger.info(f"意图解析: text={text[:50]}..., intent={intent}, params={params}")

        return intent, params

    def _recognize_intent_with_context(self, text: str, conversation_history: List[Dict[str, Any]]) -> str:
        """
        基于对话历史识别意图

        Args:
            text: 当前用户输入
            conversation_history: 对话历史

        Returns:
            意图类型
        """
        # 如果对话历史为空，使用基础意图识别
        if not conversation_history:
            return self._recognize_intent(text)

        # 基于历史上下文进行意图识别
        # 分析最近的对话了解用户意图的延续性
        last_intent = None
        last_topic = None

        for msg in conversation_history[-5:]:  # 最多看最近5条消息
            if msg.get("role") == "assistant":
                last_intent = msg.get("intent")
            if msg.get("intent") and msg.get("intent") != "unknown":
                last_topic = msg.get("intent")

        # 如果当前消息很短（如"继续"、"是的"），可能延续之前的意图
        short_confirmation = ["是", "是的", "好", "继续", "ok", "好", "接着", "然后", "还有吗"]
        if text.strip() in short_confirmation or len(text.strip()) <= 3:
            if last_topic:
                logger.info(f"简短确认，延续之前的意图: {last_topic}")
                return last_topic

        # 否则使用标准意图识别
        return self._recognize_intent(text)

    def _recognize_intent(self, text: str) -> str:
        """识别意图类型"""
        intent_scores: Dict[str, float] = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return self.INTENT_UNKNOWN

        # 返回得分最高的意图
        return max(intent_scores, key=intent_scores.get)

    def _extract_params(self, text: str, intent: str) -> Dict[str, Any]:
        """提取参数"""
        params: Dict[str, Any] = {
            "entities": self._extract_entities(text),
            "document_refs": self._extract_document_refs(text),
            "field_refs": self._extract_field_refs(text),
            "template_refs": self._extract_template_refs(text),
        }

        # 根据意图类型提取特定参数
        if intent == self.INTENT_QUESTION:
            params["question"] = text
            params["focus"] = self._extract_question_focus(text)
        elif intent == self.INTENT_FILL_TABLE:
            params["template"] = self._extract_template_info(text)
        elif intent == self.INTENT_EXTRACT:
            params["target_fields"] = self._extract_target_fields(text)

        return params

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体"""
        entities: Dict[str, List[str]] = {}

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text)
                matches.extend(found)
            if matches:
                entities[entity_type] = list(set(matches))

        return entities

    def _extract_document_refs(self, text: str) -> List[str]:
        """提取文档引用"""
        # 匹配 "文档1"、"doc1"、"第一个文档" 等
        refs = []

        # 数字索引: 文档1, doc1, 第1个文档
        num_patterns = [
            r"[文档doc]+(\d+)",
            r"第(\d+)个文档",
            r"第(\d+)份",
        ]
        for pattern in num_patterns:
            matches = re.findall(pattern, text.lower())
            refs.extend([f"doc_{m}" for m in matches])

        # "所有文档"、"全部文档"
        if any(kw in text for kw in ["所有", "全部", "整个"]):
            refs.append("all_docs")

        return refs

    def _extract_field_refs(self, text: str) -> List[str]:
        """提取字段引用"""
        fields = []

        # 匹配引号内的字段名
        quoted = re.findall(r"['\"『「]([^'\"』」]+)['\"』」]", text)
        fields.extend(quoted)

        # 匹配 "xxx字段"、"xxx列" 等
        field_patterns = [
            r"([^\s]+)字段",
            r"([^\s]+)列",
            r"([^\s]+)数据",
        ]
        for pattern in field_patterns:
            matches = re.findall(pattern, text)
            fields.extend(matches)

        return list(set(fields))

    def _extract_template_refs(self, text: str) -> List[str]:
        """提取模板引用"""
        templates = []

        # 匹配 "表格模板"、"Excel模板"、"表1" 等
        template_patterns = [
            r"([^\s]+模板)",
            r"表(\d+)",
            r"([^\s]+表格)",
        ]
        for pattern in template_patterns:
            matches = re.findall(pattern, text)
            templates.extend(matches)

        return list(set(templates))

    def _extract_question_focus(self, text: str) -> Optional[str]:
        """提取问题焦点"""
        # "什么是XXX"、"XXX是什么"
        match = re.search(r"[什么是]([^?]+)", text)
        if match:
            return match.group(1).strip()

        # "XXX有多少"
        match = re.search(r"([^?]+)有多少", text)
        if match:
            return match.group(1).strip()

        return None

    def _extract_template_info(self, text: str) -> Optional[Dict[str, str]]:
        """提取模板信息"""
        template_info: Dict[str, str] = {}

        # 提取模板类型
        if "excel" in text.lower() or "xlsx" in text.lower() or "电子表格" in text:
            template_info["type"] = "xlsx"
        elif "word" in text.lower() or "docx" in text.lower() or "文档" in text:
            template_info["type"] = "docx"

        return template_info if template_info else None

    def _extract_target_fields(self, text: str) -> List[str]:
        """提取目标字段 - 按分隔符切分再逐段清理"""
        fields = []

        # 去除提取/抽取前缀
        cleaned_text = re.sub(r"^(?:提取|抽取)", "", text).strip()

        # 按'和'、'与'、'、'分割成多段
        segments = re.split(r"[和与、]", cleaned_text)

        # 常见前缀（这些不是字段名，需要去除）
        prefixes = ["文档中的", "文档中", "文件中的", "文件中", "内容中的", "内容中"]

        for seg in segments:
            seg = seg.strip()
            # 去除常见前缀
            for p in prefixes:
                if seg.startswith(p):
                    seg = seg[len(p):]
                    break
            if seg and 2 <= len(seg) <= 20:
                fields.append(seg)

        return list(set(fields))

    def get_intent_history(self) -> List[Dict[str, Any]]:
        """获取意图历史"""
        return self.intent_history

    def clear_history(self):
        """清空历史"""
        self.intent_history = []


# 全局单例
intent_parser = IntentParser()
