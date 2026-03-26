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
}

// 表格填写结果
export interface FillResult {
  success: boolean;
  filled_data: Record<string, any>;
  fill_details: Array<{
    field: string;
    value: any;
    source: string;
  }>;
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
   * 执行表格填写
   */
  async fillTemplate(
    templateId: string,
    templateFields: TemplateField[]
  ): Promise<FillResult> {
    const url = `${BACKEND_BASE_URL}/templates/fill`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          template_fields: templateFields,
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
    format: 'xlsx' | 'docx' = 'xlsx'
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
    file: File,
    options: AIAnalyzeOptions = {}
  ): Promise<AIExcelAnalyzeResult> {
    const formData = new FormData();
    formData.append('file', file);

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
      return await response.json();
    } catch (error) {
      console.error('获取分析类型失败:', error);
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
};
