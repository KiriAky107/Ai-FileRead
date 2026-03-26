"""
提示词工程服务

管理和优化与大模型交互的提示词
"""
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示词类型"""
    DOCUMENT_PARSING = "document_parsing"       # 文档解析
    FIELD_EXTRACTION = "field_extraction"       # 字段提取
    TABLE_FILLING = "table_filling"             # 表格填写
    QUERY_GENERATION = "query_generation"       # 查询生成
    TEXT_SUMMARY = "text_summary"               # 文本摘要
    INTENT_CLASSIFICATION = "intent_classification"  # 意图分类
    DATA_CLASSIFICATION = "data_classification" # 数据分类


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    type: PromptType
    system_prompt: str
    user_template: str
    examples: List[Dict[str, str]] = field(default_factory=list)  # Few-shot 示例
    rules: List[str] = field(default_factory=list)  # 特殊规则

    def format(
        self,
        context: Dict[str, Any],
        user_input: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        格式化提示词

        Args:
            context: 上下文数据
            user_input: 用户输入

        Returns:
            格式化后的消息列表
        """
        messages = []

        # 系统提示词
        system_content = self.system_prompt

        # 添加规则
        if self.rules:
            system_content += "\n\n【输出规则】\n" + "\n".join([f"- {rule}" for rule in self.rules])

        # 添加示例
        if self.examples:
            system_content += "\n\n【示例】\n"
            for i, ex in enumerate(self.examples):
                system_content += f"\n示例 {i+1}:\n"
                system_content += f"输入: {ex.get('input', '')}\n"
                system_content += f"输出: {ex.get('output', '')}\n"

        messages.append({"role": "system", "content": system_content})

        # 用户提示词
        user_content = self._format_user_template(context, user_input)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _format_user_template(
        self,
        context: Dict[str, Any],
        user_input: Optional[str]
    ) -> str:
        """格式化用户模板"""
        content = self.user_template

        # 替换上下文变量
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in content:
                if isinstance(value, (dict, list)):
                    content = content.replace(placeholder, json.dumps(value, ensure_ascii=False, indent=2))
                else:
                    content = content.replace(placeholder, str(value))

        # 添加用户输入
        if user_input:
            content += f"\n\n【用户需求】\n{user_input}"

        return content


