"""
智能指令 API 接口

支持自然语言指令解析和执行
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.instruction.intent_parser import intent_parser
from app.instruction.executor import instruction_executor
from app.core.database import mongodb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instruction", tags=["智能指令"])


# ==================== 请求/响应模型 ====================

class InstructionRequest(BaseModel):
    instruction: str
    doc_ids: Optional[List[str]] = None  # 关联的文档 ID 列表
    context: Optional[Dict[str, Any]] = None  # 额外上下文


class IntentRecognitionResponse(BaseModel):
    success: bool
    intent: str
    params: Dict[str, Any]
    message: str


class InstructionExecutionResponse(BaseModel):
    success: bool
    intent: str
    result: Dict[str, Any]
    message: str


# ==================== 接口 ====================

@router.post("/recognize", response_model=IntentRecognitionResponse)
async def recognize_intent(request: InstructionRequest):
    """
    意图识别接口

    将自然语言指令解析为结构化的意图和参数

    示例指令:
    - "提取文档中的医院数量和床位数"
    - "根据这些数据填表"
    - "总结一下这份文档"
    - "对比这两个文档的差异"
    """
    try:
        intent, params = await intent_parser.parse(request.instruction)

        # 添加文档关联信息
        if request.doc_ids:
            params["document_refs"] = [f"doc_{doc_id}" for doc_id in request.doc_ids]

        intent_names = {
            "extract": "信息提取",
            "fill_table": "表格填写",
            "summarize": "摘要总结",
            "question": "智能问答",
            "search": "文档搜索",
            "compare": "对比分析",
            "transform": "格式转换",
            "edit": "文档编辑",
            "unknown": "未知"
        }

        return IntentRecognitionResponse(
            success=True,
            intent=intent,
            params=params,
            message=f"识别到意图: {intent_names.get(intent, intent)}"
        )

    except Exception as e:
        logger.error(f"意图识别失败: {e}")
        return IntentRecognitionResponse(
            success=False,
            intent="error",
            params={},
            message=f"意图识别失败: {str(e)}"
        )


@router.post("/execute")
async def execute_instruction(
    background_tasks: BackgroundTasks,
    request: InstructionRequest,
    async_execute: bool = Query(False, description="是否异步执行（仅返回任务ID）")
):
    """
    指令执行接口

    解析并执行自然语言指令

    示例:
    - 指令: "提取文档1中的医院数量"
      返回: {"extracted_data": {"医院数量": ["38710个"]}}

    - 指令: "填表"
      返回: {"filled_data": {...}}

    设置 async_execute=true 可异步执行，返回任务ID用于查询进度
    """
    task_id = str(uuid.uuid4())

    if async_execute:
        # 异步模式：立即返回任务ID，后台执行
        background_tasks.add_task(
            _execute_instruction_task,
            task_id=task_id,
            instruction=request.instruction,
            doc_ids=request.doc_ids,
            context=request.context
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "指令已提交执行",
            "status_url": f"/api/v1/tasks/{task_id}"
        }

    # 同步模式：等待执行完成
    return await _execute_instruction_task(task_id, request.instruction, request.doc_ids, request.context)


async def _execute_instruction_task(
    task_id: str,
    instruction: str,
    doc_ids: Optional[List[str]],
    context: Optional[Dict[str, Any]]
) -> InstructionExecutionResponse:
    """执行指令的后台任务"""
    from app.core.database import redis_db, mongodb as mongo_client

    try:
        # 记录任务
        try:
            await mongo_client.insert_task(
                task_id=task_id,
                task_type="instruction_execute",
                status="processing",
                message="正在执行指令"
            )
        except Exception:
            pass

        # 构建执行上下文
        ctx: Dict[str, Any] = context or {}

        # 如果提供了文档 ID，获取文档内容
        if doc_ids:
            docs = []
            for doc_id in doc_ids:
                doc = await mongo_client.get_document(doc_id)
                if doc:
                    docs.append(doc)

            if docs:
                ctx["source_docs"] = docs
                logger.info(f"指令执行上下文: 关联了 {len(docs)} 个文档")

        # 执行指令
        result = await instruction_executor.execute(instruction, ctx)

        # 更新任务状态
        try:
            await mongo_client.update_task(
                task_id=task_id,
                status="success",
                message="执行完成",
                result=result
            )
        except Exception:
            pass

        return InstructionExecutionResponse(
            success=result.get("success", False),
            intent=result.get("intent", "unknown"),
            result=result,
            message=result.get("message", "执行完成")
        )

    except Exception as e:
        logger.error(f"指令执行失败: {e}")
        try:
            await mongo_client.update_task(
                task_id=task_id,
                status="failure",
                message="执行失败",
                error=str(e)
            )
        except Exception:
            pass

        return InstructionExecutionResponse(
            success=False,
            intent="error",
            result={"error": str(e)},
            message=f"指令执行失败: {str(e)}"
        )


@router.post("/chat")
async def instruction_chat(
    background_tasks: BackgroundTasks,
    request: InstructionRequest,
    async_execute: bool = Query(False, description="是否异步执行（仅返回任务ID）")
):
    """
    指令对话接口

    支持多轮对话的指令执行

    示例对话流程:
    1. 用户: "上传一些文档"
    2. 系统: "请上传文档"
    3. 用户: "提取其中的医院数量"
    4. 系统: 返回提取结果

    设置 async_execute=true 可异步执行，返回任务ID用于查询进度
    """
    task_id = str(uuid.uuid4())

    if async_execute:
        # 异步模式：立即返回任务ID，后台执行
        background_tasks.add_task(
            _execute_chat_task,
            task_id=task_id,
            instruction=request.instruction,
            doc_ids=request.doc_ids,
            context=request.context
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "指令已提交执行",
            "status_url": f"/api/v1/tasks/{task_id}"
        }

    # 同步模式：等待执行完成
    return await _execute_chat_task(task_id, request.instruction, request.doc_ids, request.context)


async def _execute_chat_task(
    task_id: str,
    instruction: str,
    doc_ids: Optional[List[str]],
    context: Optional[Dict[str, Any]]
):
    """执行指令对话的后台任务"""
    from app.core.database import mongodb as mongo_client

    try:
        # 记录任务
        try:
            await mongo_client.insert_task(
                task_id=task_id,
                task_type="instruction_chat",
                status="processing",
                message="正在处理对话"
            )
        except Exception:
            pass

        # 构建上下文
        ctx: Dict[str, Any] = context or {}

        # 获取关联文档
        if doc_ids:
            docs = []
            for doc_id in doc_ids:
                doc = await mongo_client.get_document(doc_id)
                if doc:
                    docs.append(doc)
            if docs:
                ctx["source_docs"] = docs

        # 执行指令
        result = await instruction_executor.execute(instruction, ctx)

        # 根据意图类型添加友好的响应消息
        response_messages = {
            "extract": f"已提取 {len(result.get('extracted_data', {}))} 个字段的数据",
            "fill_table": f"填表完成，填写了 {len(result.get('result', {}).get('filled_data', {}))} 个字段",
            "summarize": "已生成文档摘要",
            "question": "已找到相关答案",
            "search": f"找到 {len(result.get('results', []))} 条相关内容",
            "compare": f"对比了 {len(result.get('comparison', []))} 个文档",
            "edit": "编辑操作已完成",
            "transform": "格式转换已完成",
            "unknown": "无法理解该指令，请尝试更明确的描述"
        }

        response = {
            "success": result.get("success", False),
            "intent": result.get("intent", "unknown"),
            "result": result,
            "message": response_messages.get(result.get("intent", ""), result.get("message", "")),
            "hint": _get_intent_hint(result.get("intent", ""))
        }

        # 更新任务状态
        try:
            await mongo_client.update_task(
                task_id=task_id,
                status="success",
                message="处理完成",
                result=response
            )
        except Exception:
            pass

        return response

    except Exception as e:
        logger.error(f"指令对话失败: {e}")
        try:
            await mongo_client.update_task(
                task_id=task_id,
                status="failure",
                message="处理失败",
                error=str(e)
            )
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e),
            "message": f"处理失败: {str(e)}"
        }


def _get_intent_hint(intent: str) -> Optional[str]:
    """根据意图返回下一步提示"""
    hints = {
        "extract": "您可以继续说 '提取更多字段' 或 '将数据填入表格'",
        "fill_table": "您可以提供表格模板或说 '帮我创建一个表格'",
        "question": "您可以继续提问或说 '总结一下这些内容'",
        "search": "您可以查看搜索结果或说 '对比这些内容'",
        "unknown": "您可以尝试: '提取数据'、'填表'、'总结'、'问答' 等指令"
    }
    return hints.get(intent)


@router.get("/intents")
async def list_supported_intents():
    """
    获取支持的意图类型列表

    返回所有可用的自然语言指令类型
    """
    return {
        "intents": [
            {
                "intent": "extract",
                "name": "信息提取",
                "examples": [
                    "提取文档中的医院数量",
                    "抽取所有机构的名称",
                    "找出表格中的数据"
                ],
                "params": ["field_refs", "document_refs"]
            },
            {
                "intent": "fill_table",
                "name": "表格填写",
                "examples": [
                    "填表",
                    "根据这些数据填写表格",
                    "帮我填到Excel里"
                ],
                "params": ["template", "document_refs"]
            },
            {
                "intent": "summarize",
                "name": "摘要总结",
                "examples": [
                    "总结一下这份文档",
                    "生成摘要",
                    "概括主要内容"
                ],
                "params": ["document_refs"]
            },
            {
                "intent": "question",
                "name": "智能问答",
                "examples": [
                    "这段话说的是什么？",
                    "有多少家医院？",
                    "解释一下这个概念"
                ],
                "params": ["question", "focus"]
            },
            {
                "intent": "search",
                "name": "文档搜索",
                "examples": [
                    "搜索相关内容",
                    "找找看有哪些机构",
                    "查询医院相关的数据"
                ],
                "params": ["field_refs", "question"]
            },
            {
                "intent": "compare",
                "name": "对比分析",
                "examples": [
                    "对比这两个文档",
                    "比较一下差异",
                    "找出不同点"
                ],
                "params": ["document_refs"]
            },
            {
                "intent": "edit",
                "name": "文档编辑",
                "examples": [
                    "润色这段文字",
                    "修改格式",
                    "添加注释"
                ],
                "params": []
            }
        ]
    }
