# 模板填表功能变更日志

**变更日期**: 2026-04-08
**变更类型**: 功能完善
**变更内容**: Word 表格解析和模板填表功能

---

## 变更概述

本次变更完善了 Word 表格解析、表格模板构建和填写功能，实现了从源文档（MongoDB/文件）读取数据并智能填表的核心流程。

### 涉及文件

| 文件 | 变更行数 | 说明 |
|------|----------|------|
| backend/app/api/endpoints/templates.py | +156 | API 端点完善，添加 Word 导出 |
| backend/app/core/document_parser/docx_parser.py | +130 | Word 表格解析增强 |
| backend/app/services/template_fill_service.py | +340 | 核心填表服务重写 |
| frontend/src/db/backend-api.ts | +9 | 前端 API 更新 |
| frontend/src/pages/TemplateFill.tsx | +8 | 前端页面更新 |
| 比赛备赛规划.md | +169 | 文档更新 |

---

## 详细变更

### 1. backend/app/core/document_parser/docx_parser.py

**新增方法**:

- `parse_tables_for_template(file_path)` - 解析 Word 文档中的表格，提取模板字段
- `extract_template_fields_from_docx(file_path)` - 从 Word 文档提取模板字段定义
- `_infer_field_type_from_hint(hint)` - 从提示词推断字段类型

**功能说明**:
- 专门用于比赛场景：解析表格模板，识别需要填写的字段
- 支持从表格第一列提取字段名，第二列提取提示词/描述
- 自动推断字段类型（text/number/date）

### 2. backend/app/services/template_fill_service.py

**重构内容**:

- 不再依赖 RAG 服务，直接从 MongoDB 或文件读取源文档
- 新增 `SourceDocument` 数据类
- 完善 `fill_template()` 方法，支持 `source_doc_ids` 和 `source_file_paths`
- 新增 `_load_source_documents()` - 加载源文档内容
- 新增 `_extract_field_value()` - 使用 LLM 提取字段值
- 新增 `_build_context_text()` - 构建上下文（优先使用表格数据）
- 完善 `_get_template_fields_from_docx()` - Word 模板字段提取

**核心流程**:
```
1. 加载源文档（MongoDB 或文件）
2. 对每个字段调用 LLM 提取值
3. 返回填写结果
```

### 3. backend/app/api/endpoints/templates.py

**新增内容**:

- `FillRequest` 添加 `source_doc_ids`, `source_file_paths`, `user_hint` 字段
- `ExportRequest` 添加 `format` 字段
- `_export_to_word()` - 导出为 Word 格式
- `/templates/export/excel` - 专门导出 Excel
- `/templates/export/word` - 专门导出 Word

### 4. frontend/src/db/backend-api.ts

**更新内容**:

- `TemplateField` 接口添加 `hint` 字段
- `fillTemplate()` 方法添加 `sourceDocIds`, `sourceFilePaths`, `userHint` 参数

### 5. frontend/src/pages/TemplateFill.tsx

**更新内容**:

- `handleFillTemplate()` 传递 `selectedDocs` 作为 `sourceDocIds` 参数

---

## API 接口变更

### POST /api/v1/templates/fill

**请求体**:
```json
{
  "template_id": "模板ID",
  "template_fields": [
    {
      "cell": "A1",
      "name": "姓名",
      "field_type": "text",
      "required": true,
      "hint": "提取人员姓名"
    }
  ],
  "source_doc_ids": ["mongodb_doc_id"],
  "source_file_paths": [],
  "user_hint": "请从xxx文档中提取"
}
```

**响应**:
```json
{
  "success": true,
  "filled_data": {"姓名": "张三"},
  "fill_details": [...],
  "source_doc_count": 1
}
```

### POST /api/v1/templates/export

**新增支持 format=dicx**，可导出为 Word 格式

---

## 技术细节

### 字段类型推断

| 关键词 | 推断类型 |
|--------|----------|
| 年、月、日、日期、时间、出生 | date |
| 数量、金额、比率、%、率、合计 | number |
| 其他 | text |

### 上下文构建

源文档内容构建优先级：
1. 结构化数据（表格数据）
2. 原始文本内容（限制 5000 字符）

---

## 相关文档

- [比赛备赛规划.md](../比赛备赛规划.md) - 已更新功能状态和技术实现细节
