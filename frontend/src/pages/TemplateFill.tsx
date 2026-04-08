import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  TableProperties,
  Upload,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  Download,
  Clock,
  Sparkles,
  X,
  FilePlus,
  RefreshCcw,
  ChevronDown,
  ChevronUp,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { backendApi } from '@/db/backend-api';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

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

type TemplateField = {
  cell: string;
  name: string;
  field_type: string;
  required: boolean;
  hint?: string;
};

const TemplateFill: React.FC = () => {
  const [step, setStep] = useState<'upload-template' | 'select-source' | 'preview' | 'filling'>('upload-template');
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateFields, setTemplateFields] = useState<TemplateField[]>([]);
  const [sourceDocs, setSourceDocs] = useState<DocumentItem[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [filling, setFilling] = useState(false);
  const [filledResult, setFilledResult] = useState<any>(null);

  // Load available source documents
  useEffect(() => {
    loadSourceDocuments();
  }, []);

  const loadSourceDocuments = async () => {
    setLoading(true);
    try {
      const result = await backendApi.getDocuments(undefined, 100);
      if (result.success) {
        // Filter to only non-Excel documents that can be used as data sources
        const docs = (result.documents || []).filter((d: DocumentItem) =>
          ['docx', 'md', 'txt', 'xlsx'].includes(d.doc_type)
        );
        setSourceDocs(docs);
      }
    } catch (err: any) {
      toast.error('加载数据源失败');
    } finally {
      setLoading(false);
    }
  };

  const onTemplateDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['xlsx', 'xls', 'docx'].includes(ext || '')) {
      toast.error('仅支持 xlsx/xls/docx 格式的模板文件');
      return;
    }

    setTemplateFile(file);
    setLoading(true);

    try {
      const result = await backendApi.uploadTemplate(file);
      if (result.success) {
        setTemplateFields(result.fields || []);
        setStep('select-source');
        toast.success('模板上传成功');
      }
    } catch (err: any) {
      toast.error('模板上传失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const { getRootProps: getTemplateProps, getInputProps: getTemplateInputProps, isDragActive: isTemplateDragActive } = useDropzone({
    onDrop: onTemplateDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1
  });

  const handleFillTemplate = async () => {
    if (!templateFile || selectedDocs.length === 0) {
      toast.error('请选择数据源文档');
      return;
    }

    setFilling(true);
    setStep('filling');

    try {
      // 调用后端填表接口，传递选中的文档ID
      const result = await backendApi.fillTemplate(
        'temp-template-id',
        templateFields,
        selectedDocs  // 传递源文档ID列表
      );
      setFilledResult(result);
      setStep('preview');
      toast.success('表格填写完成');
    } catch (err: any) {
      toast.error('填表失败: ' + (err.message || '未知错误'));
      setStep('select-source');
    } finally {
      setFilling(false);
    }
  };

  const handleExport = async () => {
    if (!templateFile || !filledResult) return;

    try {
      const blob = await backendApi.exportFilledTemplate('temp', filledResult.filled_data || {}, 'xlsx');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `filled_${templateFile.name}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (err: any) {
      toast.error('导出失败: ' + (err.message || '未知错误'));
    }
  };

  const resetFlow = () => {
    setStep('upload-template');
    setTemplateFile(null);
    setTemplateFields([]);
    setSelectedDocs([]);
    setFilledResult(null);
  };

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">智能填表</h1>
          <p className="text-muted-foreground">
            根据您的表格模板，自动聚合多源文档信息进行精准填充
          </p>
        </div>
        {step !== 'upload-template' && (
          <Button variant="outline" className="rounded-xl gap-2" onClick={resetFlow}>
            <RefreshCcw size={18} />
            <span>重新开始</span>
          </Button>
        )}
      </section>

      {/* Progress Steps */}
      <div className="flex items-center justify-center gap-4">
        {['上传模板', '选择数据源', '填写预览'].map((label, idx) => {
          const stepIndex = ['upload-template', 'select-source', 'preview'].indexOf(step);
          const isActive = idx <= stepIndex;
          const isCurrent = idx === stepIndex;

          return (
            <React.Fragment key={idx}>
              <div className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-full transition-all",
                isActive ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
              )}>
                <div className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                  isCurrent ? "bg-white/20" : ""
                )}>
                  {idx + 1}
                </div>
                <span className="text-sm font-medium">{label}</span>
              </div>
              {idx < 2 && (
                <div className={cn(
                  "w-12 h-0.5",
                  idx < stepIndex ? "bg-primary" : "bg-muted"
                )} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Step 1: Upload Template */}
      {step === 'upload-template' && (
        <div
          {...getTemplateProps()}
          className={cn(
            "border-2 border-dashed rounded-3xl p-16 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
            isTemplateDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5"
          )}
        >
          <input {...getTemplateInputProps()} />
          <div className="w-20 h-20 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            {loading ? <Loader2 className="animate-spin" size={40} /> : <Upload size={40} />}
          </div>
          <div className="space-y-2 max-w-md">
            <p className="text-xl font-bold tracking-tight">
              {isTemplateDragActive ? '释放以开始上传' : '点击或拖拽上传表格模板'}
            </p>
            <p className="text-sm text-muted-foreground">
              支持 Excel (.xlsx, .xls) 或 Word (.docx) 格式的表格模板
            </p>
          </div>
          <div className="mt-6 flex gap-3">
            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-200">
              <FileSpreadsheet size={14} className="mr-1" /> Excel 模板
            </Badge>
            <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-200">
              <FileText size={14} className="mr-1" /> Word 模板
            </Badge>
          </div>
        </div>
      )}

      {/* Step 2: Select Source Documents */}
      {step === 'select-source' && (
        <div className="space-y-6">
          {/* Template Info */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileSpreadsheet className="text-primary" size={20} />
                已上传模板
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                  <FileSpreadsheet size={24} />
                </div>
                <div className="flex-1">
                  <p className="font-bold">{templateFile?.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {templateFields.length} 个字段待填写
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setStep('upload-template')}>
                  重新选择
                </Button>
              </div>

              {/* Template Fields Preview */}
              <div className="mt-4 p-4 bg-muted/30 rounded-xl">
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">待填写字段</p>
                <div className="flex flex-wrap gap-2">
                  {templateFields.map((field, idx) => (
                    <Badge key={idx} variant="outline" className="bg-background">
                      {field.name}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Source Documents Selection */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="text-primary" size={20} />
                选择数据源文档
              </CardTitle>
              <CardDescription>
                从已上传的文档中选择作为填表的数据来源，支持 Excel 和非结构化文档
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
                </div>
              ) : sourceDocs.length > 0 ? (
                <div className="space-y-3">
                  {sourceDocs.map(doc => (
                    <div
                      key={doc.doc_id}
                      className={cn(
                        "flex items-center gap-4 p-4 rounded-xl border-2 transition-all cursor-pointer",
                        selectedDocs.includes(doc.doc_id)
                          ? "border-primary bg-primary/5"
                          : "border-border hover:bg-muted/30"
                      )}
                      onClick={() => {
                        setSelectedDocs(prev =>
                          prev.includes(doc.doc_id)
                            ? prev.filter(id => id !== doc.doc_id)
                            : [...prev, doc.doc_id]
                        );
                      }}
                    >
                      <div className={cn(
                        "w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all",
                        selectedDocs.includes(doc.doc_id)
                          ? "border-primary bg-primary text-white"
                          : "border-muted-foreground/30"
                      )}>
                        {selectedDocs.includes(doc.doc_id) && <CheckCircle2 size={14} />}
                      </div>
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center",
                        doc.doc_type === 'xlsx' ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
                      )}>
                        {doc.doc_type === 'xlsx' ? <FileSpreadsheet size={20} /> : <FileText size={20} />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold truncate">{doc.original_filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.doc_type.toUpperCase()} • {format(new Date(doc.created_at), 'yyyy-MM-dd')}
                        </p>
                      </div>
                      {doc.metadata?.columns && (
                        <Badge variant="outline" className="text-xs">
                          {doc.metadata.columns.length} 列
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <FileText size={48} className="mx-auto mb-4 opacity-30" />
                  <p>暂无数据源文档，请先上传文档</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Action Button */}
          <div className="flex justify-center">
            <Button
              size="lg"
              className="rounded-xl px-8 shadow-lg shadow-primary/20 gap-2"
              disabled={selectedDocs.length === 0 || filling}
              onClick={handleFillTemplate}
            >
              {filling ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>AI 正在分析并填表...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>开始智能填表</span>
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Preview Results */}
      {step === 'preview' && filledResult && (
        <Card className="border-none shadow-md">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle2 className="text-emerald-500" size={20} />
              填表完成
            </CardTitle>
            <CardDescription>
              系统已根据 {selectedDocs.length} 份文档自动完成表格填写
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Filled Data Preview */}
            <div className="p-6 bg-muted/30 rounded-2xl">
              <div className="space-y-4">
                {templateFields.map((field, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div className="w-32 text-sm font-medium text-muted-foreground">{field.name}</div>
                    <div className="flex-1 p-3 bg-background rounded-xl border">
                      {(filledResult.filled_data || {})[field.name] || '-'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center gap-4">
              <Button variant="outline" className="rounded-xl gap-2" onClick={resetFlow}>
                <RefreshCcw size={18} />
                <span>继续填表</span>
              </Button>
              <Button className="rounded-xl gap-2 shadow-lg shadow-primary/20" onClick={handleExport}>
                <Download size={18} />
                <span>导出结果</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filling State */}
      {step === 'filling' && (
        <Card className="border-none shadow-md">
          <CardContent className="py-16 flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
              <Loader2 className="animate-spin text-primary" size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">AI 正在智能分析并填表</h3>
            <p className="text-muted-foreground text-center max-w-md">
              系统正在从 {selectedDocs.length} 份文档中检索相关信息，生成字段描述，并使用 RAG 增强填写准确性...
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TemplateFill;