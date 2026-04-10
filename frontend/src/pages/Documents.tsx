import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  FileText,
  Upload,
  Search,
  RefreshCcw,
  Trash2,
  Clock,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  File,
  Table,
  CheckCircle,
  AlertCircle,
  Loader2,
  Sparkles,
  TrendingUp,
  Download,
  Brain,
  Settings2,
  List,
  MessageSquareCode,
  Tag,
  HelpCircle,
  Plus
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { backendApi, type ExcelParseResult, type AIMarkdownAnalyzeResult, type MarkdownSection, aiApi } from '@/db/backend-api';
import {
  Table as TableComponent,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Markdown } from '@/components/ui/markdown';
import { AIChartDisplay } from '@/components/ui/ai-chart-display';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { format } from 'date-fns';

type DocumentItem = {
  doc_id: string;
  filename: string;
  original_filename: string;
  doc_type: string;
  file_size: number;
  created_at: string;
  metadata?: {
    row_count?: number;
    column_count?: number;
    columns?: string[];
  };
};

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  // 上传相关状态
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [parseResult, setParseResult] = useState<ExcelParseResult | null>(null);
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);
  const [uploadExpanded, setUploadExpanded] = useState(false);

  // AI 分析相关状态
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzingForCharts, setAnalyzingForCharts] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [analysisCharts, setAnalysisCharts] = useState<any>(null);
  const [analysisTypes, setAnalysisTypes] = useState<Array<{ value: string; label: string; description: string }>>([]);

  // Markdown AI 分析相关状态
  const [mdAnalysis, setMdAnalysis] = useState<AIMarkdownAnalyzeResult | null>(null);
  const [mdAnalysisType, setMdAnalysisType] = useState<'summary' | 'outline' | 'key_points' | 'questions' | 'tags' | 'qa' | 'statistics' | 'section' | 'charts'>('summary');
  const [mdUserPrompt, setMdUserPrompt] = useState('');
  const [mdSections, setMdSections] = useState<MarkdownSection[]>([]);
  const [mdSelectedSection, setMdSelectedSection] = useState<string>('');
  const [mdStreaming, setMdStreaming] = useState(false);
  const [mdStreamingContent, setMdStreamingContent] = useState('');

  // RAG 向量检索相关状态
  const [ragStatus, setRagStatus] = useState<{ vector_count: number; collections: string[] } | null>(null);
  const [ragSearchQuery, setRagSearchQuery] = useState('');
  const [ragSearching, setRagSearching] = useState(false);
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [ragRebuilding, setRagRebuilding] = useState(false);

  // 解析选项
  const [parseOptions, setParseOptions] = useState({
    parseAllSheets: false,
    headerRow: 0
  });

  // AI 分析选项
  const [aiOptions, setAiOptions] = useState({
    userPrompt: '',
    analysisType: 'general' as 'general' | 'summary' | 'statistics' | 'insights',
    parseAllSheetsForAI: false
  });

  // 导出相关状态
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [exporting, setExporting] = useState(false);

  // 上传面板展开状态
  const [uploadPanelOpen, setUploadPanelOpen] = useState(true);

  // 获取分析类型
  useEffect(() => {
    aiApi.getAnalysisTypes()
      .then(data => setAnalysisTypes(data.types))
      .catch(() => {
        setAnalysisTypes([
          { value: 'general', label: '综合分析', description: '提供数据概览、关键发现，质量评估和建议' },
          { value: 'summary', label: '数据摘要', description: '快速了解数据的结构、范围和主要内容' },
          { value: 'statistics', label: '统计分析', description: '数值型列的统计信息和分类列的分布' },
          { value: 'insights', label: '深度洞察', description: '深入挖掘数据，提供异常值和业务建议' }
        ]);
      });
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const result = await backendApi.getDocuments(undefined, 100);
      if (result.success) {
        setDocuments(result.documents || []);
      }
    } catch (err: any) {
      toast.error('加载文档失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // 获取 RAG 状态
  useEffect(() => {
    const fetchRagStatus = async () => {
      try {
        const status = await backendApi.getRAGStatus();
        if (status.success) {
          setRagStatus({ vector_count: status.vector_count, collections: status.collections });
        }
      } catch (err) {
        console.error('获取 RAG 状态失败:', err);
      }
    };
    fetchRagStatus();
  }, []);

  // RAG 搜索
  const handleRagSearch = async () => {
    if (!ragSearchQuery.trim()) {
      toast.error('请输入搜索内容');
      return;
    }
    setRagSearching(true);
    setRagResults([]);
    try {
      const result = await backendApi.searchRAG(ragSearchQuery, 5);
      if (result.success) {
        setRagResults(result.results || []);
      }
    } catch (err: any) {
      toast.error(err.message || '搜索失败');
    } finally {
      setRagSearching(false);
    }
  };

  // 重建 RAG 索引
  const handleRebuildRag = async () => {
    setRagRebuilding(true);
    try {
      const result = await backendApi.rebuildRAGIndex();
      if (result.success) {
        toast.success(result.message || '索引重建成功');
        // 刷新状态
        const status = await backendApi.getRAGStatus();
        if (status.success) {
          setRagStatus({ vector_count: status.vector_count, collections: status.collections });
        }
      }
    } catch (err: any) {
      toast.error(err.message || '重建索引失败');
    } finally {
      setRagRebuilding(false);
    }
  };

  // 文件上传处理
  const onDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    let successCount = 0;
    let failCount = 0;
    const successfulFiles: File[] = [];

    // 逐个上传文件
    for (const file of acceptedFiles) {
      const ext = file.name.split('.').pop()?.toLowerCase();

      try {
        if (ext === 'xlsx' || ext === 'xls') {
          const result = await backendApi.uploadExcel(file, {
            parseAllSheets: parseOptions.parseAllSheets,
            headerRow: parseOptions.headerRow
          });
          if (result.success) {
            successCount++;
            successfulFiles.push(file);
            // 第一个Excel文件设置解析结果供预览
            if (successCount === 1) {
              setUploadedFile(file);
              setParseResult(result);
              if (result.metadata?.sheet_count === 1) {
                setExpandedSheet(Object.keys(result.data?.sheets || {})[0] || null);
              }
            }
            loadDocuments();
          } else {
            failCount++;
            toast.error(`${file.name}: ${result.error || '解析失败'}`);
          }
        } else if (ext === 'md' || ext === 'markdown') {
          const result = await backendApi.uploadDocument(file);
          if (result.task_id) {
            successCount++;
            successfulFiles.push(file);
            if (successCount === 1) {
              setUploadedFile(file);
            }
            // 轮询任务状态
            let attempts = 0;
            const checkStatus = async () => {
              while (attempts < 30) {
                try {
                  const status = await backendApi.getTaskStatus(result.task_id);
                  if (status.status === 'success') {
                    loadDocuments();
                    return;
                  } else if (status.status === 'failure') {
                    return;
                  }
                } catch (e) {
                  console.error('检查状态失败', e);
                }
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
              }
            };
            checkStatus();
          } else {
            failCount++;
          }
        } else {
          // 其他文档使用通用上传接口
          const result = await backendApi.uploadDocument(file);
          if (result.task_id) {
            successCount++;
            successfulFiles.push(file);
            if (successCount === 1) {
              setUploadedFile(file);
            }
            // 轮询任务状态
            let attempts = 0;
            const checkStatus = async () => {
              while (attempts < 30) {
                try {
                  const status = await backendApi.getTaskStatus(result.task_id);
                  if (status.status === 'success') {
                    loadDocuments();
                    return;
                  } else if (status.status === 'failure') {
                    return;
                  }
                } catch (e) {
                  console.error('检查状态失败', e);
                }
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
              }
            };
            checkStatus();
          } else {
            failCount++;
          }
        }
      } catch (error: any) {
        failCount++;
        toast.error(`${file.name}: ${error.message || '上传失败'}`);
      }
    }

    setUploading(false);
    loadDocuments();

    if (successCount > 0) {
      toast.success(`成功上传 ${successCount} 个文件`);
      setUploadedFiles(prev => [...prev, ...successfulFiles]);
      setUploadExpanded(true);
    }
    if (failCount > 0) {
      toast.error(`${failCount} 个文件上传失败`);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt']
    },
    multiple: true
  });

  // AI 分析处理
  const handleAnalyze = async () => {
    if (!uploadedFile || !parseResult?.success) {
      toast.error('请先上传 Excel 文件');
      return;
    }

    setAnalyzing(true);
    setAiAnalysis(null);
    setAnalysisCharts(null);

    try {
      const result = await aiApi.analyzeExcel(uploadedFile, {
        userPrompt: aiOptions.userPrompt,
        analysisType: aiOptions.analysisType,
        parseAllSheets: aiOptions.parseAllSheetsForAI
      });

      if (result.success) {
        toast.success('AI 分析完成');
        setAiAnalysis(result);
      } else {
        toast.error(result.error || 'AI 分析失败');
      }
    } catch (error: any) {
      toast.error(error.message || 'AI 分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  // 基于 AI 分析生成图表
  const handleGenerateCharts = async () => {
    if (!aiAnalysis || !aiAnalysis.success) {
      toast.error('请先进行 AI 分析');
      return;
    }

    let analysisText = '';
    if (aiAnalysis.analysis?.analysis) {
      analysisText = aiAnalysis.analysis.analysis;
    } else if (aiAnalysis.analysis?.sheets) {
      const sheets = aiAnalysis.analysis.sheets;
      if (sheets && Object.keys(sheets).length > 0) {
        const firstSheet = Object.keys(sheets)[0];
        analysisText = sheets[firstSheet]?.analysis || '';
      }
    }

    if (!analysisText?.trim()) {
      toast.error('无法获取 AI 分析结果');
      return;
    }

    setAnalyzingForCharts(true);
    setAnalysisCharts(null);

    try {
      const result = await aiApi.extractAndGenerateCharts({
        analysis_text: analysisText,
        original_filename: uploadedFile?.name || 'unknown',
        file_type: 'excel'
      });

      if (result.success) {
        toast.success('图表生成完成');
        setAnalysisCharts(result);
      } else {
        toast.error(result.error || '图表生成失败');
      }
    } catch (error: any) {
      toast.error(error.message || '图表生成失败');
    } finally {
      setAnalyzingForCharts(false);
    }
  };

  // 获取工作表数据
  const getSheetData = (sheetName: string) => {
    if (!parseResult?.success || !parseResult.data) return null;
    const data = parseResult.data;
    if (data.sheets && data.sheets[sheetName]) {
      return data.sheets[sheetName];
    }
    if (!data.sheets && data.columns && data.rows) {
      return data;
    }
    return null;
  };

  // 打开导出对话框
  const openExportDialog = () => {
    if (!parseResult?.success || !parseResult.data) {
      toast.error('请先上传并解析 Excel 文件');
      return;
    }

    const data = parseResult.data;
    let sheets: string[] = [];
    if (data.sheets) {
      sheets = Object.keys(data.sheets);
    } else {
      sheets = ['默认工作表'];
    }

    setSelectedSheet(sheets[0]);
    const sheetColumns = getSheetData(sheets[0])?.columns || [];
    setSelectedColumns(new Set(sheetColumns));
    setSelectAll(true);
    setExportDialogOpen(true);
  };

  // 导出处理
  const handleExport = async () => {
    if (selectedColumns.size === 0) {
      toast.error('请至少选择一列');
      return;
    }

    if (!parseResult?.metadata?.saved_path) {
      toast.error('无法获取文件路径');
      return;
    }

    setExporting(true);

    try {
      const blob = await backendApi.exportExcel(
        parseResult.metadata.saved_path,
        {
          columns: Array.from(selectedColumns),
          sheetName: selectedSheet === '默认工作表' ? undefined : selectedSheet
        }
      );

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `export_${selectedSheet}_${uploadedFile?.name || 'data.xlsx'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success('导出成功');
      setExportDialogOpen(false);
    } catch (error: any) {
      toast.error(error.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteFile = () => {
    setUploadedFile(null);
    setUploadedFiles([]);
    setParseResult(null);
    setAiAnalysis(null);
    setAnalysisCharts(null);
    setExpandedSheet(null);
    toast.success('文件已清除');
  };

  const handleRemoveUploadedFile = (index: number) => {
    setUploadedFiles(prev => {
      const newFiles = prev.filter((_, i) => i !== index);
      if (newFiles.length === 0) {
        setUploadedFile(null);
      }
      return newFiles;
    });
    toast.success('文件已从列表移除');
  };

  const handleDelete = async (docId: string) => {
    try {
      const result = await backendApi.deleteDocument(docId);
      if (result.success) {
        setDocuments(prev => prev.filter(d => d.doc_id !== docId));
        toast.success('文档已删除');
      }
    } catch (err: any) {
      toast.error('删除失败: ' + (err.message || '未知错误'));
    }
  };

  const filteredDocs = documents.filter(doc =>
    doc.original_filename.toLowerCase().includes(search.toLowerCase())
  );

  const getDocIcon = (docType: string) => {
    switch (docType) {
      case 'xlsx':
      case 'xls':
        return <FileSpreadsheet size={28} />;
      case 'docx':
      case 'doc':
        return <FileText size={28} />;
      default:
        return <File size={28} />;
    }
  };

  const isMarkdownFile = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ext === 'md' || ext === 'markdown';
  };

  // Markdown AI 分析处理
  const handleMdAnalyze = async () => {
    if (!uploadedFile || !isMarkdownFile(uploadedFile.name)) {
      toast.error('请先上传 Markdown 文件');
      return;
    }

    setAnalyzing(true);
    setMdAnalysis(null);

    try {
      const result = await aiApi.analyzeMarkdown(uploadedFile, {
        analysisType: mdAnalysisType,
        userPrompt: mdUserPrompt,
        sectionNumber: mdSelectedSection || undefined
      });

      if (result.success) {
        toast.success('Markdown AI 分析完成');
        setMdAnalysis(result);
      } else {
        toast.error(result.error || 'AI 分析失败');
      }
    } catch (error: any) {
      toast.error(error.message || 'AI 分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  // 流式分析 Markdown
  const handleMdAnalyzeStream = async () => {
    if (!uploadedFile || !isMarkdownFile(uploadedFile.name)) {
      toast.error('请先上传 Markdown 文件');
      return;
    }

    setAnalyzing(true);
    setMdStreaming(true);
    setMdStreamingContent('');
    setMdAnalysis(null);

    try {
      await aiApi.analyzeMarkdownStream(
        uploadedFile,
        {
          analysisType: mdAnalysisType,
          userPrompt: mdUserPrompt,
          sectionNumber: mdSelectedSection || undefined
        },
        (chunk: { type: string; delta?: string; error?: string }) => {
          if (chunk.type === 'content' && chunk.delta) {
            setMdStreamingContent(prev => prev + chunk.delta);
          } else if (chunk.type === 'error') {
            toast.error(chunk.error || '流式分析出错');
          }
        }
      );
    } catch (error: any) {
      toast.error(error.message || 'AI 分析失败');
    } finally {
      setAnalyzing(false);
      setMdStreaming(false);
    }
  };

  // 获取 Markdown 文档大纲（分章节）
  const fetchMdOutline = async () => {
    if (!uploadedFile || !isMarkdownFile(uploadedFile.name)) return;

    try {
      const result = await aiApi.getMarkdownOutline(uploadedFile);
      if (result.success && result.outline) {
        setMdSections(result.outline);
      }
    } catch (error) {
      console.error('获取大纲失败:', error);
    }
  };

  const getMdAnalysisIcon = (type: string) => {
    switch (type) {
      case 'summary': return <FileText size={20} />;
      case 'outline': return <List size={20} />;
      case 'key_points': return <TrendingUp size={20} />;
      case 'statistics': return <TrendingUp size={20} />;
      case 'section': return <FileText size={20} />;
      case 'questions': return <MessageSquareCode size={20} />;
      case 'tags': return <Tag size={20} />;
      case 'qa': return <HelpCircle size={20} />;
      case 'charts': return <TrendingUp size={20} />;
      default: return <Sparkles size={20} />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const getAnalysisIcon = (type: string) => {
    switch (type) {
      case 'general': return <FileText size={20} />;
      case 'summary': return <Table size={20} />;
      case 'statistics': return <TrendingUp size={20} />;
      case 'insights': return <Brain size={20} />;
      default: return <Sparkles size={20} />;
    }
  };

  const isExcelFile = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ext === 'xlsx' || ext === 'xls';
  };

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">文档中心</h1>
          <p className="text-muted-foreground">上传文档，自动解析并使用 AI 进行深度分析</p>
        </div>
        <Button variant="outline" className="rounded-xl gap-2" onClick={() => loadDocuments()}>
          <RefreshCcw size={18} />
          <span>刷新</span>
        </Button>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：上传和配置区域 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 上传卡片 */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Upload className="text-primary" size={20} />
                  文件上传
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setUploadPanelOpen(!uploadPanelOpen)}>
                  {uploadPanelOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </Button>
              </div>
              <CardDescription>拖拽或点击上传文档文件</CardDescription>
            </CardHeader>
            {uploadPanelOpen && (
              <CardContent className="space-y-4">
                {uploadedFiles.length > 0 || uploadedFile ? (
                  <div className="space-y-3">
                    {/* 文件列表头部 */}
                    <div
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
                      onClick={() => setUploadExpanded(!uploadExpanded)}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                          <Upload size={20} />
                        </div>
                        <div>
                          <p className="font-semibold text-sm">
                            已上传 {(uploadedFiles.length > 0 ? uploadedFiles : [uploadedFile]).length} 个文件
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {uploadExpanded ? '点击收起' : '点击展开查看'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteFile();
                          }}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 size={14} className="mr-1" />
                          清空
                        </Button>
                        {uploadExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </div>
                    </div>

                    {/* 展开的文件列表 */}
                    {uploadExpanded && (
                      <div className="space-y-2 border rounded-xl p-3">
                        {(uploadedFiles.length > 0 ? uploadedFiles : [uploadedFile]).filter(Boolean).map((file, index) => (
                          <div key={index} className="flex items-center gap-3 p-2 bg-background rounded-lg">
                            <div className={cn(
                              "w-8 h-8 rounded flex items-center justify-center",
                              isExcelFile(file?.name || '') ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
                            )}>
                              {isExcelFile(file?.name || '') ? <FileSpreadsheet size={16} /> : <FileText size={16} />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm truncate">{file?.name}</p>
                              <p className="text-xs text-muted-foreground">{formatFileSize(file?.size || 0)}</p>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:bg-destructive/10"
                              onClick={() => handleRemoveUploadedFile(index)}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </div>
                        ))}

                        {/* 继续添加按钮 */}
                        <div
                          {...getRootProps()}
                          className="flex items-center justify-center gap-2 p-3 border-2 border-dashed rounded-lg cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-colors"
                        >
                          <input {...getInputProps()} multiple={true} />
                          <Plus size={16} className="text-muted-foreground" />
                          <span className="text-sm text-muted-foreground">继续添加更多文件</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    {...getRootProps()}
                    className={cn(
                      "border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
                      isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5",
                      uploading && "opacity-50 pointer-events-none"
                    )}
                  >
                    <input {...getInputProps()} multiple={true} />
                    <div className="w-14 h-14 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                      {uploading ? <Loader2 className="animate-spin" size={28} /> : <Upload size={28} />}
                    </div>
                    <p className="font-semibold text-sm">
                      {isDragActive ? '释放以开始上传' : '点击或拖拽文件到这里'}
                    </p>
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-200 text-xs">
                        <FileText size={12} className="mr-1" /> Word
                      </Badge>
                      <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-200 text-xs">
                        <FileSpreadsheet size={12} className="mr-1" /> Excel
                      </Badge>
                      <Badge variant="outline" className="bg-purple-500/10 text-purple-600 border-purple-200 text-xs">
                        <FileText size={12} className="mr-1" /> Markdown
                      </Badge>
                      <Badge variant="outline" className="bg-gray-500/10 text-gray-600 border-gray-200 text-xs">
                        <File size={12} className="mr-1" /> 文本
                      </Badge>
                    </div>
                  </div>
                )}
              </CardContent>
            )}
          </Card>

          {/* Excel 解析选项 */}
          {uploadedFile && isExcelFile(uploadedFile.name) && (
            <Card className="border-none shadow-md">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="text-primary" size={20} />
                  解析选项
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="parse-all-sheets" className="cursor-pointer text-sm">解析所有工作表</Label>
                  <Switch
                    id="parse-all-sheets"
                    checked={parseOptions.parseAllSheets}
                    onCheckedChange={(checked) => setParseOptions({ ...parseOptions, parseAllSheets: checked })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="header-row" className="text-sm">表头行号</Label>
                  <Input
                    id="header-row"
                    type="number"
                    min="0"
                    max="100"
                    value={parseOptions.headerRow}
                    onChange={(e) => setParseOptions({ ...parseOptions, headerRow: parseInt(e.target.value) || 0 })}
                    className="bg-background"
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* AI 分析选项 */}
          {uploadedFile && isExcelFile(uploadedFile.name) && parseResult?.success && (
            <Card className="border-none shadow-md bg-gradient-to-br from-primary/5 to-purple-500/5">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="text-primary" size={20} />
                  AI 分析
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="analysis-type" className="text-sm">分析类型</Label>
                  <Select value={aiOptions.analysisType} onValueChange={(value: any) => setAiOptions({ ...aiOptions, analysisType: value })}>
                    <SelectTrigger id="analysis-type" className="bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(analysisTypes || []).map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          <div className="flex items-center gap-2">
                            {getAnalysisIcon(type.value)}
                            <div className="flex flex-col">
                              <span className="font-medium">{type.label}</span>
                            </div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="user-prompt" className="text-sm">自定义提示词（可选）</Label>
                  <Textarea
                    id="user-prompt"
                    placeholder="例如：请帮我分析销售额最高的产品..."
                    value={aiOptions.userPrompt}
                    onChange={(e) => setAiOptions({ ...aiOptions, userPrompt: e.target.value })}
                    className="bg-background resize-none"
                    rows={2}
                  />
                </div>
                <Button onClick={handleAnalyze} disabled={analyzing} className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90">
                  {analyzing ? <><Loader2 className="mr-2 animate-spin" size={16} /> AI 分析中...</> : <><Sparkles className="mr-2" size={16} />开始 AI 分析</>}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Markdown AI 分析选项 */}
          {uploadedFile && isMarkdownFile(uploadedFile.name) && (
            <Card className="border-none shadow-md bg-gradient-to-br from-purple-500/5 to-primary/5">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="text-purple-500" size={20} />
                  Markdown AI 分析
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 章节选择 */}
                {mdSections.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="md-section" className="text-sm">指定章节（可选）</Label>
                    <Select value={mdSelectedSection} onValueChange={setMdSelectedSection}>
                      <SelectTrigger id="md-section" className="bg-background">
                        <SelectValue placeholder="全文分析" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">全文分析</SelectItem>
                        {mdSections.map((section) => (
                          <SelectItem key={section.number} value={section.number}>
                            {section.number}、{section.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="md-analysis-type" className="text-sm">分析类型</Label>
                  <Select value={mdAnalysisType} onValueChange={(value: any) => setMdAnalysisType(value)}>
                    <SelectTrigger id="md-analysis-type" className="bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[
                        { value: 'summary', label: '文档摘要', desc: '主要内容摘要' },
                        { value: 'outline', label: '大纲提取', desc: '提取文档结构' },
                        { value: 'key_points', label: '关键要点', desc: '提取关键信息' },
                        { value: 'statistics', label: '统计分析', desc: '统计数据分析' },
                        { value: 'section', label: '章节分析', desc: '分章节详细分析' },
                        { value: 'questions', label: '生成问题', desc: '生成理解性问题' },
                        { value: 'tags', label: '生成标签', desc: '提取主题标签' },
                        { value: 'qa', label: '问答对', desc: '生成问答内容' },
                        { value: 'charts', label: '数据图表', desc: '生成可视化数据' }
                      ].map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          <div className="flex items-center gap-2">
                            {getMdAnalysisIcon(type.value)}
                            <div className="flex flex-col">
                              <span className="font-medium">{type.label}</span>
                              <span className="text-xs text-muted-foreground">{type.desc}</span>
                            </div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="md-user-prompt" className="text-sm">自定义提示词（可选）</Label>
                  <Textarea
                    id="md-user-prompt"
                    placeholder="例如：请重点关注技术实现部分..."
                    value={mdUserPrompt}
                    onChange={(e) => setMdUserPrompt(e.target.value)}
                    className="bg-background resize-none"
                    rows={2}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleMdAnalyze}
                    disabled={analyzing}
                    className="flex-1 bg-gradient-to-r from-purple-500 to-primary hover:from-purple-500/90 hover:to-primary/90"
                  >
                    {analyzing && !mdStreaming ? <><Loader2 className="mr-2 animate-spin" size={16} /> 分析中...</> : <><Sparkles className="mr-2" size={16} />普通分析</>}
                  </Button>
                  <Button
                    onClick={handleMdAnalyzeStream}
                    disabled={analyzing}
                    variant="outline"
                    className="flex-1"
                  >
                    {analyzing && mdStreaming ? <><Loader2 className="mr-2 animate-spin" size={16} /> 流式...</> : <><Sparkles className="mr-2" size={16} />流式分析</>}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 数据操作 */}
          {parseResult?.success && (
            <Card className="border-none shadow-md bg-gradient-to-br from-emerald-500/5 to-blue-500/5">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <Download className="text-emerald-500" size={20} />
                  数据操作
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button onClick={handleGenerateCharts} disabled={!aiAnalysis?.success || analyzingForCharts} className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90">
                  {analyzingForCharts ? <><Loader2 className="mr-2 animate-spin" size={16} />生成中...</> : <><Brain size={16} className="mr-2" />AI 分析图表</>}
                </Button>
                <Button onClick={openExportDialog} variant="outline" className="w-full">
                  <Download size={16} className="mr-2" />导出 Excel 数据
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 右侧：结果显示区域 */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI 分析结果 */}
          {aiAnalysis && (
            <Card className="border-none shadow-md border-l-4 border-l-primary">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="text-primary" size={20} />
                      AI 分析结果
                    </CardTitle>
                    {aiAnalysis.analysis?.model && (
                      <CardDescription>使用模型: {aiAnalysis.analysis.model}</CardDescription>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="max-h-[400px] overflow-y-auto">
                {aiAnalysis.analysis?.sheets && typeof aiAnalysis.analysis.sheets === 'object' ? (
                  <div className="space-y-4">
                    {Object.entries(aiAnalysis.analysis.sheets || {}).map(([sheetName, result]: [string, any]) => (
                      <div key={sheetName} className="p-4 bg-muted/30 rounded-xl">
                        <div className="flex items-center gap-2 mb-2">
                          <FileSpreadsheet size={16} className="text-primary" />
                          <span className="font-semibold">{sheetName}</span>
                          {result.success ? <CheckCircle size={16} className="text-emerald-500" /> : <AlertCircle size={16} className="text-destructive" />}
                        </div>
                        {result.success && result.analysis && <Markdown content={result.analysis} />}
                        {!result.success && <p className="text-sm text-destructive">{result.error || '分析失败'}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  aiAnalysis.analysis?.analysis && <Markdown content={aiAnalysis.analysis.analysis} />
                )}
              </CardContent>
            </Card>
          )}

          {/* Markdown AI 分析结果 */}
          {(mdAnalysis || mdStreamingContent) && (
            <Card className="border-none shadow-md border-l-4 border-l-purple-500">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="text-purple-500" size={20} />
                      Markdown AI 分析结果
                      {mdStreaming && <Badge variant="default" className="ml-2 bg-purple-500">流式输出中</Badge>}
                    </CardTitle>
                    {mdAnalysis && (
                      <CardDescription>
                        {mdAnalysis.filename} • {mdAnalysis.word_count || 0} 字 • {mdAnalysis.analysis_type}
                        {mdAnalysis.section && ` • ${mdAnalysis.section}`}
                      </CardDescription>
                    )}
                  </div>
                  {mdAnalysis?.structure && (
                    <Badge variant="secondary">
                      {mdAnalysis.structure.title_count || 0} 标题 • {mdAnalysis.structure.section_count || 0} 章节
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="max-h-[500px] overflow-y-auto">
                {/* 流式内容优先显示 */}
                {mdStreamingContent && (
                  <div className="animate-pulse text-sm text-muted-foreground mb-4">
                    流式输出中...
                  </div>
                )}
                {mdStreamingContent && <Markdown content={mdStreamingContent} />}
                {mdAnalysis?.analysis && !mdStreamingContent && <Markdown content={mdAnalysis.analysis} />}
                {!mdAnalysis?.success && !mdStreamingContent && <p className="text-sm text-destructive">{mdAnalysis?.error || '分析失败'}</p>}
              </CardContent>
            </Card>
          )}

          {/* 图表显示 */}
          {analysisCharts && (
            <Card className="border-none shadow-md border-l-4 border-l-indigo-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="text-indigo-500" size={20} />
                  AI 分析结果图表
                </CardTitle>
              </CardHeader>
              <CardContent>
                <AIChartDisplay
                  charts={analysisCharts.charts}
                  statistics={analysisCharts.statistics}
                  tablePreview={analysisCharts.charts?.table_preview}
                />
              </CardContent>
            </Card>
          )}

          {/* Excel 数据预览 */}
          {parseResult?.success && parseResult.data && (
            <Card className="border-none shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <Table className="text-primary" size={20} />
                      数据预览
                    </CardTitle>
                    <CardDescription>{parseResult?.data?.sheets ? '所有工作表数据' : '工作表数据'}</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={openExportDialog} className="gap-2">
                    <Download size={14} />导出
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {parseResult?.data?.sheets && typeof parseResult.data.sheets === 'object' ? (
                  <div className="space-y-4">
                    {Object.entries(parseResult.data.sheets || {}).map(([sheetName, sheetData]: [string, any]) => (
                      <div key={sheetName} className="border rounded-xl overflow-hidden">
                        <button
                          onClick={() => setExpandedSheet(expandedSheet === sheetName ? null : sheetName)}
                          className="w-full px-6 py-4 flex items-center justify-between bg-muted/30 hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <FileSpreadsheet size={18} className="text-primary" />
                            <span className="font-semibold">{sheetName}</span>
                            <Badge variant="secondary" className="text-xs">{sheetData.row_count || 0} 行</Badge>
                          </div>
                          {expandedSheet === sheetName ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {expandedSheet === sheetName && (
                          <div className="p-4">
                            <DataTable columns={sheetData.columns || []} rows={sheetData.rows || []} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <DataTable columns={parseResult?.data?.columns || []} rows={parseResult?.data?.rows || []} />
                )}
              </CardContent>
            </Card>
          )}

          {/* RAG 向量检索 */}
          <Card className="border-none shadow-md bg-gradient-to-br from-violet-500/5 to-cyan-500/5">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="text-violet-500" size={20} />
                    RAG 向量检索
                  </CardTitle>
                  <CardDescription>
                    向量索引: {(ragStatus?.vector_count) || 0} 条
                    {ragStatus?.collections && ragStatus.collections.length > 0 && ` | 集合: ${ragStatus.collections.join(', ')}`}
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRebuildRag}
                  disabled={ragRebuilding}
                >
                  {ragRebuilding ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />}
                  重建索引
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 搜索框 */}
              <div className="flex gap-2">
                <Input
                  placeholder="输入查询内容，例如：查询去年销售额最高的客户..."
                  value={ragSearchQuery}
                  onChange={(e) => setRagSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRagSearch()}
                  className="flex-1"
                />
                <Button onClick={handleRagSearch} disabled={ragSearching}>
                  {ragSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                </Button>
              </div>
              {/* 搜索结果 */}
              {(ragResults?.length ?? 0) > 0 && (
                <div className="space-y-3">
                  <Label className="text-sm font-medium">检索结果</Label>
                  {(ragResults || []).map((result, index) => (
                    <div key={index} className="p-4 rounded-xl border bg-card hover:bg-muted/30 transition-colors">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <Badge variant="outline" className="text-xs">
                          相似度: {(result.score * 100).toFixed(1)}%
                        </Badge>
                        {result.metadata?.table_name && (
                          <Badge variant="secondary" className="text-xs">
                            {result.metadata.table_name}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{result.content}</p>
                      {result.metadata && (
                        <div className="flex gap-2 mt-2 flex-wrap">
                          {result.metadata.field_name && (
                            <span className="text-xs text-muted-foreground">
                              字段: {result.metadata.field_name}
                            </span>
                          )}
                          {result.metadata.filename && (
                            <span className="text-xs text-muted-foreground">
                              文件: {result.metadata.filename}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 文档列表 */}
          <Card className="border-none shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="text-primary" size={20} />
                已上传文档
              </CardTitle>
              <CardDescription>共 {documents.length} 个文档</CardDescription>
            </CardHeader>
            <CardContent>
              {/* 搜索 */}
              <div className="mb-4 relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索文档..."
                  className="pl-9 h-10 bg-muted/30"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>

              {/* 文档列表 */}
              {loading ? (
                <div className="space-y-3">{[1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>
              ) : (filteredDocs?.length ?? 0) > 0 ? (
                <div className="space-y-3">
                  {(filteredDocs || []).map(doc => (
                    <div key={doc.doc_id} className="flex items-center gap-4 p-4 rounded-xl border border-transparent hover:bg-muted/30 transition-all group">
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
                        doc.doc_type === 'xlsx' ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
                      )}>
                        {getDocIcon(doc.doc_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold truncate">{doc.original_filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.doc_type.toUpperCase()} • {format(new Date(doc.created_at), 'yyyy-MM-dd HH:mm')}
                        </p>
                      </div>
                      <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100" onClick={() => handleDelete(doc.doc_id)}>
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <FileText size={48} className="mx-auto mb-4 opacity-30" />
                  <p>暂无文档，上传文件开始使用</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 初始状态 */}
          {!loading && !uploadedFile && !parseResult && !aiAnalysis && (
            <Card className="border-none shadow-md">
              <CardContent className="p-12 flex flex-col items-center justify-center text-center">
                <Sparkles size={48} className="text-muted-foreground/30 mb-4" />
                <p className="font-semibold text-lg">上传文档开始分析</p>
                <p className="text-sm text-muted-foreground mt-2">上传 Excel 文件可获得 AI 分析和图表生成功能</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 导出对话框 */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>导出 Excel 数据</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>选择工作表</Label>
              <Select value={selectedSheet} onValueChange={(value) => {
                setSelectedSheet(value);
                const sheetColumns = getSheetData(value)?.columns || [];
                setSelectedColumns(new Set(sheetColumns));
                setSelectAll(true);
              }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {parseResult?.data?.sheets ? (
                    Object.keys(parseResult.data.sheets).map(sheetName => (
                      <SelectItem key={sheetName} value={sheetName}>{sheetName}</SelectItem>
                    ))
                  ) : (
                    <SelectItem value="默认工作表">默认工作表</SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>选择列</Label>
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => {
                  if (selectAll) {
                    setSelectedColumns(new Set());
                  } else {
                    setSelectedColumns(new Set(getSheetData(selectedSheet)?.columns || []));
                  }
                  setSelectAll(!selectAll);
                }}>
                  {selectAll ? '取消全选' : '全选'}
                </Button>
              </div>
              <div className="border rounded-lg max-h-60 overflow-y-auto">
                <div className="grid gap-1 p-2">
                  {getSheetData(selectedSheet)?.columns?.map((column: string) => (
                    <div
                      key={column}
                      className={cn("flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer", selectedColumns.has(column) && "bg-primary/5")}
                      onClick={() => {
                        const newSelected = new Set(selectedColumns);
                        if (newSelected.has(column)) {
                          newSelected.delete(column);
                        } else {
                          newSelected.add(column);
                        }
                        setSelectedColumns(newSelected);
                        setSelectAll(newSelected.size === (getSheetData(selectedSheet)?.columns || []).length);
                      }}
                    >
                      <Checkbox checked={selectedColumns.has(column)} />
                      <span className="text-sm flex-1 truncate">{column}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">已选择 {selectedColumns.size} 列</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExportDialogOpen(false)} disabled={exporting}>取消</Button>
            <Button onClick={handleExport} disabled={exporting || selectedColumns.size === 0}>
              {exporting ? <><Loader2 className="mr-2 animate-spin" size={16} />导出中...</> : <><Download size={16} className="mr-2" />导出</>}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// 数据表格组件
const DataTable: React.FC<{ columns: string[]; rows: Record<string, any>[] }> = ({ columns, rows }) => {
  if (!columns.length || !rows.length) {
    return <div className="text-center py-8 text-muted-foreground text-sm">暂无数据</div>;
  }

  return (
    <div className="rounded-lg border overflow-x-auto">
      <TableComponent>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16 text-center text-muted-foreground">#</TableHead>
            {columns.map((col, idx) => (
              <TableHead key={idx} className="whitespace-nowrap">{col || `<列${idx + 1}>`}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.slice(0, 100).map((row, rowIdx) => (
            <TableRow key={rowIdx}>
              <TableCell className="text-center text-muted-foreground font-medium">{rowIdx + 1}</TableCell>
              {columns.map((col, colIdx) => (
                <TableCell key={colIdx} className="whitespace-nowrap">
                  {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </TableComponent>
      {rows.length > 100 && (
        <div className="p-3 text-center text-sm text-muted-foreground bg-muted/30">
          仅显示前 100 行数据
        </div>
      )}
    </div>
  );
};

export default Documents;