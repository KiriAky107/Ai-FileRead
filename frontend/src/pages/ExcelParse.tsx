import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  FileSpreadsheet,
  Upload,
  Trash2,
  ChevronDown,
  ChevronUp,
  Table,
  Info,
  CheckCircle,
  AlertCircle,
  Loader2,
  Sparkles,
  FileText,
  TrendingUp,
  Download,
  Brain,
  Check,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { backendApi, type ExcelParseResult, type ExcelUploadOptions, aiApi } from '@/db/backend-api';
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

const ExcelParse: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzingForCharts, setAnalyzingForCharts] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [parseResult, setParseResult] = useState<ExcelParseResult | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [analysisCharts, setAnalysisCharts] = useState<any>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);
  const [parseOptions, setParseOptions] = useState<ExcelUploadOptions>({
    parseAllSheets: false,
    headerRow: 0
  });
  const [aiOptions, setAiOptions] = useState({
    userPrompt: '',
    analysisType: 'general' as 'general' | 'summary' | 'statistics' | 'insights',
    parseAllSheetsForAI: false
  });
  const [analysisTypes, setAnalysisTypes] = useState<Array<{ value: string; label: string; description: string }>>([]);

  // 导出相关状态
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // 获取支持的分析类型
  useEffect(() => {
    aiApi.getAnalysisTypes()
      .then(data => setAnalysisTypes(data.types))
      .catch(() => {
        setAnalysisTypes([
          { value: 'general', label: '综合分析', description: '提供数据概览、关键发现、质量评估和建议' },
          { value: 'summary', label: '数据摘要', description: '快速了解数据的结构、范围和主要内容' },
          { value: 'statistics', label: '统计分析', description: '数值型列的统计信息和分类列的分布' },
          { value: 'insights', label: '深度洞察', description: '深入挖掘数据，提供异常值和业务建议' }
        ]);
      });
  }, []);

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      toast.error('仅支持 .xlsx 和 .xls 格式的 Excel 文件');
      return;
    }

    setUploadedFile(file);
    setLoading(true);
    setParseResult(null);
    setAiAnalysis(null);
    setAnalysisCharts(null);
    setExpandedSheet(null);

    try {
      const result = await backendApi.uploadExcel(file, parseOptions);

      if (result.success) {
        toast.success(`解析成功: ${file.name}`);
        setParseResult(result);
        // 自动展开第一个工作表
        if (result.metadata?.sheet_count === 1) {
          setExpandedSheet(null);
        }
      } else {
        toast.error(result.error || '解析失败');
      }
    } catch (error: any) {
      toast.error(error.message || '上传失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!uploadedFile || !parseResult?.success) {
      toast.error('请先上传并解析 Excel 文件');
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

  const handleGenerateChartsFromAnalysis = async () => {
    if (!aiAnalysis || !aiAnalysis.success) {
      toast.error('请先进行 AI 分析');
      return;
    }

    // 提取 AI 分析文本
    let analysisText = '';

    if (aiAnalysis.analysis?.analysis) {
      analysisText = aiAnalysis.analysis.analysis;
    } else if (aiAnalysis.analysis?.sheets) {
      // 多工作表模式，合并所有工作表的分析结果
      const sheetAnalyses = aiAnalysis.analysis.sheets;
      if (sheetAnalyses && Object.keys(sheetAnalyses).length > 0) {
        const firstSheet = Object.keys(sheetAnalyses)[0];
        analysisText = sheetAnalyses[firstSheet]?.analysis || '';
      }
    }

    if (!analysisText || !analysisText.trim()) {
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
        toast.success('基于 AI 分析的图表生成完成');
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

    // 多工作表模式
    if (data.sheets && data.sheets[sheetName]) {
      return data.sheets[sheetName];
    }

    // 单工作表模式
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

    // 获取所有工作表
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

  // 处理列选择
  const toggleColumn = (column: string) => {
    const newSelected = new Set(selectedColumns);
    if (newSelected.has(column)) {
      newSelected.delete(column);
    } else {
      newSelected.add(column);
    }
    setSelectedColumns(newSelected);
    setSelectAll(newSelected.size === (getSheetData(selectedSheet)?.columns || []).length);
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    const sheetColumns = getSheetData(selectedSheet)?.columns || [];
    if (selectAll) {
      setSelectedColumns(new Set());
    } else {
      setSelectedColumns(new Set(sheetColumns));
    }
    setSelectAll(!selectAll);
  };

  // 执行导出
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

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1
  });

  const handleDeleteFile = () => {
    setUploadedFile(null);
    setParseResult(null);
    setAiAnalysis(null);
    setAnalysisCharts(null);
    setExpandedSheet(null);
    toast.success('文件已清除');
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
      case 'general':
        return <FileText size={20} />;
      case 'summary':
        return <Table size={20} />;
      case 'statistics':
        return <TrendingUp size={20} />;
      case 'insights':
        return <Brain size={20} />;
      default:
        return <Sparkles size={20} />;
    }
  };

  const downloadAnalysis = () => {
    if (!aiAnalysis?.analysis?.analysis) return;

    const content = aiAnalysis.analysis.analysis;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `AI分析结果_${uploadedFile?.name || 'excel'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('分析结果已下载');
  };

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-2">
            <Sparkles className="text-primary" />
            Excel 智能分析工具
          </h1>
          <p className="text-muted-foreground">上传 Excel 文件，使用 AI 进行深度数据分析。</p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：上传区域 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 上传卡片 */}
          <Card className="border-none shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileSpreadsheet className="text-primary" size={20} />
                文件上传
              </CardTitle>
              <CardDescription>
                拖拽或点击上传 Excel 文件
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!uploadedFile ? (
                <div
                  {...getRootProps()}
                  className={cn(
                    "border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
                    isDragActive ? "border-primary bg-primary/5 scale-[1.02]" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5",
                    loading && "opacity-50 pointer-events-none"
                  )}
                >
                  <input {...getInputProps()} />
                  <div className="w-16 h-16 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    {loading ? <Loader2 className="animate-spin" size={32} /> : <Upload size={32} />}
                  </div>
                  <p className="font-semibold text-sm">
                    {isDragActive ? '释放以开始上传' : '点击或拖拽文件到这里'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">支持 .xlsx 和 .xls 格式</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 bg-muted/30 rounded-xl">
                    <div className="w-12 h-12 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                      <FileSpreadsheet size={24} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{uploadedFile.name}</p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(uploadedFile.size)}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:bg-destructive/10"
                      onClick={handleDeleteFile}
                    >
                      <Trash2 size={18} />
                    </Button>
                  </div>
                  <Button
                    onClick={() => onDrop([uploadedFile])}
                    className="w-full"
                    disabled={loading}
                  >
                    {loading ? '解析中...' : '重新解析'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 解析选项卡片 */}
          <Card className="border-none shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="text-primary" size={20} />
                解析选项
              </CardTitle>
              <CardDescription>
                配置 Excel 文件的解析方式
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="parse-all-sheets" className="cursor-pointer">
                  解析所有工作表
                </Label>
                <Switch
                  id="parse-all-sheets"
                  checked={parseOptions.parseAllSheets}
                  onCheckedChange={(checked) => setParseOptions({ ...parseOptions, parseAllSheets: checked })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="header-row">表头行号</Label>
                <Input
                  id="header-row"
                  type="number"
                  min="0"
                  max="100"
                  value={parseOptions.headerRow}
                  onChange={(e) => setParseOptions({ ...parseOptions, headerRow: parseInt(e.target.value) || 0 })}
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">
                  从 0 开始，0 表示第一行
                </p>
              </div>
            </CardContent>
          </Card>

          {/* AI 分析选项卡片 */}
          <Card className="border-none shadow-md bg-gradient-to-br from-primary/5 to-purple-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="text-primary" size={20} />
                AI 分析选项
              </CardTitle>
              <CardDescription>
                配置 AI 分析的方式
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="analysis-type">分析类型</Label>
                <Select
                  value={aiOptions.analysisType}
                  onValueChange={(value: any) => setAiOptions({ ...aiOptions, analysisType: value })}
                >
                  <SelectTrigger id="analysis-type" className="bg-background">
                    <SelectValue placeholder="选择分析类型" />
                  </SelectTrigger>
                  <SelectContent>
                    {analysisTypes.map(type => (
                      <SelectItem key={type.value} value={type.value}>
                        <div className="flex items-center gap-2">
                          {getAnalysisIcon(type.value)}
                          <div className="flex flex-col">
                            <span className="font-medium">{type.label}</span>
                            <span className="text-xs text-muted-foreground">{type.description}</span>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="user-prompt">自定义提示词（可选）</Label>
                <Textarea
                  id="user-prompt"
                  placeholder="例如：请帮我分析销售额最高的产品..."
                  value={aiOptions.userPrompt}
                  onChange={(e) => setAiOptions({ ...aiOptions, userPrompt: e.target.value })}
                  className="bg-background resize-none"
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">
                  填写后将覆盖标准分析
                </p>
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="ai-parse-all-sheets" className="cursor-pointer">
                  分析所有工作表
                </Label>
                <Switch
                  id="ai-parse-all-sheets"
                  checked={aiOptions.parseAllSheetsForAI}
                  onCheckedChange={(checked) => setAiOptions({ ...aiOptions, parseAllSheetsForAI: checked })}
                />
              </div>
              <Button
                onClick={handleAnalyze}
                disabled={!parseResult?.success || analyzing}
                className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="mr-2 animate-spin" size={18} />
                    AI 分析中...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2" size={18} />
                    开始 AI 分析
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* 数据操作卡片 */}
          <Card className="border-none shadow-md bg-gradient-to-br from-emerald-500/5 to-blue-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="text-emerald-500" size={20} />
                数据操作
              </CardTitle>
              <CardDescription>
                数据导出和可视化操作
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-4 bg-primary/5 rounded-xl border border-primary/20">
                  <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center shrink-0">
                    <Brain size={18} />
                  </div>
                  <div className="flex-1 space-y-1">
                    <h4 className="font-semibold text-sm">基于 AI 分析结果</h4>
                    <p className="text-xs text-muted-foreground">从 AI 分析文本中提取数据并生成可视化图表</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-xl">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                    <Download size={18} />
                  </div>
                  <div className="flex-1 space-y-1">
                    <h4 className="font-semibold text-sm">导出 Excel 数据</h4>
                    <p className="text-xs text-muted-foreground">选择工作表和列，导出为新的 Excel 文件</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2 flex flex gap-2">
                <Button
                  onClick={handleGenerateChartsFromAnalysis}
                  disabled={!aiAnalysis?.success || analyzingForCharts}
                  className="flex-1 bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90"
                >
                  {analyzingForCharts ? (
                    <>
                      <Loader2 className="mr-2 animate-spin" size={16} />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Brain size={16} className="mr-2" />
                      AI 分析图表
                    </>
                  )}
                </Button>
                <Button
                  onClick={openExportDialog}
                  disabled={!parseResult?.success}
                  variant="outline"
                  className="flex-1"
                >
                  <Download size={16} className="mr-2" />
                  导出数据
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧：解析结果和 AI 分析 */}
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
                      <CardDescription>
                        <span className="text-xs">
                          使用模型: {aiAnalysis.analysis.model}
                          {aiAnalysis.analysis.is_template && ' • 自定义模板'}
                        </span>
                      </CardDescription>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={downloadAnalysis}
                  >
                    <Download size={16} />
                    下载
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="max-h-[600px] overflow-y-auto custom-scrollbar">
                {aiAnalysis.analysis?.sheets ? (
                  <div className="space-y-4">
                    {Object.entries(aiAnalysis.analysis.sheets).map(([sheetName, result]: [string, any]) => (
                      <div key={sheetName} className="p-4 bg-muted/30 rounded-xl">
                        <div className="flex items-center gap-2 mb-2">
                          <FileSpreadsheet size={16} className="text-primary" />
                          <span className="font-semibold">{sheetName}</span>
                          {result.success ? (
                            <CheckCircle size={16} className="text-emerald-500" />
                          ) : (
                            <AlertCircle size={16} className="text-destructive" />
                          )}
                        </div>
                        {result.success && result.analysis && (
                          <Markdown content={result.analysis} />
                        )}
                        {!result.success && (
                          <p className="text-sm text-destructive">{result.error || '分析失败'}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  aiAnalysis.analysis?.analysis && (
                    <Markdown content={aiAnalysis.analysis.analysis} />
                  )
                )}
              </CardContent>
            </Card>
          )}

          {/* 基于 AI 分析结果的图表 */}
          {analysisCharts && (
            <Card className="border-none shadow-md border-l-4 border-l-indigo-500">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <Brain className="text-indigo-500" size={20} />
                      AI 分析结果图表
                    </CardTitle>
                    {analysisCharts.data_source && (
                      <CardDescription>
                        <span className="text-xs">
                          数据来源: {analysisCharts.data_source === 'ai_analysis' ? 'AI 分析结果' : '其他'}
                        </span>
                      </CardDescription>
                    )}
                  </div>
                </div>
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

          {/* 解析状态 */}
          {parseResult && !aiAnalysis && !analysisCharts && (
            <Card className={cn(
              "border-none shadow-md",
              parseResult.success ? "border-l-4 border-l-emerald-500" : "border-l-4 border-l-destructive"
            )}>
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <div className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center",
                    parseResult.success ? "bg-emerald-500/10 text-emerald-500" : "bg-destructive/10 text-destructive"
                  )}>
                    {parseResult.success ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-lg">
                      {parseResult.success ? '解析成功' : '解析失败'}
                    </h3>
                    {parseResult.metadata && (
                      <div className="flex flex-wrap gap-3 mt-3">
                        {parseResult.metadata.original_filename && (
                          <Badge variant="secondary">{parseResult.metadata.original_filename}</Badge>
                        )}
                        {parseResult.metadata.sheet_count !== undefined && (
                          <Badge variant="outline">
                            {parseResult.metadata.sheet_count} 个工作表
                          </Badge>
                        )}
                        {parseResult.metadata.row_count !== undefined && (
                          <Badge variant="outline">
                            {parseResult.metadata.row_count} 行
                          </Badge>
                        )}
                        {parseResult.metadata.column_count !== undefined && (
                          <Badge variant="outline">
                            {parseResult.metadata.column_count} 列
                          </Badge>
                        )}
                        {parseResult.metadata.file_size && (
                          <Badge variant="outline">
                            {formatFileSize(parseResult.metadata.file_size)}
                          </Badge>
                        )}
                      </div>
                    )}
                    {parseResult.error && (
                      <p className="text-destructive text-sm mt-2">{parseResult.error}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 数据表格 */}
          {parseResult?.success && parseResult.data && (
            <Card className="border-none shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                      <Table className="text-primary" size={20} />
                      数据预览
                    </CardTitle>
                    <CardDescription>
                      {parseResult.data.sheets ? '所有工作表数据' : '工作表数据'}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={openExportDialog}
                    className="gap-2"
                  >
                    <Download size={14} />
                    导出
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {parseResult.data.sheets ? (
                  <div className="space-y-6">
                    {Object.entries(parseResult.data.sheets).map(([sheetName, sheetData]: [string, any]) => (
                      <div key={sheetName} className="border rounded-xl overflow-hidden">
                        <button
                          onClick={() => setExpandedSheet(expandedSheet === sheetName ? null : sheetName)}
                          className="w-full px-6 py-4 flex items-center justify-between bg-muted/30 hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <FileSpreadsheet size={18} className="text-primary" />
                            <span className="font-semibold">{sheetName}</span>
                            <Badge variant="secondary" className="text-xs">
                              {sheetData.row_count || 0} 行
                            </Badge>
                          </div>
                          {expandedSheet === sheetName ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {expandedSheet === sheetName && (
                          <div className="p-4">
                            <DataTable
                              columns={sheetData.columns || []}
                              rows={sheetData.rows || []}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <DataTable
                    columns={parseResult.data.columns || []}
                    rows={parseResult.data.rows || []}
                  />
                )}
              </CardContent>
            </Card>
          )}

          {/* 初始状态 */}
          {!loading && !parseResult && !aiAnalysis && !analysisCharts && (
            <Card className="border-none shadow-md">
              <CardContent className="p-12 flex flex-col items-center justify-center text-center">
                <FileSpreadsheet size={48} className="text-muted-foreground/30 mb-4" />
                <p className="font-semibold text-lg">暂无数据</p>
                <p className="text-sm text-muted-foreground mt-2">
                  上传 Excel 文件后，解析和 AI 分析结果将显示在这里
                </p>
              </CardContent>
            </Card>
          )}

          {/* 加载状态 */}
          {loading && (
            <Card className="border-none shadow-md">
              <CardContent className="p-12 flex flex-col items-center justify-center">
                <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
                <p className="font-semibold">正在解析 Excel 文件...</p>
                <p className="text-sm text-muted-foreground mt-1">请稍候</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 导出对话框 */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>导出 Excel 数据</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* 工作表选择 */}
            <div className="space-y-2">
              <Label>选择工作表</Label>
              <Select value={selectedSheet} onValueChange={(value) => {
                setSelectedSheet(value);
                const sheetColumns = getSheetData(value)?.columns || [];
                setSelectedColumns(new Set(sheetColumns));
                setSelectAll(true);
              }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {parseResult?.data?.sheets ? (
                    Object.keys(parseResult.data.sheets).map(sheetName => (
                      <SelectItem key={sheetName} value={sheetName}>
                        {sheetName}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="默认工作表">默认工作表</SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* 列选择 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>选择列</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={toggleSelectAll}
                >
                  {selectAll ? '取消全选' : '全选'}
                </Button>
              </div>
              <div className="border rounded-lg max-h-60 overflow-y-auto">
                <div className="grid gap-1 p-2">
                  {getSheetData(selectedSheet)?.columns?.map(column => (
                    <div
                      key={column}
                      className={cn(
                        "flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer",
                        selectedColumns.has(column) && "bg-primary/5"
                      )}
                      onClick={() => toggleColumn(column)}
                    >
                      <Checkbox
                        checked={selectedColumns.has(column)}
                        onChange={() => {}}
                      />
                      <span className="text-sm flex-1 truncate">{column}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                已选择 {selectedColumns.size} 列
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setExportDialogOpen(false)}
              disabled={exporting}
            >
              取消
            </Button>
            <Button
              onClick={handleExport}
              disabled={exporting || selectedColumns.size === 0}
            >
              {exporting ? (
                <>
                  <Loader2 className="mr-2 animate-spin" size={16} />
                  导出中...
                </>
              ) : (
                <>
                  <Download size={16} className="mr-2" />
                  导出
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// 数据表格组件
const DataTable: React.FC<{
  columns: string[];
  rows: Record<string, any>[];
}> = ({ columns, rows }) => {
  if (!columns.length || !rows.length) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        暂无数据
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-x-auto">
      <TableComponent>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16 text-center text-muted-foreground">#</TableHead>
            {columns.map((col, idx) => (
              <TableHead key={idx} className="whitespace-nowrap">
                {col || `<列${idx + 1}>`}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, rowIdx) => (
            <TableRow key={rowIdx}>
              <TableCell className="text-center text-muted-foreground font-medium">
                {rowIdx + 1}
              </TableCell>
              {columns.map((col, colIdx) => (
                <TableCell key={colIdx} className="whitespace-nowrap">
                  {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </TableComponent>
      {rows.length > 10 && (
        <div className="p-3 text-center text-sm text-muted-foreground bg-muted/30">
          仅显示前 {rows.length} 行数据
        </div>
      )}
    </div>
  );
};

export default ExcelParse;