class PromptEngineeringService:
    """提示词工程服务"""

    def __init__(self):
        self.templates: Dict[PromptType, PromptTemplate] = {}
        self._init_templates()

    def _init_templates(self):
        """初始化所有提示词模板"""

        # ==================== 文档解析模板 ====================
        self.templates[PromptType.DOCUMENT_PARSING] = PromptTemplate(
            name="文档解析",
            type=PromptType.DOCUMENT_PARSING,
            system_prompt="""你是一个专业的文档解析专家。你的任务是从各类文档（Word、Excel、Markdown、纯文本）中提取关键信息。

请严格按照JSON格式输出解析结果：
{
    "success": true/false,
    "document_type": "文档类型",
    "key_fields": {"字段名": "字段值", ...},
    "summary": "文档摘要（100字内）",
    "structured_data": {...}  // 提取的表格或其他结构化数据
}

重要规则：
- 只提取明确存在的信息，不要猜测
- 如果是表格数据，请以数组格式输出
- 日期请使用 YYYY-MM-DD 格式
- 金额请使用数字格式
- 如果无法提取某个字段，设置为 null""",
            user_template="""请解析以下文档内容：

=== 文档开始 ===
{content}
=== 文档结束 ===

请提取文档中的关键信息。""",
            examples=[
                {
                    "input": "合同金额：100万元\n签订日期：2024年1月15日\n甲方：张三\n乙方：某某公司",
                    "output": '{"success": true, "document_type": "合同", "key_fields": {"金额": 1000000, "日期": "2024-01-15", "甲方": "张三", "乙方": "某某公司"}, "summary": "甲乙双方签订的金额为100万元的合同", "structured_data": null}'
                }
            ],
            rules=[
                "只输出JSON，不要添加任何解释",
                "使用严格的JSON格式"
            ]
        )

        # ==================== 字段提取模板 ====================
        self.templates[PromptType.FIELD_EXTRACTION] = PromptTemplate(
            name="字段提取",
            type=PromptType.FIELD_EXTRACTION,
            system_prompt="""你是一个专业的数据提取专家。你的任务是从文档内容中提取指定字段的信息。

请严格按照以下JSON格式输出：
{
    "value": "提取到的值，找不到则为空字符串",
    "source": "数据来源描述",
    "confidence": 0.0到1.0之间的置信度
}

重要规则：
- 严格按字段名称匹配，不要提取无关信息
- 置信度反映你对提取结果的信心程度
- 如果字段不存在或无法确定，value设为空字符串，confidence设为0.0
- value必须是实际值，不能是"未找到"之类的描述""",
            user_template="""请从以下文档内容中提取指定字段的信息。

【需要提取的字段】
字段名称：{field_name}
字段类型：{field_type}
是否必填：{required}

【用户提示】
{hint}

【文档内容】
{context}

请提取字段值。""",
            examples=[
                {
                    "input": "文档内容：姓名张三，电话13800138000，邮箱zhangsan@example.com",
                    "output": '{"value": "张三", "source": "文档第1行", "confidence": 1.0}'
                }
            ],
            rules=[
                "只输出JSON，不要添加任何解释"
            ]
        )

        # ==================== 表格填写模板 ====================
        self.templates[PromptType.TABLE_FILLING] = PromptTemplate(
            name="表格填写",
            type=PromptType.TABLE_FILLING,
            system_prompt="""你是一个专业的表格填写助手。你的任务是根据提供的文档内容，填写表格模板中的字段。

请严格按照以下JSON格式输出：
{
    "filled_data": {{"字段1": "值1", "字段2": "值2", ...}},
    "fill_details": [
        {{"field": "字段1", "value": "值1", "source": "来源", "confidence": 0.95}},
        ...
    ]
}

重要规则：
- 只填写模板中存在的字段
- 值必须来自提供的文档内容，不要编造
- 如果某个字段在文档中找不到对应值，设为空字符串
- fill_details 中记录每个字段的详细信息""",
            user_template="""请根据以下文档内容，填写表格模板。

【表格模板字段】
{fields}

【用户需求】
{hint}

【参考文档内容】
{context}

请填写表格。""",
            examples=[
                {
                    "input": "字段：姓名、电话\n文档：张三，电话是13800138000",
                    "output": '{"filled_data": {"姓名": "张三", "电话": "13800138000"}, "fill_details": [{"field": "姓名", "value": "张三", "source": "文档第1行", "confidence": 1.0}, {"field": "电话", "value": "13800138000", "source": "文档第1行", "confidence": 1.0}]}'
                }
            ],
            rules=[
                "只输出JSON，不要添加任何解释"
            ]
        )

        # ==================== 查询生成模板 ====================
        self.templates[PromptType.QUERY_GENERATION] = PromptTemplate(
            name="查询生成",
            type=PromptType.QUERY_GENERATION,
            system_prompt="""你是一个SQL查询生成专家。你的任务是根据用户的自然语言需求，生成相应的数据库查询语句。

请严格按照以下JSON格式输出：
{
    "sql_query": "生成的SQL查询语句",
    "explanation": "查询逻辑说明"
}

重要规则：
- 只生成 SELECT 查询语句，不要生成 INSERT/UPDATE/DELETE
- 必须包含 WHERE 条件限制查询范围
- 表名和字段名使用反引号包裹
- 确保SQL语法正确
- 如果无法生成有效的查询，sql_query设为空字符串""",
            user_template="""根据以下信息生成查询语句。

【数据库表结构】
{table_schema}

【RAG检索到的上下文】
{rag_context}

【用户查询需求】
{user_intent}

请生成SQL查询。""",
            examples=[
                {
                    "input": "表：orders(订单号, 金额, 日期, 客户)\n需求：查询2024年1月销售额超过10000的订单",
                    "output": '{"sql_query": "SELECT * FROM `orders` WHERE `日期` >= \\'2024-01-01\\' AND `日期` < \\'2024-02-01\\' AND `金额` > 10000", "explanation": "筛选2024年1月销售额超过10000的订单"}'
                }
            ],
            rules=[
                "只输出JSON，不要添加任何解释",
                "禁止生成 DROP、DELETE、TRUNCATE 等危险操作"
            ]
        )

        # ==================== 文本摘要模板 ====================
        self.templates[PromptType.TEXT_SUMMARY] = PromptTemplate(
            name="文本摘要",
            type=PromptType.TEXT_SUMMARY,
            system_prompt="""你是一个专业的文本摘要专家。你的任务是对长文档进行压缩，提取关键信息。

请严格按照以下JSON格式输出：
{
    "summary": "摘要内容（不超过200字）",
    "key_points": ["要点1", "要点2", "要点3"],
    "keywords": ["关键词1", "关键词2", "关键词3"]
}""",
            user_template="""请为以下文档生成摘要：

=== 文档开始 ===
{content}
=== 文档结束 ===

生成简明摘要。""",
            rules=[
                "只输出JSON，不要添加任何解释"
            ]
        )

        # ==================== 意图分类模板 ====================
        self.templates[PromptType.INTENT_CLASSIFICATION] = PromptTemplate(
            name="意图分类",
            type=PromptType.INTENT_CLASSIFICATION,
            system_prompt="""你是一个意图分类专家。你的任务是分析用户的自然语言输入，判断用户的真实意图。

支持的意图类型：
- upload: 上传文档
- parse: 解析文档
- query: 查询数据
- fill: 填写表格
- export: 导出数据
- analyze: 分析数据
- other: 其他/未知

请严格按照以下JSON格式输出：
{
    "intent": "意图类型",
    "confidence": 0.0到1.0之间的置信度,
    "entities": {{"实体名": "实体值", ...}},  // 识别出的关键实体
    "suggestion": "建议的下一步操作"
}""",
            user_template="""请分析以下用户输入，判断其意图：

【用户输入】
{user_input}

请分类。""",
            rules=[
                "只输出JSON，不要添加任何解释"
            ]
        )

        # ==================== 数据分类模板 ====================
        self.templates[PromptType.DATA_CLASSIFICATION] = PromptTemplate(
            name="数据分类",
            type=PromptType.DATA_CLASSIFICATION,
            system_prompt="""你是一个数据分类专家。你的任务是判断数据的类型和格式。

请严格按照以下JSON格式输出：
{
    "data_type": "text/number/date/email/phone/url/amount/other",
    "format": "具体格式描述",
    "is_valid": true/false,
    "normalized_value": "规范化后的值"
}""",
            user_template="""请分析以下数据的类型和格式：

【数据】
{value}

【期望类型（如果有）】
{expected_type}

请分类。""",
            rules=[
                "只输出JSON，不要添加任何解释"
            ]
        )

    def get_prompt(
        self,
        type: PromptType,
        context: Dict[str, Any],
        user_input: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        获取格式化后的提示词

        Args:
            type: 提示词类型
            context: 上下文数据
            user_input: 用户输入

        Returns:
            消息列表
        """
        template = self.templates.get(type)
        if not template:
            logger.warning(f"未找到提示词模板: {type}")
            return [{"role": "user", "content": str(context)}]

        return template.format(context, user_input)

    def get_template(self, type: PromptType) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        return self.templates.get(type)

    def add_template(self, template: PromptTemplate):
        """添加自定义提示词模板"""
        self.templates[template.type] = template
        logger.info(f"已添加提示词模板: {template.name}")

    def update_template(self, type: PromptType, **kwargs):
        """更新提示词模板"""
        template = self.templates.get(type)
        if template:
            for key, value in kwargs.items():
                if hasattr(template, key):
                    setattr(template, key, value)

    def optimize_prompt(
        self,
        type: PromptType,
        feedback: str,
        iteration: int = 1
    ) -> List[Dict[str, str]]:
        """
        根据反馈优化提示词

        Args:
            type: 提示词类型
            feedback: 优化反馈
            iteration: 迭代次数

        Returns:
            优化后的提示词
        """
        template = self.templates.get(type)
        if not template:
            return []

        # 简单优化策略：根据反馈添加规则
        optimization_rules = {
            "准确率低": "提高要求，明确指出必须从原文提取，不要猜测",
            "格式错误": "强调JSON格式要求，提供更详细的格式示例",
            "遗漏信息": "添加提取更多细节的要求",
        }

        new_rules = []
        for keyword, rule in optimization_rules.items():
            if keyword in feedback:
                new_rules.append(rule)

        if new_rules:
            template.rules.extend(new_rules)

        return template.format({}, None)


# ==================== 全局单例 ====================

prompt_service = PromptEngineeringService()
