/**
 * 后端 FastAPI 调用封装
 * 基于大语言模型的文档理解与多源数据融合系统
 */

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000/api/v1';

// ==================== 类型定义 ====================

// 文档类型
export type DocumentType = 'docx' | 'xlsx' | 'md' | 'txt';

// 任务状态
export type TaskStatus = 'pending' | 'processing' | 'success' | 'failure';

// 解析选项
export interface DocumentUploadOptions {
  docType?: DocumentType;
  parseAllSheets?: boolean;
  sheetName?: string;
  headerRow?: number;
}

// 任务状态响应
export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  progress: number;
  message?: string;
  result?: any;
  error?: string;
}

// 文档元数据
export interface DocumentMetadata {
  doc_id?: string;
  filename?: string;
  original_filename?: string;
  extension?: string;
  file_size?: number;
  doc_type?: DocumentType;
  sheet_count?: number;
  sheet_names?: string[];
  row_count?: number;
  column_count?: number;
  columns?: string[];
  saved_path?: string;
  created_at?: string;
}

// 解析结果
export interface DocumentParseResult {
  success: boolean;
  data?: {
    columns?: string[];
    rows?: Record<string, any>[];
    row_count?: number;
    column_count?: number;
    sheets?: Record<string, any>;
    content?: string;  // 文本内容 (非结构化文档)
  };
  metadata?: DocumentMetadata;
  error?: string;
}

// 上传响应
export interface UploadResponse {
  task_id: string;
  file_count: number;
  message: string;
  status_url: string;
}

// 文档库项
export interface DocumentItem {
  doc_id: string;
  filename: string;
  original_filename: string;
  doc_type: DocumentType;
  file_size: number;
  created_at: string;
  metadata?: {
    row_count?: number;
    column_count?: number;
    columns?: string[];
  };
}

// 表格模板字段
export interface TemplateField {
  cell: string;
  name: string;
  field_type: string;
  required: boolean;
  hint?: string;
}

// 表格填写结果
export interface FillResult {
  success: boolean;
  filled_data: Record<string, any>;
  fill_details: Array<{
    field: string;
    value: any;
    source: string;
    confidence?: number;
  }>;
  source_doc_count?: number;
  error?: string;
}

// ==================== Excel 相关类型 (保留) ====================

export interface ExcelUploadOptions {
  parseAllSheets?: boolean;
  sheetName?: string;
  headerRow?: number;
}

export interface ExcelParseResult {
  success: boolean;
  data?: {
    columns?: string[];
    rows?: Record<string, any>[];
    row_count?: number;
    column_count?: number;
    sheets?: Record<string, any>;
  };
  error?: string;
  metadata?: {
    filename?: string;
    extension?: string;
    sheet_count?: number;
    sheet_names?: string[];
    row_count?: number;
    column_count?: number;
    columns?: string[];
    file_size?: number;
    saved_path?: string;
    original_filename?: string;
  };
}

export interface ExcelExportOptions {
  columns?: string[];
  sheetName?: string;
}

// ==================== AI 分析相关类型 ====================

export interface AIAnalyzeOptions {
  userPrompt?: string;
  analysisType?: 'general' | 'summary' | 'statistics' | 'insights';
  parseAllSheets?: boolean;
}

export interface ExcelData {
  columns?: string[];
  rows?: Record<string, any>[];
  row_count?: number;
  column_count?: number;
}

export interface AIAnalysisResult {
  success: boolean;
  analysis?: string;
  model?: string;
  analysisType?: string;
  error?: string;
}

// ==================== Markdown AI 分析类型 ====================

export interface AIMarkdownAnalyzeResult {
  success: boolean;
  filename?: string;
  analysis_type?: string;
  section?: string;
  word_count?: number;
  structure?: {
    title_count?: number;
    code_block_count?: number;
    table_count?: number;
    section_count?: number;
  };
  sections?: MarkdownSection[];
  analysis?: string;
  chart_data?: {
    tables?: Array<{
      description?: string;
      columns?: string[];
      rows?: string[][];
      visualization?: {
        statistics?: any;
        charts?: any;
        distributions?: any;
      };
    }>;
    key_statistics?: Array<{
      name?: string;
      value?: string;
      trend?: string;
      description?: string;
    }>;
    chart_suggestions?: Array<{
      chart_type?: string;
      title?: string;
      data_source?: string;
    }>;
  };
  error?: string;
}

