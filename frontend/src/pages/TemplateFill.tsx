import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  File,
  Plus
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
    sourceDocIds, setSourceDocIds, addSourceDocId, removeSourceDocId,
    templateId, setTemplateId,
    filledResult, setFilledResult,
    reset
  } = useTemplateFill();

  const [loading, setLoading] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<{ name: string; content: string } | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [sourceMode, setSourceMode] = useState<'upload' | 'select'>('upload');
  const [uploadedDocuments, setUploadedDocuments] = useState<DocumentItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const sourceFileInputRef = useRef<HTMLInputElement>(null);

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
  const onSourceDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ['xlsx', 'xls', 'docx', 'md', 'txt'].includes(ext || '');
    });
    if (files.length > 0) {
      addSourceFiles(files.map(f => ({ file: f })));
    }
  }, [addSourceFiles]);

  const handleSourceFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      addSourceFiles(files.map(f => ({ file: f })));
      toast.success(`已添加 ${files.length} 个文件`);
    }
    e.target.value = '';
  };

  // 仅添加源文档不上传
  const handleAddSourceFiles = () => {
    if (sourceFiles.length === 0) {
      toast.error('请先选择源文档');
      return;
    }
    toast.success(`已添加 ${sourceFiles.length} 个源文档，可继续添加更多`);
  };

  // 加载已上传文档
  const loadUploadedDocuments = useCallback(async () => {
    setDocsLoading(true);
    try {
      const result = await backendApi.getDocuments(undefined, 100);
      if (result.success) {
        // 过滤可作为数据源的文档类型
        const docs = (result.documents || []).filter((d: DocumentItem) =>
          ['docx', 'md', 'txt', 'xlsx', 'xls'].includes(d.doc_type)
        );
        setUploadedDocuments(docs);
      }
    } catch (err: any) {
      console.error('加载文档失败:', err);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  // 删除文档
  const handleDeleteDocument = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除该文档吗？')) return;
    try {
      const result = await backendApi.deleteDocument(docId);
      if (result.success) {
        setUploadedDocuments(prev => prev.filter(d => d.doc_id !== docId));
        removeSourceDocId(docId);
        toast.success('文档已删除');
      } else {
        toast.error(result.message || '删除失败');
      }
    } catch (err: any) {
      toast.error('删除失败: ' + (err.message || '未知错误'));
    }
  };

  useEffect(() => {
    if (sourceMode === 'select') {
      loadUploadedDocuments();
    }
  }, [sourceMode, loadUploadedDocuments]);

  const handleJointUploadAndFill = async () => {
    if (!templateFile) {
      toast.error('请先上传模板文件');
      return;
    }

    // 检查是否选择了数据源
    if (sourceMode === 'upload' && sourceFiles.length === 0) {
      toast.error('请上传源文档或从已上传文档中选择');
      return;
    }
    if (sourceMode === 'select' && sourceDocIds.length === 0) {
      toast.error('请选择源文档');
      return;
    }

    setLoading(true);

    try {
      if (sourceMode === 'select') {
        // 使用已上传文档作为数据源
        const result = await backendApi.uploadTemplate(templateFile);

        if (result.success) {
          setTemplateFields(result.fields || []);
          setTemplateId(result.template_id || 'temp');
          toast.success('开始智能填表');
          setStep('filling');

          // 使用 source_doc_ids 进行填表
          const fillResult = await backendApi.fillTemplate(
            result.template_id || 'temp',
            result.fields || [],
            sourceDocIds,
            [],
            '请从以下文档中提取相关信息填写表格'
          );

          setFilledResult(fillResult);
          setStep('preview');
          toast.success('表格填写完成');
        }
      } else {
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
            [],
            result.source_file_paths || [],
            '请从以下文档中提取相关信息填写表格'
          );

          setFilledResult(fillResult);
          setStep('preview');
          toast.success('表格填写完成');
        }
      }
    } catch (err: any) {
      toast.error('处理失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!templateFile || !filledResult) return;

    try {
      const ext = templateFile.name.split('.').pop()?.toLowerCase();
      const exportFormat = (ext === 'docx') ? 'docx' : 'xlsx';
      // 对于 Word 模板，如果已有填写后的文件（已填入表格单元格），传递其路径以便直接下载
      const filledFilePath = (ext === 'docx' && filledResult.filled_file_path)
        ? filledResult.filled_file_path
        : undefined;
      const blob = await backendApi.exportFilledTemplate(
        templateId || 'temp',
        filledResult.filled_data || {},
        exportFormat,
        filledFilePath
      );
      const ext_match = templateFile.name.match(/\.([^.])+$/);
      const baseName = ext_match ? templateFile.name.replace(ext_match[0], '') : templateFile.name;
      const downloadName = `filled_${baseName}.${exportFormat}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadName;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (err: any) {
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
                选择包含数据的源文档作为填表依据
              </CardDescription>
              {/* Source Mode Tabs */}
              <div className="flex gap-2 mt-2">
                <Button
                  variant={sourceMode === 'upload' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSourceMode('upload')}
                >
                  <Upload size={14} className="mr-1" />
                  上传文件
                </Button>
                <Button
                  variant={sourceMode === 'select' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSourceMode('select')}
                >
                  <Files size={14} className="mr-1" />
                  从文档中心选择
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {sourceMode === 'upload' ? (
                <>
                  <div className="border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group min-h-[200px] border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5">
                    <input
                      id="source-file-input"
                      type="file"
                      multiple={true}
                      accept=".xlsx,.xls,.docx,.md,.txt"
                      onChange={handleSourceFileSelect}
                      className="hidden"
                    />
                    <label htmlFor="source-file-input" className="cursor-pointer flex flex-col items-center">
                      <div className="w-14 h-14 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        {loading ? <Loader2 className="animate-spin" size={28} /> : <Upload size={28} />}
                      </div>
                      <p className="font-medium">
                        点击上传源文档
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        支持 .xlsx .xls .docx .md .txt
                      </p>
                    </label>
                  </div>
                  <div
                    onDragOver={(e) => { e.preventDefault(); }}
                    onDrop={onSourceDrop}
                    className="mt-2 text-center text-xs text-muted-foreground"
                  >
                    或拖拽文件到此处
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
                      <div className="flex justify-center pt-2">
                        <Button variant="outline" size="sm" onClick={() => document.getElementById('source-file-input')?.click()}>
                          <Plus size={14} className="mr-1" />
                          继续添加更多文档
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* Uploaded Documents Selection */}
                  {docsLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map(i => (
                        <Skeleton key={i} className="h-16 w-full rounded-xl" />
                      ))}
                    </div>
                  ) : uploadedDocuments.length > 0 ? (
                    <div className="space-y-2">
                      {sourceDocIds.length > 0 && (
                        <div className="flex items-center justify-between p-3 bg-primary/5 rounded-xl border border-primary/20">
                          <span className="text-sm font-medium">已选择 {sourceDocIds.length} 个文档</span>
                          <Button variant="ghost" size="sm" onClick={() => loadUploadedDocuments()}>
                            <RefreshCcw size={14} className="mr-1" />
                            刷新列表
                          </Button>
                        </div>
                      )}
                      <div className="max-h-[300px] overflow-y-auto space-y-2">
                        {uploadedDocuments.map((doc) => (
                          <div
                            key={doc.doc_id}
                            className={cn(
                              "flex items-center gap-3 p-3 rounded-xl border-2 transition-all cursor-pointer",
                              sourceDocIds.includes(doc.doc_id)
                                ? "border-primary bg-primary/5"
                                : "border-border hover:bg-muted/30"
                            )}
                            onClick={() => {
                              if (sourceDocIds.includes(doc.doc_id)) {
                                removeSourceDocId(doc.doc_id);
                              } else {
                                addSourceDocId(doc.doc_id);
                              }
                            }}
                          >
                            <div className={cn(
                              "w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all shrink-0",
                              sourceDocIds.includes(doc.doc_id)
                                ? "border-primary bg-primary text-white"
                                : "border-muted-foreground/30"
                            )}>
                              {sourceDocIds.includes(doc.doc_id) && <CheckCircle2 size={14} />}
                            </div>
                            {getFileIcon(doc.original_filename)}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                              <p className="text-xs text-muted-foreground">
                                {doc.doc_type.toUpperCase()} • {format(new Date(doc.created_at), 'yyyy-MM-dd')}
                              </p>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => handleDeleteDocument(doc.doc_id, e)}
                              className="shrink-0"
                            >
                              <Trash2 size={14} className="text-red-500" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Files size={32} className="mx-auto mb-2 opacity-30" />
                      <p className="text-sm">暂无可用的已上传文档</p>
                    </div>
                  )}
                </>
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
              系统正在从 {sourceFiles.length || sourceFilePaths.length || sourceDocIds.length || 0} 份文档中检索相关信息...
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
                系统已根据 {filledResult.source_doc_count || sourceFiles.length || sourceFilePaths.length || sourceDocIds.length} 份文档自动完成表格填写
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
                        {detail.warning && (
                          <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-xs">
                            ⚠️ {detail.warning}
                          </div>
                        )}
                        {detail.values && detail.values.length > 1 && !detail.warning && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            多值: {detail.values.join(', ')}
                          </div>
                        )}
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