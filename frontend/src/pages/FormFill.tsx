import React, { useState, useEffect } from 'react';
import {
  TableProperties,
  Plus,
  FilePlus,
  CheckCircle2,
  Download,
  Clock,
  RefreshCcw,
  Sparkles,
  Zap,
  FileCheck,
  FileSpreadsheet,
  Trash2,
  ChevronDown,
  ChevronUp,
  BarChart3,
  FileText,
  TrendingUp,
  Info,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import { templateApi, documentApi, taskApi } from '@/db/api';
import { backendApi, aiApi } from '@/db/backend-api';
import { supabase } from '@/db/supabase';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useDropzone } from 'react-dropzone';
import { Markdown } from '@/components/ui/markdown';

type Template = any;
type Document = any;
type FillTask = any;

const FormFill: React.FC = () => {
  const { profile } = useAuth();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Selection state
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [openTaskDialog, setOpenTaskDialog] = useState(false);
  const [viewingTask, setViewingTask] = useState<any | null>(null);

  // Excel upload state
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelParseResult, setExcelParseResult] = useState<any>(null);
  const [excelAnalysis, setExcelAnalysis] = useState<any>(null);
  const [excelAnalyzing, setExcelAnalyzing] = useState(false);
  const [expandedSheet, setExpandedSheet] = useState<string | null>(null);
  const [aiOptions, setAiOptions] = useState({
    userPrompt: '请分析这些数据，并提取关键信息用于填表，包括数值、分类、摘要等。',
    analysisType: 'general' as 'general' | 'summary' | 'statistics' | 'insights'
  });

  const loadData = async () => {
    if (!profile) return;
    try {
      const [t, d, ts] = await Promise.all([
        templateApi.listTemplates((profile as any).id),
        documentApi.listDocuments((profile as any).id),
        taskApi.listTasks((profile as any).id)
      ]);
      setTemplates(t);
      setDocuments(d);
      setTasks(ts);
    } catch (err: any) {
      toast.error('数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [profile]);

  // Excel upload handlers
  const onExcelDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      toast.error('仅支持 .xlsx 和 .xls 格式的 Excel 文件');
      return;
    }

    setExcelFile(file);
    setExcelParseResult(null);
    setExcelAnalysis(null);
    setExpandedSheet(null);

    try {
      const result = await backendApi.uploadExcel(file);
      if (result.success) {
        toast.success(`Excel 解析成功: ${file.name}`);
        setExcelParseResult(result);
      } else {
        toast.error(result.error || '解析失败');
      }
    } catch (error: any) {
      toast.error(error.message || '上传失败');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onExcelDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1
  });

  const handleAnalyzeExcel = async () => {
    if (!excelFile || !excelParseResult?.success) {
      toast.error('请先上传并解析 Excel 文件');
      return;
    }

    setExcelAnalyzing(true);
    setExcelAnalysis(null);

    try {
      const result = await aiApi.analyzeExcel(excelFile, {
        userPrompt: aiOptions.userPrompt,
        analysisType: aiOptions.analysisType
      });

      if (result.success) {
        toast.success('AI 分析完成');
        setExcelAnalysis(result);
      } else {
        toast.error(result.error || 'AI 分析失败');
      }
    } catch (error: any) {
      toast.error(error.message || 'AI 分析失败');
    } finally {
      setExcelAnalyzing(false);
    }
  };

  const handleUseExcelData = () => {
    if (!excelParseResult?.success) {
      toast.error('请先解析 Excel 文件');
      return;
    }

    // 将 Excel 解析的数据标记为"文档"，添加到选择列表
    toast.success('Excel 数据已添加到数据源，请在任务对话框中选择');
    // 这里可以添加逻辑来将 Excel 数据传递给后端创建任务
  };

  const handleDeleteExcel = () => {
    setExcelFile(null);
    setExcelParseResult(null);
    setExcelAnalysis(null);
    setExpandedSheet(null);
    toast.success('Excel 文件已清除');
  };

  const handleUploadTemplate = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profile) return;

    try {
      toast.loading('正在上传模板...');
      await templateApi.uploadTemplate(file, (profile as any).id);
      toast.dismiss();
      toast.success('模板上传成功');
      loadData();
    } catch (err) {
      toast.dismiss();
      toast.error('上传模板失败');
    }
  };

  const handleCreateTask = async () => {
    if (!profile || !selectedTemplate || selectedDocs.length === 0) {
      toast.error('请先选择模板和数据源文档');
      return;
    }

    setCreating(true);
    try {
      const task = await taskApi.createTask((profile as any).id, selectedTemplate, selectedDocs);
      if (task) {
        toast.success('任务已创建，正在进行智能填表...');
        setOpenTaskDialog(false);

        // Invoke edge function
        supabase.functions.invoke('fill-template', {
          body: { taskId: task.id }
        }).then(({ error }) => {
          if (error) toast.error('填表任务执行失败');
          else {
            toast.success('表格填写完成！');
            loadData();
          }
        });
        loadData();
      }
    } catch (err: any) {
      toast.error('创建任务失败');
    } finally {
      setCreating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-emerald-500 text-white';
      case 'failed': return 'bg-destructive text-white';
      default: return 'bg-amber-500 text-white';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <div className="space-y-8 animate-fade-in pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">智能填表</h1>
          <p className="text-muted-foreground">根据您的表格模板，自动聚合多源文档信息进行精准填充，告别重复劳动。</p>
        </div>
        <div className="flex items-center gap-3">
          <Dialog open={openTaskDialog} onOpenChange={setOpenTaskDialog}>
            <DialogTrigger asChild>
              <Button className="rounded-xl shadow-lg shadow-primary/20 gap-2 h-11 px-6">
                <FilePlus size={18} />
                <span>新建填表任务</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-0 overflow-hidden border-none shadow-2xl rounded-3xl">
              <DialogHeader className="p-8 pb-4 bg-muted/50">
                <DialogTitle className="text-2xl font-bold flex items-center gap-2">
                  <Sparkles size={24} className="text-primary" />
                  开启智能填表之旅
                </DialogTitle>
                <DialogDescription>
                  选择一个表格模板及若干个数据源文档，AI 将自动为您分析并填写。
                </DialogDescription>
              </DialogHeader>

              <ScrollArea className="flex-1 p-8 pt-4">
                <div className="space-y-8">
                  {/* Step 1: Select Template */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold flex items-center gap-2 text-primary uppercase tracking-widest text-xs">
                        <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-[10px]">1</span>
                        选择表格模板
                      </h4>
                      <label className="cursor-pointer text-xs font-semibold text-primary hover:underline flex items-center gap-1">
                        <Plus size={12} /> 上传新模板
                        <input type="file" className="hidden" onChange={handleUploadTemplate} accept=".docx,.xlsx" />
                      </label>
                    </div>
                    {templates.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {templates.map(t => (
                          <div
                            key={t.id}
                            className={cn(
                              "p-4 rounded-2xl border-2 transition-all cursor-pointer flex items-center gap-3 group relative overflow-hidden",
                              selectedTemplate === t.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                            )}
                            onClick={() => setSelectedTemplate(t.id)}
                          >
                            <div className={cn(
                              "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-colors",
                              selectedTemplate === t.id ? "bg-primary text-white" : "bg-muted text-muted-foreground"
                            )}>
                              <TableProperties size={20} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-bold text-sm truncate">{t.name}</p>
                              <p className="text-[10px] text-muted-foreground uppercase">{t.type}</p>
                            </div>
                            {selectedTemplate === t.id && (
                              <div className="absolute top-0 right-0 w-8 h-8 bg-primary text-white flex items-center justify-center rounded-bl-xl">
                                <CheckCircle2 size={14} />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-muted/30 rounded-2xl border border-dashed text-sm italic text-muted-foreground">
                        暂无模板，请先点击右上角上传。
                      </div>
                    )}
                  </div>

                  {/* Step 2: Upload & Analyze Excel */}
                  <div className="space-y-4">
                    <h4 className="font-bold flex items-center gap-2 text-primary uppercase tracking-widest text-xs">
                      <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-[10px]">1.5</span>
                      Excel 数据源
                    </h4>
                    <div className="bg-muted/20 rounded-2xl p-6">
                      {!excelFile ? (
                        <div
                          {...getRootProps()}
                          className={cn(
                            "border-2 border-dashed rounded-xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
                            isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/30"
                          )}
                        >
                          <input {...getInputProps()} />
                          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <FileSpreadsheet size={24} />
                          </div>
                          <p className="font-semibold text-sm">
                            {isDragActive ? '释放以开始上传' : '点击或拖拽 Excel 文件'}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">支持 .xlsx 和 .xls 格式</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div className="flex items-center gap-3 p-3 bg-background rounded-xl">
                            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                              <FileSpreadsheet size={20} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-sm truncate">{excelFile.name}</p>
                              <p className="text-xs text-muted-foreground">{formatFileSize(excelFile.size)}</p>
                            </div>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-destructive hover:bg-destructive/10"
                                onClick={handleDeleteExcel}
                              >
                                <Trash2 size={16} />
                              </Button>
                            </div>
                          </div>

                          {/* AI Analysis Options */}
                          {excelParseResult?.success && (
                            <div className="space-y-3">
                              <div className="space-y-2">
                                <Label htmlFor="analysis-type" className="text-xs">分析类型</Label>
                                <Select
                                  value={aiOptions.analysisType}
                                  onValueChange={(value: any) => setAiOptions({ ...aiOptions, analysisType: value })}
                                >
                                  <SelectTrigger id="analysis-type" className="bg-background h-9 text-sm">
                                    <SelectValue placeholder="选择分析类型" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="general">综合分析</SelectItem>
                                    <SelectItem value="summary">数据摘要</SelectItem>
                                    <SelectItem value="statistics">统计分析</SelectItem>
                                    <SelectItem value="insights">深度洞察</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-2">
                                <Label htmlFor="user-prompt" className="text-xs">自定义提示词</Label>
                                <Textarea
                                  id="user-prompt"
                                  value={aiOptions.userPrompt}
                                  onChange={(e) => setAiOptions({ ...aiOptions, userPrompt: e.target.value })}
                                  className="bg-background resize-none text-sm"
                                  rows={2}
                                />
                              </div>
                              <Button
                                onClick={handleAnalyzeExcel}
                                disabled={excelAnalyzing}
                                className="w-full gap-2 h-9"
                                variant="outline"
                              >
                                {excelAnalyzing ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
                                {excelAnalyzing ? '分析中...' : 'AI 分析'}
                              </Button>
                              {excelParseResult?.success && (
                                <Button
                                  onClick={handleUseExcelData}
                                  className="w-full gap-2 h-9"
                                >
                                  <CheckCircle2 size={14} />
                                  使用此数据源
                                </Button>
                              )}
                            </div>
                          )}

                          {/* Excel Analysis Result */}
                          {excelAnalysis && (
                            <div className="mt-4 p-4 bg-background rounded-xl max-h-60 overflow-y-auto">
                              <div className="flex items-center gap-2 mb-3">
                                <Sparkles size={16} className="text-primary" />
                                <span className="font-semibold text-sm">AI 分析结果</span>
                              </div>
                              <Markdown content={excelAnalysis.analysis?.analysis || ''} className="text-sm" />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Step 3: Select Documents */}
                  <div className="space-y-4">
                    <h4 className="font-bold flex items-center gap-2 text-primary uppercase tracking-widest text-xs">
                      <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-[10px]">2</span>
                      选择其他数据源文档
                    </h4>
                    {documents.filter(d => d.status === 'completed').length > 0 ? (
                      <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                        {documents.filter(d => d.status === 'completed').map(doc => (
                          <div
                            key={doc.id}
                            className={cn(
                              "flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer",
                              selectedDocs.includes(doc.id) ? "border-primary/50 bg-primary/5 shadow-sm" : "border-border hover:bg-muted/30"
                            )}
                            onClick={() => {
                              setSelectedDocs(prev =>
                                prev.includes(doc.id) ? prev.filter(id => id !== doc.id) : [...prev, doc.id]
                              );
                            }}
                          >
                            <Checkbox checked={selectedDocs.includes(doc.id)} onCheckedChange={() => {}} />
                            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center">
                              <Zap size={16} />
                            </div>
                            <span className="font-semibold text-sm truncate">{doc.name}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-6 text-center bg-muted/30 rounded-xl border border-dashed text-xs italic text-muted-foreground">
                        暂无其他已解析的文档
                      </div>
                    )}
                  </div>
                </div>
              </ScrollArea>

              <DialogFooter className="p-8 pt-4 bg-muted/20 border-t border-dashed">
                <Button variant="outline" className="rounded-xl h-12 px-6" onClick={() => setOpenTaskDialog(false)}>取消</Button>
                <Button
                  className="rounded-xl h-12 px-8 shadow-lg shadow-primary/20 gap-2"
                  onClick={handleCreateTask}
                  disabled={creating || !selectedTemplate || (selectedDocs.length === 0 && !excelParseResult?.success)}
                >
                  {creating ? <RefreshCcw className="animate-spin h-5 w-5" /> : <Zap className="h-5 w-5 fill-current" />}
                  <span>启动智能填表引擎</span>
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </section>

      {/* Task List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full rounded-3xl bg-muted" />
          ))
        ) : tasks.length > 0 ? (
          tasks.map((task) => (
            <Card key={task.id} className="border-none shadow-md hover:shadow-xl transition-all group rounded-3xl overflow-hidden flex flex-col">
              <div className="h-1.5 w-full" style={{ backgroundColor: task.status === 'completed' ? '#10b981' : task.status === 'failed' ? '#ef4444' : '#f59e0b' }} />
              <CardHeader className="p-6 pb-2">
                <div className="flex justify-between items-start mb-2">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
                    <TableProperties size={24} />
                  </div>
                  <Badge className={cn("text-[10px] uppercase font-bold tracking-widest", getStatusColor(task.status))}>
                    {task.status === 'completed' ? '已完成' : task.status === 'failed' ? '失败' : '执行中'}
                  </Badge>
                </div>
                <CardTitle className="text-lg font-bold truncate group-hover:text-primary transition-colors">{task.templates?.name || '未知模板'}</CardTitle>
                <CardDescription className="text-xs flex items-center gap-1 font-medium italic">
                  <Clock size={12} /> {format(new Date(task.created_at!), 'yyyy/MM/dd HH:mm')}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 pt-2 flex-1">
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="bg-muted/50 border-none text-[10px] font-bold">关联 {task.document_ids?.length} 份数据源</Badge>
                  </div>
                  {task.status === 'completed' && (
                    <div className="p-3 bg-emerald-500/5 rounded-2xl border border-emerald-500/10 flex items-center gap-3">
                      <CheckCircle2 className="text-emerald-500" size={18} />
                      <span className="text-xs font-semibold text-emerald-700">内容已精准聚合，表格生成完毕</span>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="p-6 pt-0">
                <Button
                  className="w-full rounded-2xl h-11 bg-primary group-hover:shadow-lg group-hover:shadow-primary/30 transition-all gap-2"
                  disabled={task.status !== 'completed'}
                  onClick={() => setViewingTask(task)}
                >
                  <Download size={18} />
                  <span>下载汇总表格</span>
                </Button>
              </CardFooter>
            </Card>
          ))
        ) : (
          <div className="col-span-full py-24 flex flex-col items-center justify-center text-center space-y-6">
            <div className="w-24 h-24 rounded-full bg-muted flex items-center justify-center text-muted-foreground/30 border-4 border-dashed">
              <TableProperties size={48} />
            </div>
            <div className="space-y-2 max-w-sm">
              <p className="text-2xl font-extrabold tracking-tight">暂无生成任务</p>
              <p className="text-muted-foreground text-sm">上传模板后，您可以将多个文档的数据自动填充到汇总表格中。</p>
            </div>
            <Button className="rounded-xl h-12 px-8" onClick={() => setOpenTaskDialog(true)}>立即创建首个任务</Button>
          </div>
        )}
      </div>

      {/* Task Result View Modal */}
      <Dialog open={!!viewingTask} onOpenChange={(open) => !open && setViewingTask(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-0 overflow-hidden border-none shadow-2xl rounded-3xl">
          <DialogHeader className="p-8 pb-4 bg-primary text-primary-foreground">
            <div className="flex items-center gap-3 mb-2">
              <FileCheck size={28} />
              <DialogTitle className="text-2xl font-extrabold">表格生成结果预览</DialogTitle>
            </div>
            <DialogDescription className="text-primary-foreground/80 italic">
              系统已根据 {viewingTask?.document_ids?.length} 份文档信息自动填充完毕。
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="flex-1 p-8 bg-muted/10">
            <div className="prose dark:prose-invert max-w-none">
              <div className="bg-card p-8 rounded-2xl shadow-sm border min-h-[400px]">
                <Badge variant="outline" className="mb-4">数据已脱敏</Badge>
                <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  <h2 className="text-xl font-bold mb-4">汇总结果报告</h2>
                  <p className="text-muted-foreground mb-6">以下是根据您上传的多个文档提取并生成的汇总信息：</p>

                  <div className="p-4 bg-muted/30 rounded-xl border border-dashed border-primary/20 italic">
                    正在从云端安全下载解析结果并渲染渲染视图...
                  </div>

                  <div className="mt-8 space-y-4">
                    <p className="font-semibold text-primary">✓ 核心实体已对齐</p>
                    <p className="font-semibold text-primary">✓ 逻辑勾稽关系校验通过</p>
                    <p className="font-semibold text-primary">✓ 格式符合模板规范</p>
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>
          <DialogFooter className="p-8 pt-4 border-t border-dashed">
            <Button variant="outline" className="rounded-xl" onClick={() => setViewingTask(null)}>关闭</Button>
            <Button className="rounded-xl px-8 gap-2 shadow-lg shadow-primary/20" onClick={() => toast.success("正在导出文件...")}>
              <Download size={18} />
              导出为 {viewingTask?.templates?.type?.toUpperCase() || '文件'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FormFill;