export interface MarkdownSection {
  number: string;
  title: string;
  level: number;
  content_preview?: string;
  line_start: number;
  line_end?: number;
  subsections?: MarkdownSection[];
}

export interface MarkdownOutlineResult {
  success: boolean;
  outline?: MarkdownSection[];
  error?: string;
}

export type MarkdownAnalysisType = 'summary' | 'outline' | 'key_points' | 'questions' | 'tags' | 'qa' | 'statistics' | 'section' | 'charts';

export interface AIExcelAnalyzeResult {
  success: boolean;
  excel?: {
    data?: ExcelData;
    sheets?: Record<string, ExcelData>;
    metadata?: any;
    saved_path?: string;
  };
  analysis?: {
    analysis?: string;
    model?: string;
    analysisType?: string;
    is_template?: boolean;
    sheets?: Record<string, AIAnalysisResult>;
    total_sheets?: number;
    successful?: number;
    errors?: Record<string, string>;
  };
  error?: string;
}

// ==================== Word/TXT AI 分析类型 ====================

export type WordAnalysisType = 'structured' | 'charts';
export type TxtAnalysisType = 'structured' | 'charts';

export interface WordAIStructuredResult {
  success: boolean;
  result?: {
    success?: boolean;
    type?: string;
    headers?: string[];
    rows?: string[][];
    key_values?: Record<string, string>;
    list_items?: string[];
    summary?: string;
    error?: string;
  };
  error?: string;
}

export interface WordAIChartsResult {
  success: boolean;
  result?: {
    success?: boolean;
    charts?: {
      histograms?: Array<any>;
      bar_charts?: Array<any>;
      box_plots?: Array<any>;
      correlation?: any;
    };
    statistics?: {
      numeric?: Record<string, any>;
      categorical?: Record<string, any>;
    };
    distributions?: Record<string, any>;
    row_count?: number;
    column_count?: number;
    error?: string;
  };
  error?: string;
}

export interface TxtAIStructuredResult {
  success: boolean;
  result?: {
    success?: boolean;
    type?: string;
    tables?: Array<{
      headers?: string[];
      rows?: string[][];
    }>;
    key_values?: Record<string, string>;
    list_items?: string[];
    summary?: string;
    error?: string;
  };
  error?: string;
}

export interface TxtAIChartsResult {
  success: boolean;
  result?: {
    success?: boolean;
    charts?: {
      histograms?: Array<any>;
      bar_charts?: Array<any>;
      box_plots?: Array<any>;
      correlation?: any;
    };
    statistics?: {
      numeric?: Record<string, any>;
      categorical?: Record<string, any>;
    };
    distributions?: Record<string, any>;
    row_count?: number;
    column_count?: number;
    key_statistics?: Array<{
      name?: string;
      value?: string;
      trend?: string;
      description?: string;
    }>;
    chart_suggestions?: Array<{
      chart_type?: string;
      title?: string;
      data_source?: string;
    }>;
    error?: string;
  };
  error?: string;
}

// ==================== API 封装 ====================

