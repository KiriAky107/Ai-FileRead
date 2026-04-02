"""
Markdown 文档 AI 分析服务

支持：
- 分章节解析（中文章节编号：一、二、三， （一）（二）（三））
- 结构化数据提取
- 流式输出
- 多种分析类型
"""
import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.llm_service import llm_service
from app.core.document_parser import MarkdownParser

logger = logging.getLogger(__name__)


class MarkdownSection:
    """文档章节结构"""
    def __init__(self, number: str, title: str, level: int, content: str, line_start: int, line_end: int):
        self.number = number  # 章节编号，如 "一", "（一）", "1"
        self.title = title
        self.level = level  # 层级深度
        self.content = content  # 章节内容（不含子章节）
        self.line_start = line_start
        self.line_end = line_end
        self.subsections: List[MarkdownSection] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "level": self.level,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "subsections": [s.to_dict() for s in self.subsections]
        }


class MarkdownAIService:
    """Markdown 文档 AI 分析服务"""

    # 中文章节编号模式
    CHINESE_NUMBERS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    CHINESE_SUFFIX = "、"
    PARENTHESIS_PATTERN = re.compile(r'^（([一二三四五六七八九十]+)\s*(.+)$')
    CHINESE_SECTION_PATTERN = re.compile(r'^([一二三四五六七八九十]+)、\s*(.+)$')
    ARABIC_SECTION_PATTERN = re.compile(r'^(\d+)\.\s+(.+)$')

    def __init__(self):
        self.parser = MarkdownParser()

    def get_supported_analysis_types(self) -> list:
        """获取支持的分析类型"""
        return [
            "summary",      # 文档摘要
            "outline",     # 大纲提取
            "key_points",   # 关键点提取
            "questions",    # 生成问题
            "tags",         # 生成标签
            "qa",           # 问答对
            "statistics",   # 统计数据分析（适合政府公报）
            "section"       # 分章节详细分析
        ]

    def extract_sections(self, content: str, titles: List[Dict]) -> List[MarkdownSection]:
        """
        从文档内容中提取章节结构

        识别以下章节格式：
        - 一级：一、二、三...
        - 二级：（一）（二）（三）...
        - 三级：1. 2. 3. ...
        """
        sections = []
        lines = content.split('\n')

        # 构建标题行到内容的映射
        title_lines = {}
        for t in titles:
            title_lines[t.get('line', 0)] = t

        current_section = None
        section_stack = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检查是否是一级标题（中文数字 + 、）
            match = self.CHINESE_SECTION_PATTERN.match(stripped)
            if match:
                # 结束当前章节
                if current_section:
                    current_section.content = self._get_section_content(
                        lines, current_section.line_start, i - 1
                    )

                current_section = MarkdownSection(
                    number=match.group(1),
                    title=match.group(2),
                    level=1,
                    content="",
                    line_start=i,
                    line_end=len(lines)
                )
                sections.append(current_section)
                section_stack = [current_section]
                continue

            # 检查是否是二级标题（（一）（二）...）
            match = self.PARENTHESIS_PATTERN.match(stripped)
            if match and current_section:
                # 结束当前子章节
                if section_stack and len(section_stack) > 1:
                    parent = section_stack[-1]
                    parent.content = self._get_section_content(
                        lines, parent.line_start, i - 1
                    )

                subsection = MarkdownSection(
                    number=match.group(1),
                    title=match.group(2),
                    level=2,
                    content="",
                    line_start=i,
                    line_end=len(lines)
                )
                current_section.subsections.append(subsection)
                section_stack = [current_section, subsection]
                continue

            # 检查是否是三级标题（1. 2. 3.）
            match = self.ARABIC_SECTION_PATTERN.match(stripped)
            if match and len(section_stack) > 1:
                # 结束当前子章节
                if len(section_stack) > 2:
                    parent = section_stack[-1]
                    parent.content = self._get_section_content(
                        lines, parent.line_start, i - 1
                    )

                sub_subsection = MarkdownSection(
                    number=match.group(1),
                    title=match.group(2),
                    level=3,
                    content="",
                    line_start=i,
                    line_end=len(lines)
                )
                section_stack[-1].subsections.append(sub_subsection)
                section_stack = section_stack[:-1] + [sub_subsection]
                continue

        # 处理最后一个章节
        if current_section:
            current_section.content = self._get_section_content(
                lines, current_section.line_start, len(lines)
            )

        return sections

    def _get_section_content(self, lines: List[str], start: int, end: int) -> str:
        """获取指定行范围的内容"""
        if start > end:
            return ""
        content_lines = lines[start-1:end]
        # 清理：移除标题行和空行
        cleaned = []
        for line in content_lines:
            stripped = line.strip()
            if not stripped:
                continue
            # 跳过章节标题行
            if self.CHINESE_SECTION_PATTERN.match(stripped):
                continue
            if self.PARENTHESIS_PATTERN.match(stripped):
                continue
            if self.ARABIC_SECTION_PATTERN.match(stripped):
                continue
            cleaned.append(stripped)
        return '\n'.join(cleaned)

    async def analyze_markdown(
        self,
        file_path: str,
        analysis_type: str = "summary",
        user_prompt: str = "",
        section_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 AI 分析 Markdown 文档

        Args:
            file_path: 文件路径
            analysis_type: 分析类型
            user_prompt: 用户自定义提示词
            section_number: 指定分析的章节编号（如 "一" 或 "（一）"）

        Returns:
            dict: 分析结果
        """
        try:
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                return {
                    "success": False,
                    "error": parse_result.error
                }

            data = parse_result.data

            # 提取章节结构
            sections = self.extract_sections(data.get("content", ""), data.get("titles", []))

            # 如果指定了章节，只分析该章节
            target_content = data.get("content", "")
            target_title = parse_result.metadata.get("filename", "")

            if section_number:
                section = self._find_section(sections, section_number)
                if section:
                    target_content = section.content
                    target_title = f"{section.number}、{section.title}"
                else:
                    return {
                        "success": False,
                        "error": f"未找到章节: {section_number}"
                    }

            # 根据分析类型构建提示词
            prompt = self._build_prompt(
                content=target_content,
                analysis_type=analysis_type,
                user_prompt=user_prompt,
                title=target_title
            )

            # 调用 LLM 分析
            messages = [
                {"role": "system", "content": self._get_system_prompt(analysis_type)},
                {"role": "user", "content": prompt}
            ]

            response = await llm_service.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=4000
            )

            analysis = llm_service.extract_message_content(response)

            return {
                "success": True,
                "filename": parse_result.metadata.get("filename", ""),
                "analysis_type": analysis_type,
                "section": target_title if section_number else None,
                "word_count": len(target_content),
                "structure": {
                    "title_count": parse_result.metadata.get("title_count", 0),
                    "code_block_count": parse_result.metadata.get("code_block_count", 0),
                    "table_count": parse_result.metadata.get("table_count", 0),
                    "section_count": len(sections)
                },
                "sections": [s.to_dict() for s in sections[:10]],  # 最多返回10个一级章节
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Markdown AI 分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_markdown_stream(
        self,
        file_path: str,
        analysis_type: str = "summary",
        user_prompt: str = "",
        section_number: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式分析 Markdown 文档 (SSE)

        Yields:
            str: SSE 格式的数据块
        """
        try:
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                yield f"data: {json.dumps({'error': parse_result.error}, ensure_ascii=False)}\n\n"
                return

            data = parse_result.data
            sections = self.extract_sections(data.get("content", ""), data.get("titles", []))

            target_content = data.get("content", "")
            target_title = parse_result.metadata.get("filename", "")

            if section_number:
                section = self._find_section(sections, section_number)
                if section:
                    target_content = section.content
                    target_title = f"{section.number}、{section.title}"
                else:
                    yield f"data: {json.dumps({'error': f'未找到章节: {section_number}'}, ensure_ascii=False)}\n\n"
                    return

            prompt = self._build_prompt(
                content=target_content,
                analysis_type=analysis_type,
                user_prompt=user_prompt,
                title=target_title
            )

            messages = [
                {"role": "system", "content": self._get_system_prompt(analysis_type)},
                {"role": "user", "content": prompt}
            ]

            # 发送初始元数据
            yield f"data: {json.dumps({
                'type': 'start',
                'filename': parse_result.metadata.get("filename", ""),
                'analysis_type': analysis_type,
                'section': target_title if section_number else None,
                'word_count': len(target_content)
            }, ensure_ascii=False)}\n\n"

            # 流式调用 LLM
            full_response = ""
            async for chunk in llm_service.chat_stream(messages, temperature=0.3, max_tokens=4000):
                content = chunk.get("content", "")
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'type': 'content', 'delta': content}, ensure_ascii=False)}\n\n"

            # 发送完成消息
            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Markdown AI 流式分析失败: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    def _find_section(self, sections: List[MarkdownSection], number: str) -> Optional[MarkdownSection]:
        """查找指定编号的章节"""
        # 标准化编号
        num = number.strip()
        for section in sections:
            if section.number == num or section.title == num:
                return section
            # 在子章节中查找
            found = self._find_section(section.subsections, number)
            if found:
                return found
        return None

    def _get_system_prompt(self, analysis_type: str) -> str:
        """根据分析类型获取系统提示词"""
        prompts = {
            "summary": "你是一个专业的文档摘要助手，擅长从长文档中提取核心信息。",
            "outline": "你是一个专业的文档结构分析助手，擅长提取文档大纲和层级结构。",
            "key_points": "你是一个专业的知识提取助手，擅长从文档中提取关键信息和要点。",
            "questions": "你是一个专业的教育助手，擅长生成帮助理解文档的问题。",
            "tags": "你是一个专业的标签生成助手，擅长提取文档的主题标签。",
            "qa": "你是一个专业的问答助手，擅长基于文档内容生成问答对。",
            "statistics": "你是一个专业的统计数据分析助手，擅长分析政府统计公报中的数据。",
            "section": "你是一个专业的章节分析助手，擅长对文档的特定章节进行深入分析。"
        }
        return prompts.get(analysis_type, "你是一个专业的文档分析助手。")

    def _build_prompt(
        self,
        content: str,
        analysis_type: str,
        user_prompt: str,
        title: str = ""
    ) -> str:
        """根据分析类型构建提示词"""

        # 截断内容避免超出 token 限制
        max_content_len = 6000
        if len(content) > max_content_len:
            content = content[:max_content_len] + "\n\n[内容已截断...]"

        base_prompts = {
            "summary": f"""请对以下文档进行摘要分析：

文档标题：{title}

文档内容：
{content}

请提供：
1. 文档主要内容摘要（300字以内）
2. 文档的目的和用途
3. 适合的读者群体

请用中文回答，结构清晰。""",

            "outline": f"""请提取以下文档的大纲结构：

文档标题：{title}

文档内容：
{content}

请按层级列出文档大纲，用缩进表示层级关系。
格式：
一、一级标题
   （一）二级标题
      1. 三级标题

请用中文回答。""",

            "key_points": f"""请从以下文档中提取关键要点：

文档标题：{title}

文档内容：
{content}

请列出文档的关键要点（5-10条），每条用简洁的语言描述，并说明其在文档中的重要性。

请用中文回答，格式清晰。""",

            "questions": f"""请根据以下文档生成有助于理解内容的问题：

文档标题：{title}

文档内容：
{content}

请生成5-10个问题，帮助读者更好地理解文档内容。每个问题应该：
1. 涵盖文档的重要信息点
2. 易于理解和回答
3. 具有思考价值

请用中文回答。""",

            "tags": f"""请为以下文档生成标签：

文档标题：{title}

文档内容：
{content[:3000]}

请生成5-8个标签，用逗号分隔。标签应该反映：
- 文档的主题领域
- 文档的类型
- 文档的关键特征

请用中文回答，只需输出标签，不要其他内容。""",

            "qa": f"""请根据以下文档生成问答对：

文档标题：{title}

文档内容：
{content[:4000]}

请生成3-5个问答对，帮助读者通过问答形式理解文档内容。
格式：
Q1: 问题
A1: 回答
Q2: 问题
A2: 回答

请用中文回答，内容准确。""",

            "statistics": f"""请分析以下政府统计公报中的数据和结论：

文档标题：{title}

文档内容：
{content}

请提供：
1. 文档中涉及的主要统计数据（列出关键数字和指标）
2. 数据的变化趋势（增长/下降）
3. 重要的百分比和对比
4. 数据来源和统计口径说明

请用中文回答，数据准确。""",

            "section": f"""请详细分析以下文档章节：

章节标题：{title}

章节内容：
{content}

请提供：
1. 章节主要内容概括
2. 关键信息和数据
3. 与其他部分的关联（如有）
4. 重要结论

请用中文回答，分析深入。"""
        }

        prompt = base_prompts.get(analysis_type, base_prompts["summary"])

        if user_prompt and user_prompt.strip():
            prompt += f"\n\n用户额外需求：{user_prompt}"

        return prompt

    async def extract_outline(self, file_path: str) -> Dict[str, Any]:
        """提取文档大纲"""
        try:
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                return {"success": False, "error": parse_result.error}

            data = parse_result.data
            sections = self.extract_sections(data.get("content", ""), data.get("titles", []))

            # 构建结构化大纲
            outline = []
            for section in sections:
                outline.append({
                    "number": section.number,
                    "title": section.title,
                    "level": section.level,
                    "line": section.line_start,
                    "content_preview": section.content[:100] + "..." if len(section.content) > 100 else section.content,
                    "subsections": [{
                        "number": s.number,
                        "title": s.title,
                        "level": s.level,
                        "line": s.line_start
                    } for s in section.subsections]
                })

            return {
                "success": True,
                "outline": outline
            }

        except Exception as e:
            logger.error(f"大纲提取失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def extract_tables_summary(self, file_path: str) -> Dict[str, Any]:
        """提取并总结文档中的表格"""
        try:
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                return {"success": False, "error": parse_result.error}

            tables = parse_result.data.get("tables", [])

            if not tables:
                return {"success": True, "tables": [], "message": "文档中没有表格"}

            # 提取每个表格的关键信息
            table_summaries = []
            for i, table in enumerate(tables):
                summary = {
                    "index": i + 1,
                    "headers": table.get("headers", []),
                    "row_count": table.get("row_count", 0),
                    "column_count": table.get("column_count", 0),
                    "preview_rows": table.get("rows", [])[:3],  # 只取前3行预览
                    "first_column": [row[0] if row else "" for row in table.get("rows", [])[:5]]
                }
                table_summaries.append(summary)

            return {
                "success": True,
                "tables": table_summaries,
                "table_count": len(tables)
            }

        except Exception as e:
            logger.error(f"表格提取失败: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
markdown_ai_service = MarkdownAIService()
