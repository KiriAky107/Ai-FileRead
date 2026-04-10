import React, { useState, useEffect, useCallback } from 'react';
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
  Loader2,
  Files,
  Trash2,
  Eye,
  File
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTemplateFill } from '@/context/TemplateFillContext';

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

const TemplateFill: React.FC = () => {
  const {
    step, setStep,
    templateFile, setTemplateFile,
    templateFields, setTemplateFields,
    sourceFiles, setSourceFiles, addSourceFiles, removeSourceFile,
    sourceFilePaths, setSourceFilePaths,
    templateId, setTemplateId,
    filledResult, setFilledResult,
    reset
  } = useTemplateFill();

  const [loading, setLoading] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<{ name: string; content: string } | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  // 模板拖拽
  const onTemplateDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setTemplateFile(file);
    }
  }, []);

  const { getRootProps: getTemplateProps, getInputProps: getTemplateInputProps, isDragActive: isTemplateDragActive } = useDropzone({
    onDrop: onTemplateDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    multiple: false
  });

  // 源文档拖拽
  const onSourceDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(f => ({
      file: f,
      preview: f.type.startsWith('text/') || f.name.endsWith('.md') ? undefined : undefined
    }));
    addSourceFiles(newFiles);
  }, [addSourceFiles]);

  const { getRootProps: getSourceProps, getInputProps: getSourceInputProps, isDragActive: isSourceDragActive } = useDropzone({
    onDrop: onSourceDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    multiple: true
  });

  const handleJointUploadAndFill = async () => {
    if (!templateFile) {
      toast.error('请先上传模板文件');
      return;
    }

    setLoading(true);

    try {
      // 使用联合上传API
      const result = await backendApi.uploadTemplateAndSources(
        templateFile,
        sourceFiles.map(sf => sf.file)
      );

      if (result.success) {
        setTemplateFields(result.fields || []);
        setTemplateId(result.template_id);
        setSourceFilePaths(result.source_file_paths || []);
        toast.success('文档上传成功，开始智能填表');
        setStep('filling');

        // 自动开始填表
        const fillResult = await backendApi.fillTemplate(
          result.template_id,
          result.fields || [],
          [],  // 使用 source_file_paths 而非 source_doc_ids
          result.source_file_paths || [],
          '请从以下文档中提取相关信息填写表格'
        );

        setFilledResult(fillResult);
        setStep('preview');
        toast.success('表格填写完成');
      }
    } catch (err: any) {
      toast.error('处理失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!templateFile || !filledResult) {
      console.error('handleExport 失败: templateFile=', templateFile, 'filledResult=', filledResult);
      toast.error('数据不完整，无法导出');
      return;
    }

    console.log('=== handleExport 调试 ===');
    console.log('templateFile:', templateFile);
    console.log('templateId:', templateId);
    console.log('filledResult:', filledResult);
    console.log('filledResult.filled_data:', filledResult.filled_data);
    console.log('=========================');

    const ext = templateFile.name.split('.').pop()?.toLowerCase();

    try {
      // 使用新的 fillAndExportTemplate 直接填充原始模板
      const blob = await backendApi.fillAndExportTemplate(
        templateId || '',
        filledResult.filled_data || {},
        ext === 'docx' ? 'docx' : 'xlsx'
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `filled_${templateFile.name}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (err: any) {
      console.error('导出失败:', err);
      toast.error('导出失败: ' + (err.message || '未知错误'));
    }
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['xlsx', 'xls'].includes(ext || '')) {
      return <FileSpreadsheet size={20} className="text-emerald-500" />;
    }
    if (ext === 'docx') {
      return <FileText size={20} className="text-blue-500" />;
    }
    if (['md', 'txt'].includes(ext || '')) {
      return <FileText size={20} className="text-orange-500" />;
    }
    return <File size={20} className="text-gray-500" />;
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
        {step !== 'upload' && (
          <Button variant="outline" className="rounded-xl gap-2" onClick={reset}>
            <RefreshCcw size={18} />
            <span>重新开始</span>
          </Button>
        )}
      </section>

      {/* Step 1: Upload - Joint Upload of Template + Source Docs */}
      {step === 'upload' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Template Upload */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileSpreadsheet className="text-primary" size={20} />
                表格模板
              </CardTitle>
              <CardDescription>
                上传需要填写的 Excel/Word 模板文件
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!templateFile ? (
                <div
                  {...getTemplateProps()}
                  className={cn(
                    "border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group min-h-[200px]",
                    isTemplateDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5"
                  )}
                >
                  <input {...getTemplateInputProps()} />
                  <div className="w-14 h-14 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    {loading ? <Loader2 className="animate-spin" size={28} /> : <Upload size={28} />}
                  </div>
                  <p className="font-medium">
                    {isTemplateDragActive ? '释放以上传' : '点击或拖拽上传模板'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    支持 .xlsx .xls .docx
                  </p>
                </div>
              ) : (
                <div className="flex items-center gap-3 p-4 bg-emerald-500/5 rounded-xl border border-emerald-200">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                    <FileSpreadsheet size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{templateFile.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(templateFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setTemplateFile(null)}>
                    <X size={16} />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Source Documents Upload */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <Files className="text-primary" size={20} />
                源文档
              </CardTitle>
              <CardDescription>
                上传包含数据的源文档（支持多选），可同时上传多个文件
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                {...getSourceProps()}
                className={cn(
                  "border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group min-h-[200px]",
                  isSourceDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5"
                )}
              >
                <input {...getSourceInputProps()} />
                <div className="w-14 h-14 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  {loading ? <Loader2 className="animate-spin" size={28} /> : <Upload size={28} />}
                </div>
                <p className="font-medium">
                  {isSourceDragActive ? '释放以上传' : '点击或拖拽上传源文档'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  支持 .xlsx .xls .docx .md .txt
                </p>
              </div>

              {/* Selected Source Files */}
              {sourceFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {sourceFiles.map((sf, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-muted/50 rounded-xl">
                      {getFileIcon(sf.file.name)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{sf.file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(sf.file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => removeSourceFile(idx)}>
                        <Trash2 size={14} className="text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Action Button */}
          <div className="col-span-1 lg:col-span-2 flex justify-center">
            <Button
              size="lg"
              className="rounded-xl px-12 shadow-lg shadow-primary/20 gap-2"
              disabled={!templateFile || loading}
              onClick={handleJointUploadAndFill}
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>正在处理...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>上传并智能填表</span>
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Filling State */}
      {step === 'filling' && (
        <Card className="border-none shadow-md">
          <CardContent className="py-16 flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
              <Loader2 className="animate-spin text-primary" size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">AI 正在智能分析并填表</h3>
            <p className="text-muted-foreground text-center max-w-md">
              系统正在从 {sourceFiles.length || sourceFilePaths.length} 份文档中检索相关信息...
            </p>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Preview Results */}
      {step === 'preview' && filledResult && (
        <div className="space-y-6">
          <Card className="border-none shadow-md">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle2 className="text-emerald-500" size={20} />
                填表完成
              </CardTitle>
              <CardDescription>
                系统已根据 {sourceFiles.length || sourceFilePaths.length} 份文档自动完成表格填写
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Filled Data Preview */}
              <div className="p-6 bg-muted/30 rounded-2xl">
                <div className="space-y-4">
                  {templateFields.map((field, idx) => {
                    const value = filledResult.filled_data?.[field.name];
                    const displayValue = Array.isArray(value)
                      ? value.filter(v => v && String(v).trim()).join(', ') || '-'
                      : value || '-';
                    return (
                      <div key={idx} className="flex items-center gap-4">
                        <div className="w-40 text-sm font-medium text-muted-foreground">{field.name}</div>
                        <div className="flex-1 p-3 bg-background rounded-xl border">
                          {displayValue}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Source Files Info */}
              <div className="mt-4 flex flex-wrap gap-2">
                {sourceFiles.map((sf, idx) => (
                  <Badge key={idx} variant="outline" className="bg-blue-500/5">
                    {getFileIcon(sf.file.name)}
                    <span className="ml-1">{sf.file.name}</span>
                  </Badge>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex justify-center gap-4 mt-6">
                <Button variant="outline" className="rounded-xl gap-2" onClick={reset}>
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

          {/* Fill Details */}
          {filledResult.fill_details && filledResult.fill_details.length > 0 && (
            <Card className="border-none shadow-md">
              <CardHeader>
                <CardTitle className="text-lg">填写详情</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {filledResult.fill_details.map((detail: any, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-muted/30 rounded-xl text-sm">
                      <div className="w-1 h-1 rounded-full bg-primary mt-2" />
                      <div className="flex-1">
                        <div className="font-medium">{detail.field}</div>
                        <div className="text-muted-foreground text-xs mt-1">
                          来源: {detail.source} | 置信度: {detail.confidence ? (detail.confidence * 100).toFixed(0) + '%' : 'N/A'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{previewDoc?.name || '文档预览'}</DialogTitle>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh]">
            <pre className="text-sm whitespace-pre-wrap">{previewDoc?.content}</pre>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TemplateFill;