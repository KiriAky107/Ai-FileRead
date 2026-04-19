/**
 * PDF 转换页面
 * 支持将 Word、Excel、Txt、Markdown 格式转换为 PDF
 */
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  FileText,
  Upload,
  Download,
  FileSpreadsheet,
  File as FileIcon,
  Loader2,
  CheckCircle,
  AlertCircle,
  Trash2,
  FileDown,
  X,
  Copy
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { backendApi } from '@/db/backend-api';

type FileState = {
  file: File;
  status: 'pending' | 'converting' | 'success' | 'failed';
  progress: number;
  pdfBlob?: Blob;
  error?: string;
};

const SUPPORTED_FORMATS = [
  { ext: 'docx', name: 'Word 文档', icon: FileText, color: 'blue' },
  { ext: 'xlsx', name: 'Excel 表格', icon: FileSpreadsheet, color: 'emerald' },
  { ext: 'txt', name: '文本文件', icon: FileIcon, color: 'gray' },
  { ext: 'md', name: 'Markdown', icon: FileText, color: 'purple' },
];

const PdfConverter: React.FC = () => {
  const [files, setFiles] = useState<FileState[]>([]);
  const [converting, setConverting] = useState(false);
  const [convertedCount, setConvertedCount] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: FileState[] = acceptedFiles.map(file => ({
      file,
      status: 'pending',
      progress: 0,
    }));
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
    },
    multiple: true,
  });

  const handleConvert = async () => {
    if (files.length === 0) {
      toast.error('请先上传文件');
      return;
    }

    setConverting(true);
    setConvertedCount(0);

    const pendingFiles = files.filter(f => f.status === 'pending' || f.status === 'failed');
    let successCount = 0;

    for (let i = 0; i < pendingFiles.length; i++) {
      const fileState = pendingFiles[i];
      const fileIndex = files.findIndex(f => f.file === fileState.file);

      // 更新状态为转换中
      setFiles(prev => prev.map((f, idx) =>
        idx === fileIndex ? { ...f, status: 'converting', progress: 10 } : f
      ));

      try {
        // 获取 PDF blob
        const pdfBlob = await backendApi.convertToPdf(fileState.file);

        // 触发下载
        const url = URL.createObjectURL(pdfBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${fileState.file.name.replace(/\.[^.]+$/, '')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // 保存 blob 以便批量下载
        setFiles(prev => prev.map((f, idx) =>
          idx === fileIndex ? { ...f, status: 'success', progress: 100, pdfBlob } : f
        ));
        successCount++;
        setConvertedCount(successCount);
        toast.success(`${fileState.file.name} 下载已开始`);
      } catch (error: any) {
        setFiles(prev => prev.map((f, idx) =>
          idx === fileIndex ? { ...f, status: 'failed', error: error.message || '转换失败' } : f
        ));
      }
    }

    setConverting(false);
    toast.success(`转换完成：${successCount}/${pendingFiles.length} 个文件`);
  };

  const handleDownload = (fileState: FileState) => {
    if (!fileState.pdfBlob) return;

    const url = URL.createObjectURL(fileState.pdfBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${fileState.file.name.replace(/\.[^.]+$/, '')}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadAll = async () => {
    const successFiles = files.filter(f => f.status === 'success' && f.pdfBlob);

    if (successFiles.length === 0) {
      toast.error('没有可下载的文件');
      return;
    }

    if (successFiles.length === 1) {
      handleDownload(successFiles[0]);
      return;
    }

    // 多个文件，下载 ZIP
    try {
      const zipBlob = await backendApi.batchConvertToPdf(
        successFiles.map(f => f.file)
      );
      const url = URL.createObjectURL(zipBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'converted_pdfs.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success('ZIP 下载开始');
    } catch (error: any) {
      toast.error(error.message || '下载失败');
    }
  };

  const handleRemove = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleClear = () => {
    setFiles([]);
    setConvertedCount(0);
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const format = SUPPORTED_FORMATS.find(f => f.ext === ext);
    if (!format) return FileIcon;
    return format.icon;
  };

  const getFileColor = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const format = SUPPORTED_FORMATS.find(f => f.ext === ext);
    return format?.color || 'gray';
  };

  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-500',
    emerald: 'bg-emerald-500/10 text-emerald-500',
    purple: 'bg-purple-500/10 text-purple-500',
    gray: 'bg-gray-500/10 text-gray-500',
  };

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">文档转 PDF</h1>
          <p className="text-muted-foreground">将 Word、Excel、文本、Markdown 文件转换为 PDF 格式</p>
        </div>
        {files.length > 0 && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClear}>
              <Trash2 size={18} className="mr-2" />
              清空
            </Button>
            <Button onClick={handleDownloadAll} disabled={files.filter(f => f.status === 'success').length === 0}>
              <Download size={18} className="mr-2" />
              打包下载 ({files.filter(f => f.status === 'success').length})
            </Button>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：上传区域 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 上传卡片 */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2">
                <Upload className="text-primary" size={20} />
                上传文件
              </CardTitle>
              <CardDescription>拖拽或点击上传要转换的文件</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                {...getRootProps()}
                className={cn(
                  "border-2 border-dashed rounded-2xl p-8 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
                  isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5",
                  converting && "opacity-50 pointer-events-none"
                )}
              >
                <input {...getInputProps()} />
                <div className="w-14 h-14 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  {converting ? <Loader2 className="animate-spin" size={28} /> : <Upload size={28} />}
                </div>
                <p className="font-semibold text-sm">
                  {isDragActive ? '释放以开始上传' : '点击或拖拽文件到这里'}
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {SUPPORTED_FORMATS.map(format => (
                    <Badge key={format.ext} variant="outline" className={cn("text-xs", colorClasses[format.color])}>
                      {format.name}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 转换按钮 */}
              {files.length > 0 && (
                <Button
                  onClick={handleConvert}
                  disabled={converting || files.filter(f => f.status === 'pending' || f.status === 'failed').length === 0}
                  className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90"
                >
                  {converting ? (
                    <>
                      <Loader2 className="mr-2 animate-spin" size={16} />
                      转换中... ({convertedCount}/{files.filter(f => f.status === 'pending' || f.status === 'failed').length})
                    </>
                  ) : (
                    <>
                      <FileDown className="mr-2" size={16} />
                      开始转换 ({files.filter(f => f.status === 'pending' || f.status === 'failed').length})
                    </>
                  )}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* 格式说明 */}
          <Card className="border-none shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2">
                <FileText className="text-primary" size={20} />
                支持的格式
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {SUPPORTED_FORMATS.map(format => {
                  const Icon = format.icon;
                  return (
                    <div key={format.ext} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                      <div className={cn("w-8 h-8 rounded flex items-center justify-center", colorClasses[format.color])}>
                        <Icon size={16} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">.{format.ext.toUpperCase()}</p>
                        <p className="text-xs text-muted-foreground">{format.name}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧：文件列表 */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-none shadow-md">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2">
                    <FileIcon className="text-primary" size={20} />
                    文件列表
                  </CardTitle>
                  <CardDescription>
                    共 {files.length} 个文件，已转换 {files.filter(f => f.status === 'success').length} 个
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {files.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <FileIcon size={48} className="mx-auto mb-4 opacity-30" />
                  <p>暂无文件，上传文件开始转换</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {files.map((fileState, index) => {
                    const Icon = getFileIcon(fileState.file.name);
                    const color = getFileColor(fileState.file.name);

                    return (
                      <div
                        key={index}
                        className="flex items-center gap-4 p-4 rounded-xl border bg-card hover:bg-muted/30 transition-colors"
                      >
                        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center shrink-0", colorClasses[color])}>
                          <Icon size={20} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold truncate">{fileState.file.name}</p>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {(fileState.file.size / 1024).toFixed(1)} KB
                            </span>
                            {fileState.status === 'pending' && (
                              <Badge variant="secondary" className="text-xs">待转换</Badge>
                            )}
                            {fileState.status === 'converting' && (
                              <Badge variant="default" className="text-xs bg-blue-500">转换中</Badge>
                            )}
                            {fileState.status === 'success' && (
                              <Badge variant="default" className="text-xs bg-emerald-500">已转换</Badge>
                            )}
                            {fileState.status === 'failed' && (
                              <Badge variant="destructive" className="text-xs">失败</Badge>
                            )}
                          </div>
                          {fileState.status === 'converting' && (
                            <div className="mt-1 h-1 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary transition-all duration-300"
                                style={{ width: `${fileState.progress}%` }}
                              />
                            </div>
                          )}
                          {fileState.error && (
                            <p className="text-xs text-destructive mt-1">{fileState.error}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {fileState.status === 'success' && (
                            <>
                              <Button variant="ghost" size="icon" onClick={() => handleDownload(fileState)}>
                                <Download size={18} className="text-emerald-500" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => {
                                  // 复制下载链接到剪贴板
                                  if (fileState.pdfBlob) {
                                    const url = URL.createObjectURL(fileState.pdfBlob);
                                    navigator.clipboard.writeText(url);
                                    toast.success('链接已复制');
                                  }
                                }}
                              >
                                <Copy size={18} />
                              </Button>
                            </>
                          )}
                          {(fileState.status === 'pending' || fileState.status === 'failed') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemove(index)}
                              className="text-destructive hover:bg-destructive/10"
                            >
                              <X size={18} />
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 使用说明 */}
          <Card className="border-none shadow-md bg-gradient-to-br from-primary/5 to-purple-500/5">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2">
                <FileText className="text-primary" size={20} />
                使用说明
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-xs font-bold">1</div>
                  <p>上传要转换的文件，支持 Word(.docx)、Excel(.xlsx)、文本(.txt)、Markdown(.md) 格式</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-xs font-bold">2</div>
                  <p>点击「开始转换」按钮，系统将自动将文件转换为 PDF 格式</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-xs font-bold">3</div>
                  <p>转换完成后，点击下载按钮获取 PDF 文件，或使用「打包下载」一次性下载所有文件</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PdfConverter;