export const backendApi = {

  // ==================== 健康检查 ====================

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{
    status: string;
    service: string;
    databases?: { mysql: string; mongodb: string; redis: string };
  }> {
    try {
      const response = await fetch(`${BACKEND_BASE_URL.replace('/api/v1', '')}/health`);
      if (!response.ok) throw new Error('健康检查失败');
      return await response.json();
    } catch (error) {
      console.error('健康检查失败:', error);
      throw error;
    }
  },

  // ==================== 文档上传与解析 ====================

  /**
   * 上传单个文档 (支持 docx/xlsx/md/txt)
   * 文件会存入 MySQL (结构化) 和 MongoDB (非结构化)，并建立 RAG 索引
   */
  async uploadDocument(
    file: File,
    options: DocumentUploadOptions = {}
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (options.docType) {
      params.append('doc_type', options.docType);
    }
    if (options.parseAllSheets === true) {
      params.append('parse_all_sheets', 'true');
    }
    if (options.sheetName) {
      params.append('sheet_name', options.sheetName);
    }
    if (options.headerRow !== undefined) {
      params.append('header_row', String(options.headerRow));
    }

    const url = `${BACKEND_BASE_URL}/upload/document?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传失败');
      }

      return await response.json();
    } catch (error) {
      console.error('上传文档失败:', error);
      throw error;
    }
  },

  /**
   * 批量上传文档
   */
  async uploadDocuments(
    files: File[],
    options: DocumentUploadOptions = {}
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const params = new URLSearchParams();
    if (options.docType) {
      params.append('doc_type', options.docType);
    }

    const url = `${BACKEND_BASE_URL}/upload/documents?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '批量上传失败');
      }

      return await response.json();
    } catch (error) {
      console.error('批量上传文档失败:', error);
      throw error;
    }
  },

  /**
   * 解析已上传的文档
   */
  async parseDocument(filePath: string): Promise<DocumentParseResult> {
    const url = `${BACKEND_BASE_URL}/upload/document/parse?file_path=${encodeURIComponent(filePath)}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '解析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('解析文档失败:', error);
      throw error;
    }
  },

  // ==================== 任务状态查询 ====================

  /**
   * 查询任务状态
   */
  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    const url = `${BACKEND_BASE_URL}/tasks/${taskId}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取任务状态失败');
      }
      return await response.json();
    } catch (error) {
      console.error('获取任务状态失败:', error);
      throw error;
    }
  },

  /**
   * 获取任务历史列表
   */
  async getTasks(
    limit: number = 50,
    skip: number = 0
  ): Promise<{ success: boolean; tasks: any[]; count: number }> {
    const url = `${BACKEND_BASE_URL}/tasks?limit=${limit}&skip=${skip}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取任务列表失败');
      }
      return await response.json();
    } catch (error) {
      console.error('获取任务列表失败:', error);
      throw error;
    }
  },

  /**
   * 删除任务
   */
  async deleteTask(taskId: string): Promise<{ success: boolean; deleted: boolean }> {
    const url = `${BACKEND_BASE_URL}/tasks/${taskId}`;

    try {
      const response = await fetch(url, {
        method: 'DELETE'
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '删除任务失败');
      }
      return await response.json();
    } catch (error) {
      console.error('删除任务失败:', error);
      throw error;
    }
  },

  /**
   * 轮询任务状态直到完成
   */
  async pollTaskStatus(
    taskId: string,
    onProgress?: (status: TaskStatusResponse) => void,
    interval: number = 2000,
    maxAttempts: number = 90  // 最多90秒 (比赛要求)
  ): Promise<TaskStatusResponse> {
    return new Promise((resolve, reject) => {
      let attempts = 0;

      const poll = async () => {
        try {
          const status = await backendApi.getTaskStatus(taskId);
          onProgress?.(status);

          if (status.status === 'success') {
            resolve(status);
            return;
          }

          if (status.status === 'failure') {
            reject(new Error(status.error || '任务失败'));
            return;
          }

          attempts++;
          if (attempts >= maxAttempts) {
            reject(new Error('任务超时'));
            return;
          }

          setTimeout(poll, interval);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  },

  // ==================== 文档库管理 ====================

  /**
   * 获取文档列表
   */
  async getDocuments(
    docType?: DocumentType,
    limit: number = 50
  ): Promise<{ success: boolean; documents: DocumentItem[] }> {
    const params = new URLSearchParams();
    if (docType) params.append('doc_type', docType);
    params.append('limit', String(limit));

    const url = `${BACKEND_BASE_URL}/documents?${params.toString()}`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取文档列表失败');
      return await response.json();
    } catch (error) {
      console.error('获取文档列表失败:', error);
      throw error;
    }
  },

  /**
   * 获取单个文档详情
   */
  async getDocument(docId: string): Promise<{
    success: boolean;
    document?: DocumentItem & { content?: string; structured_data?: any };
    error?: string;
  }> {
    const url = `${BACKEND_BASE_URL}/documents/${docId}`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取文档详情失败');
      return await response.json();
    } catch (error) {
      console.error('获取文档详情失败:', error);
      throw error;
    }
  },

  /**
   * 删除文档
   */
  async deleteDocument(docId: string): Promise<{ success: boolean; message: string }> {
    const url = `${BACKEND_BASE_URL}/documents/${docId}`;

    try {
      const response = await fetch(url, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '删除失败');
      }
      return await response.json();
    } catch (error) {
      console.error('删除文档失败:', error);
      throw error;
    }
  },

  // ==================== RAG 检索 ====================

  /**
   * 检索相关文档/字段
   */
  async searchRAG(
    query: string,
    topK: number = 5
  ): Promise<{
    success: boolean;
    results: Array<{
      content: string;
      metadata: Record<string, any>;
      score: number;
      doc_id: string;
    }>;
  }> {
    const url = `${BACKEND_BASE_URL}/rag/search`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '检索失败');
      }
      return await response.json();
    } catch (error) {
      console.error('RAG 检索失败:', error);
      throw error;
    }
  },

  /**
   * 获取 RAG 索引状态
   */
  async getRAGStatus(): Promise<{
    success: boolean;
    vector_count: number;
    collections: string[];
  }> {
    const url = `${BACKEND_BASE_URL}/rag/status`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取 RAG 状态失败');
      return await response.json();
    } catch (error) {
      console.error('获取 RAG 状态失败:', error);
      throw error;
    }
  },

  /**
   * 重建 RAG 索引
   */
  async rebuildRAGIndex(): Promise<{
    success: boolean;
    message: string;
  }> {
    const url = `${BACKEND_BASE_URL}/rag/rebuild`;

    try {
      const response = await fetch(url, {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '重建索引失败');
      }
      return await response.json();
    } catch (error) {
      console.error('重建 RAG 索引失败:', error);
      throw error;
    }
  },

  // ==================== 表格填写 ====================

  /**
   * 上传表格模板
   */
  async uploadTemplate(file: File): Promise<{
    success: boolean;
    template_id: string;
    fields: TemplateField[];
    sheets: string[];
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${BACKEND_BASE_URL}/templates/upload`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传模板失败');
      }
      return await response.json();
    } catch (error) {
      console.error('上传模板失败:', error);
      throw error;
    }
  },

  /**
   * 从已上传的模板提取字段定义
   */
  async extractTemplateFields(
    templateId: string,
    fileType: string = 'xlsx'
  ): Promise<{
    success: boolean;
    fields: TemplateField[];
  }> {
    const url = `${BACKEND_BASE_URL}/templates/fields`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          file_type: fileType,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '提取字段失败');
      }
      return await response.json();
    } catch (error) {
      console.error('提取字段失败:', error);
      throw error;
    }
  },

  /**
   * 联合上传模板和源文档
   */
  async uploadTemplateAndSources(
    templateFile: File,
    sourceFiles: File[]
  ): Promise<{
    success: boolean;
    template_id: string;
    filename: string;
    file_type: string;
    fields: TemplateField[];
    field_count: number;
    source_file_paths: string[];
    source_filenames: string[];
    task_id: string;
  }> {
    const formData = new FormData();
    formData.append('template_file', templateFile);
    sourceFiles.forEach(file => formData.append('source_files', file));

    const url = `${BACKEND_BASE_URL}/templates/upload-joint`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '联合上传失败');
      }
      return await response.json();
    } catch (error) {
      console.error('联合上传失败:', error);
      throw error;
    }
  },

  /**
   * 执行表格填写
   */
  async fillTemplate(
    templateId: string,
    templateFields: TemplateField[],
    sourceDocIds?: string[],
    sourceFilePaths?: string[],
    userHint?: string
  ): Promise<FillResult> {
    const url = `${BACKEND_BASE_URL}/templates/fill`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          template_fields: templateFields,
          source_doc_ids: sourceDocIds || [],
          source_file_paths: sourceFilePaths || [],
          user_hint: userHint || null,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '填写表格失败');
      }
      return await response.json();
    } catch (error) {
      console.error('填写表格失败:', error);
      throw error;
    }
  },

  /**
   * 导出填写后的表格
   */
  async exportFilledTemplate(
    templateId: string,
    filledData: Record<string, any>,
    format: 'xlsx' | 'docx' = 'xlsx',
    filledFilePath?: string
  ): Promise<Blob> {
    const url = `${BACKEND_BASE_URL}/templates/export`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          filled_data: filledData,
          format,
          ...(filledFilePath && { filled_file_path: filledFilePath }),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '导出失败');
      }
      return await response.blob();
    } catch (error) {
      console.error('导出表格失败:', error);
      throw error;
    }
  },

  /**
   * 填充原始模板并导出
   *
   * 直接打开原始模板文件，将数据填入模板的表格/单元格中，然后导出
   * 适用于比赛场景：保持原始模板格式不变
   */
  async fillAndExportTemplate(
    templatePath: string,
    filledData: Record<string, any>,
    format: 'xlsx' | 'docx' = 'xlsx'
  ): Promise<Blob> {
    const url = `${BACKEND_BASE_URL}/templates/fill-and-export`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_path: templatePath,
          filled_data: filledData,
          format,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '填充模板失败');
      }
      return await response.blob();
    } catch (error) {
      console.error('填充模板失败:', error);
      throw error;
    }
  },

  // ==================== Excel 专用接口 (保留兼容) ====================

  /**
   * 上传并解析 Excel 文件
   */
  async uploadExcel(
    file: File,
    options: ExcelUploadOptions = {}
  ): Promise<ExcelParseResult> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (options.parseAllSheets === true) {
      params.append('parse_all_sheets', 'true');
    }
    if (options.sheetName) {
      params.append('sheet_name', options.sheetName);
    }
    if (options.headerRow !== undefined) {
      params.append('header_row', String(options.headerRow));
    }

    const url = `${BACKEND_BASE_URL}/upload/excel?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传失败');
      }

      return await response.json();
    } catch (error) {
      console.error('上传 Excel 文件失败:', error);
      throw error;
    }
  },

  /**
   * 导出 Excel 文件
   */
  async exportExcel(
    filePath: string,
    options: ExcelExportOptions = {}
  ): Promise<Blob> {
    const params = new URLSearchParams();
    if (options.sheetName) {
      params.append('sheet_name', options.sheetName);
    }
    if (options.columns && options.columns.length > 0) {
      params.append('columns', options.columns.join(','));
    }

    const url = `${BACKEND_BASE_URL}/upload/excel/export/${encodeURIComponent(filePath)}?${params.toString()}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '导出失败');
      }
      return await response.blob();
    } catch (error) {
      console.error('导出 Excel 文件失败:', error);
      throw error;
    }
  },

  /**
   * 获取 Excel 文件预览
   */
  async getExcelPreview(
    filePath: string,
    sheetName?: string,
    maxRows: number = 10
  ): Promise<ExcelParseResult> {
    const params = new URLSearchParams();
    if (sheetName !== undefined) {
      params.append('sheet_name', sheetName);
    }
    params.append('max_rows', String(maxRows));

    const url = `${BACKEND_BASE_URL}/upload/excel/preview/${encodeURIComponent(filePath)}?${params.toString()}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取预览失败');
      }
      return await response.json();
    } catch (error) {
      console.error('获取预览失败:', error);
      throw error;
    }
  },

  /**
   * 删除已上传的文件
   */
  async deleteUploadedFile(filePath: string): Promise<{ success: boolean; message: string }> {
    const url = `${BACKEND_BASE_URL}/upload/file?file_path=${encodeURIComponent(filePath)}`;

    try {
      const response = await fetch(url, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '删除失败');
      }
      return await response.json();
    } catch (error) {
      console.error('删除文件失败:', error);
      throw error;
    }
  },

  // ==================== 智能指令 API ====================

  /**
   * 智能对话（支持多轮对话的指令执行）
   */
  async instructionChat(
    instruction: string,
    docIds?: string[],
    context?: Record<string, any>
  ): Promise<{
    success: boolean;
    intent: string;
    result: Record<string, any>;
    message: string;
    hint?: string;
  }> {
    const url = `${BACKEND_BASE_URL}/instruction/chat`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, doc_ids: docIds, context }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '对话处理失败');
      }

      return await response.json();
    } catch (error) {
      console.error('对话处理失败:', error);
      throw error;
    }
  },

  /**
   * 获取支持的指令类型列表
   */
  async getSupportedIntents(): Promise<{
    intents: Array<{
      intent: string;
      name: string;
      examples: string[];
      params: string[];
    }>;
  }> {
    const url = `${BACKEND_BASE_URL}/instruction/intents`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取指令列表失败');
      return await response.json();
    } catch (error) {
      console.error('获取指令列表失败:', error);
      throw error;
    }
  },

  /**
   * 执行指令（同步模式）
   */
  async executeInstruction(
    instruction: string,
    docIds?: string[],
    context?: Record<string, any>
  ): Promise<{
    success: boolean;
    intent: string;
    result: Record<string, any>;
    message: string;
  }> {
    const url = `${BACKEND_BASE_URL}/instruction/execute`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, doc_ids: docIds, context }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '指令执行失败');
      }

      return await response.json();
    } catch (error) {
      console.error('指令执行失败:', error);
      throw error;
    }
  },

};

// ==================== AI 分析 API ====================

export interface AIChartRequest {
  analysis_text: string;
  original_filename?: string;
  file_type?: string;
}

export interface VisualizationResult {
  success: boolean;
  statistics?: {
    numeric?: Record<string, any>;
    categorical?: Record<string, any>;
  };
  charts?: {
    histograms?: Array<any>;
    bar_charts?: Array<any>;
    box_plots?: Array<any>;
    correlation?: any;
  };
  distributions?: Record<string, any>;
  row_count?: number;
  column_count?: number;
  error?: string;
}

export const aiApi = {

  /**
   * 上传并使用 AI 分析 Excel 文件
   */
  async analyzeExcel(
    file: File | null,
    options: AIAnalyzeOptions = {},
    docId: string | null = null
  ): Promise<AIExcelAnalyzeResult> {
    const formData = new FormData();

    if (docId) {
      formData.append('doc_id', docId);
    } else if (file) {
      formData.append('file', file);
    } else {
      throw new Error('必须提供文件或文档ID');
    }

    const params = new URLSearchParams();
    if (options.userPrompt) {
      params.append('user_prompt', options.userPrompt);
    }
    if (options.analysisType) {
      params.append('analysis_type', options.analysisType);
    }
    if (options.parseAllSheets === true) {
      params.append('parse_all_sheets', 'true');
    }

    const url = `${BACKEND_BASE_URL}/ai/analyze/excel?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'AI 分析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('AI 分析失败:', error);
      throw error;
    }
  },

  /**
   * 对已解析的 Excel 数据进行 AI 分析
   */
  async analyzeText(
    excelData: ExcelData,
    userPrompt: string = '',
    analysisType: string = 'general'
  ): Promise<AIAnalysisResult> {
    const url = `${BACKEND_BASE_URL}/ai/analyze/text`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excel_data: excelData,
          user_prompt: userPrompt,
          analysis_type: analysisType,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '文本分析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('文本分析失败:', error);
      throw error;
    }
  },

  /**
   * 获取支持的分析类型
   */
  async getAnalysisTypes(): Promise<{
    types: Array<{ value: string; label: string; description: string }>;
  }> {
    const url = `${BACKEND_BASE_URL}/ai/analysis/types`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取分析类型失败');
      const data = await response.json();
      // 转换后端返回格式 {excel_types: [], markdown_types: []} 为前端期望的 {types: []}
      return { types: data.excel_types || [] };
    } catch (error) {
      console.error('获取分析类型失败:', error);
      throw error;
    }
  },

  /**
   * 上传并使用 AI 分析 Markdown 文件
   */
  async analyzeMarkdown(
    file: File | null,
    options: {
      docId?: string;
      analysisType?: MarkdownAnalysisType;
      userPrompt?: string;
      sectionNumber?: string;
    } = {}
  ): Promise<AIMarkdownAnalyzeResult> {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (options.docId) {
      formData.append('doc_id', options.docId);
    }

    const params = new URLSearchParams();
    if (options.analysisType) {
      params.append('analysis_type', options.analysisType);
    }
    if (options.userPrompt) {
      params.append('user_prompt', options.userPrompt);
    }
    if (options.sectionNumber) {
      params.append('section_number', options.sectionNumber);
    }

    const url = `${BACKEND_BASE_URL}/ai/analyze/md?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Markdown AI 分析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Markdown AI 分析失败:', error);
      throw error;
    }
  },

  /**
   * 流式分析 Markdown 文件 (SSE)
   */
  async analyzeMarkdownStream(
    file: File,
    options: {
      analysisType?: MarkdownAnalysisType;
      userPrompt?: string;
      sectionNumber?: string;
    } = {},
    onChunk?: (chunk: { type: string; delta?: string; error?: string }) => void
  ): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (options.analysisType) {
      params.append('analysis_type', options.analysisType);
    }
    if (options.userPrompt) {
      params.append('user_prompt', options.userPrompt);
    }
    if (options.sectionNumber) {
      params.append('section_number', options.sectionNumber);
    }

    const url = `${BACKEND_BASE_URL}/ai/analyze/md/stream?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Markdown AI 流式分析失败');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('无法读取响应流');

      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'content' && parsed.delta) {
                fullResponse += parsed.delta;
                onChunk?.({ type: 'content', delta: parsed.delta });
              } else if (parsed.type === 'done') {
                fullResponse = parsed.full_response || fullResponse;
              } else if (parsed.error) {
                onChunk?.({ type: 'error', error: parsed.error });
              }
            } catch {
              // Ignore parse errors for incomplete JSON
            }
          }
        }
      }

      return fullResponse;
    } catch (error) {
      console.error('Markdown AI 流式分析失败:', error);
      throw error;
    }
  },

  /**
   * 获取 Markdown 文档大纲（分章节信息）
   */
  async getMarkdownOutline(file: File): Promise<MarkdownOutlineResult> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${BACKEND_BASE_URL}/ai/analyze/md/outline`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取 Markdown 大纲失败');
      }

      return await response.json();
    } catch (error) {
      console.error('获取 Markdown 大纲失败:', error);
      throw error;
    }
  },

  /**
   * 上传并使用 AI 分析 TXT 文本文件，提取结构化数据或生成图表
   */
  async analyzeTxt(
    file: File | null,
    docId: string | null = null,
    analysisType: TxtAnalysisType = 'structured'
  ): Promise<{
    success: boolean;
    filename?: string;
    analysis_type?: string;
    result?: any;
    error?: string;
  }> {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (docId) {
      formData.append('doc_id', docId);
    }

    const params = new URLSearchParams();
    params.append('analysis_type', analysisType);

    const url = `${BACKEND_BASE_URL}/ai/analyze/txt?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'TXT AI 分析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('TXT AI 分析失败:', error);
      throw error;
    }
  },

  /**
   * 生成统计信息和图表
   */
  async generateStatistics(
    excelData: ExcelData,
    analysisType: string = 'statistics'
  ): Promise<VisualizationResult> {
    const url = `${BACKEND_BASE_URL}/visualization/statistics`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excel_data: excelData,
          analysis_type: analysisType
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '生成图表失败');
      }

      return await response.json();
    } catch (error) {
      console.error('生成图表失败:', error);
      throw error;
    }
  },

  /**
   * 获取支持的图表类型
   */
  async getChartTypes(): Promise<{
    chart_types: Array<{ value: string; label: string; description: string }>;
  }> {
    const url = `${BACKEND_BASE_URL}/visualization/chart-types`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取图表类型失败');
      return await response.json();
    } catch (error) {
      console.error('获取图表类型失败:', error);
      throw error;
    }
  },

  /**
   * 从 AI 分析结果中提取数据并生成图表
   */
  async extractAndGenerateCharts(request: AIChartRequest) {
    const url = `${BACKEND_BASE_URL}/analysis/extract-and-chart`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '生成图表失败');
      }

      return await response.json();
    } catch (error) {
      console.error('生成分析结果图表失败:', error);
      throw error;
    }
  },

  /**
   * 仅提取结构化数据（调试用）
   */
  async analyzeTextOnly(request: AIChartRequest) {
    const url = `${BACKEND_BASE_URL}/analysis/analyze-text`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '分析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('分析文本失败:', error);
      throw error;
    }
  },

  // ==================== Word AI 解析 ====================

  /**
   * 使用 AI 解析 Word 文档，提取结构化数据或生成图表
   */
  async analyzeWordWithAI(
    file: File | null,
    docId: string | null = null,
    userHint: string = '',
    analysisType: WordAnalysisType = 'structured'
  ): Promise<{
    success: boolean;
    filename?: string;
    analysis_type?: string;
    result?: any;
    error?: string;
  }> {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (docId) {
      formData.append('doc_id', docId);
    }
    if (userHint) {
      formData.append('user_hint', userHint);
    }

    const params = new URLSearchParams();
    params.append('analysis_type', analysisType);

    const url = `${BACKEND_BASE_URL}/ai/analyze/word?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Word AI 解析失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Word AI 解析失败:', error);
      throw error;
    }
  },

  /**
   * 使用 AI 解析 Word 文档并填写模板
   * 一次性完成：AI解析 + 填表
   */
  async fillTemplateFromWordAI(
    file: File,
    templateFields: TemplateField[],
    userHint: string = ''
  ): Promise<FillResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_fields', JSON.stringify(templateFields));
    if (userHint) {
      formData.append('user_hint', userHint);
    }

    const url = `${BACKEND_BASE_URL}/ai/analyze/word/fill-template`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Word AI 填表失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Word AI 填表失败:', error);
      throw error;
    }
  },

  // ==================== 智能指令 ====================

  /**
   * 识别自然语言指令的意图
   */
  async recognizeIntent(
    instruction: string,
    docIds?: string[]
  ): Promise<{
    success: boolean;
    intent: string;
    params: Record<string, any>;
    message: string;
  }> {
    const url = `${BACKEND_BASE_URL}/instruction/recognize`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, doc_ids: docIds }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '意图识别失败');
      }

      return await response.json();
    } catch (error) {
      console.error('意图识别失败:', error);
      throw error;
    }
  },

  /**
   * 执行自然语言指令
   */
  async executeInstruction(
    instruction: string,
    docIds?: string[],
    context?: Record<string, any>
  ): Promise<{
    success: boolean;
    intent: string;
    result: Record<string, any>;
    message: string;
  }> {
    const url = `${BACKEND_BASE_URL}/instruction/execute`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, doc_ids: docIds, context }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '指令执行失败');
      }

      return await response.json();
    } catch (error) {
      console.error('指令执行失败:', error);
      throw error;
    }
  },

  // ==================== 对话历史 API ====================

  /**
   * 获取对话历史
   */
  async getConversationHistory(conversationId: string, limit: number = 20): Promise<{
    success: boolean;
    messages: Array<{
      role: string;
      content: string;
      intent?: string;
      created_at: string;
    }>;
  }> {
    const url = `${BACKEND_BASE_URL}/conversation/${conversationId}/history?limit=${limit}`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取对话历史失败');
      return await response.json();
    } catch (error) {
      console.error('获取对话历史失败:', error);
      return { success: false, messages: [] };
    }
  },

  /**
   * 删除对话历史
   */
  async deleteConversation(conversationId: string): Promise<{
    success: boolean;
  }> {
    const url = `${BACKEND_BASE_URL}/conversation/${conversationId}`;

    try {
      const response = await fetch(url, { method: 'DELETE' });
      if (!response.ok) throw new Error('删除对话历史失败');
      return await response.json();
    } catch (error) {
      console.error('删除对话历史失败:', error);
      return { success: false };
    }
  },

  /**
   * 获取会话列表
   */
  async listConversations(limit: number = 50): Promise<{
    success: boolean;
    conversations: Array<any>;
  }> {
    const url = `${BACKEND_BASE_URL}/conversation/all?limit=${limit}`;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('获取会话列表失败');
      return await response.json();
    } catch (error) {
      console.error('获取会话列表失败:', error);
      return { success: false, conversations: [] };
    }
  }
};
