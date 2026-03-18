/**
 * 后端 FastAPI 调用封装
 */

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000/api/v1';

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

export const backendApi = {
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
    // 只在显式设置为 true 时才发送参数，避免发送 "false" 字符串
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
   * 导出 Excel 文件（基于原始解析结果，选择列导出）
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

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string; service: string }> {
    try {
      const response = await fetch(`${BACKEND_BASE_URL.replace('/api/v1', '')}/health`);
      if (!response.ok) throw new Error('健康检查失败');
      return await response.json();
    } catch (error) {
      console.error('健康检查失败:', error);
      throw error;
    }
  }
};

/**
 * AI 分析相关的 API 调用
 */
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
    // 只在显式设置为 true 时才发送参数
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
        headers: {
          'Content-Type': 'application/json',
        },
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
    types: Array<{
      value: string;
      label: string;
      description: string;
    }>;
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
  }
};

/**
 * 可视化相关的 API 调用
 */
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
    correlation?: any;  // 修复：后端返回的是 correlation，不是 relation
  };
  distributions?: Record<string, any>;
  row_count?: number;
  column_count?: number;
  error?: string;
}

export const visualizationApi = {
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
        headers: {
          'Content-Type': 'application/json',
        },
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
    chart_types: Array<{
      value: string;
      label: string;
      description: string;
    }>;
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
  }
};

/**
 * 分析结果图表 API - 根据 AI 分析结果生成图表
 */

export interface AnalysisChartRequest {
  analysis_text: string;
  original_filename?: string;
  file_type?: string;
}

export interface AnalysisChartResult {
  success: boolean;
  charts?: {
    numeric_charts?: Array<{
      type: string;
      title: string;
      image: string;
      data: Array<{ name: string; value: number }>;
    }>;
    categorical_charts?: Array<{
      type: string;
      title: string;
      image: string;
      data: Array<{ name: string; count: number }>;
    }>;
    time_series_chart?: {
      type: string;
      title: string;
      image: string;
      data: Array<{ name: string; value: number }>;
    };
    comparison_chart?: {
      type: string;
      title: string;
      image: string;
      data: Array<{ name: string; value: number }>;
    };
    table_preview?: {
      columns: string[];
      rows: any[];
      total_rows: number;
      preview_rows: number;
    };
  };
  statistics?: {
    numeric_summary?: {
      count: number;
      sum: number;
      mean: number;
      median: number;
      min: number;
      max: number;
      std: number;
    };
  };
  metadata?: {
    total_items?: number;
    data_types?: string[];
  };
  data_source?: string;
  error?: string;
}

export const analysisChartsApi = {
  /**
   * 从 AI 分析结果中提取数据并生成图表
   */
  async extractAndGenerateCharts(request: AnalysisChartRequest): Promise<AnalysisChartResult> {
    const url = `${BACKEND_BASE_URL}/analysis/extract-and-chart`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
  async analyzeTextOnly(request: AnalysisChartRequest) {
    const url = `${BACKEND_BASE_URL}/analysis/analyze-text`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
  }
};
