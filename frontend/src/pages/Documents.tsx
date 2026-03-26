import React, { useState, useEffect, useCallback } from 'react';
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
  Database,
  FileSpreadsheet,
  File
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

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

  const onDrop = async (acceptedFiles: File[]) => {
    setUploading(true);
    const uploaded: string[] = [];

    try {
      for (const file of acceptedFiles) {
        try {
          const result = await backendApi.uploadDocument(file);
          if (result.task_id) {
            uploaded.push(file.name);

            // 轮询任务状态
            const checkStatus = async () => {
              let attempts = 0;
              while (attempts < 30) {
                try {
                  const status = await backendApi.getTaskStatus(result.task_id);
                  if (status.status === 'success') {
                    toast.success(`文件 ${file.name} 处理完成`);
                    loadDocuments();
                    return;
                  } else if (status.status === 'failure') {
                    toast.error(`文件 ${file.name} 处理失败: ${status.error}`);
                    return;
                  }
                } catch (e) {
                  console.error('检查状态失败', e);
                }
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
              }
              toast.error(`文件 ${file.name} 处理超时`);
            };
            checkStatus();
          }
        } catch (err: any) {
          toast.error(`上传失败: ${file.name} - ${err.message}`);
        }
      }

      if (uploaded.length > 0) {
        toast.success(`已提交 ${uploaded.length} 个文件进行处理`);
      }
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt']
    }
  });

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

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">文档中心</h1>
          <p className="text-muted-foreground">上传并管理您的非结构化文档（docx/md/txt），系统将自动进行深度理解与信息提取。</p>
        </div>
        <Button variant="outline" className="rounded-xl gap-2" onClick={loadDocuments}>
          <RefreshCcw size={18} />
          <span>刷新</span>
        </Button>
      </section>

      {/* Upload Zone - For non-Excel documents */}
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-3xl p-12 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group",
          isDragActive ? "border-primary bg-primary/5 scale-[1.01]" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/5",
          uploading && "opacity-50 pointer-events-none"
        )}
      >
        <input {...getInputProps()} />
        <div className="w-20 h-20 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
          {uploading ? <RefreshCcw className="animate-spin" size={40} /> : <Upload size={40} />}
        </div>
        <div className="space-y-2 max-w-sm">
          <p className="text-xl font-bold tracking-tight">
            {isDragActive ? '释放以开始上传' : '点击或拖拽文件到这里'}
          </p>
          <p className="text-sm text-muted-foreground">
            支持 docx, md, txt 格式文档，系统将自动识别关键信息并存入 MongoDB
          </p>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-200">
            <FileText size={14} className="mr-1" /> Word 文档
          </Badge>
          <Badge variant="outline" className="bg-purple-500/10 text-purple-600 border-purple-200">
            <FileText size={14} className="mr-1" /> Markdown
          </Badge>
          <Badge variant="outline" className="bg-gray-500/10 text-gray-600 border-gray-200">
            <File size={14} className="mr-1" /> 文本文件
          </Badge>
        </div>
      </div>

      {/* Filter & Search */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索文档名称..."
            className="pl-9 h-11 bg-card rounded-xl border-none shadow-sm focus-visible:ring-primary"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2 items-center text-sm text-muted-foreground">
          <Database size={16} />
          <span>{documents.length} 个文档</span>
        </div>
      </div>

      {/* Document List */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-2xl" />
          ))
        ) : filteredDocs.length > 0 ? (
          filteredDocs.map((doc) => (
            <Card key={doc.doc_id} className="border-none shadow-sm overflow-hidden group hover:shadow-md transition-all">
              <div className="flex flex-col">
                <div className="p-6 flex flex-col md:flex-row md:items-center gap-6">
                  <div className={cn(
                    "w-14 h-14 rounded-2xl flex items-center justify-center shrink-0",
                    doc.doc_type === 'xlsx' ? "bg-emerald-500/10 text-emerald-500" :
                    doc.doc_type === 'docx' ? "bg-blue-500/10 text-blue-500" :
                    "bg-gray-500/10 text-gray-500"
                  )}>
                    {getDocIcon(doc.doc_type)}
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold text-lg truncate">{doc.original_filename}</h3>
                      <Badge variant="secondary" className="bg-muted text-muted-foreground text-[10px] uppercase tracking-widest">
                        {doc.doc_type}
                      </Badge>
                      {doc.metadata?.columns && (
                        <Badge variant="outline" className="text-[10px]">
                          {doc.metadata.columns.length} 列
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {format(new Date(doc.created_at), 'yyyy-MM-dd HH:mm')}
                      </span>
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="rounded-xl gap-2 text-primary hover:bg-primary/10"
                      onClick={() => setExpandedDoc(expandedDoc === doc.doc_id ? null : doc.doc_id)}
                    >
                      {expandedDoc === doc.doc_id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      <span>{expandedDoc === doc.doc_id ? '收起详情' : '查看详情'}</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-lg text-destructive hover:bg-destructive/10"
                      onClick={() => handleDelete(doc.doc_id)}
                    >
                      <Trash2 size={18} />
                    </Button>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedDoc === doc.doc_id && (
                  <div className="px-6 pb-6 pt-2 border-t border-dashed animate-in slide-in-from-top-2 duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 bg-muted/30 rounded-xl">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">文件信息</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">文件名</span>
                            <span className="font-medium">{doc.original_filename}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">文件大小</span>
                            <span className="font-medium">{(doc.file_size / 1024).toFixed(2)} KB</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">文档类型</span>
                            <span className="font-medium">{doc.doc_type.toUpperCase()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">创建时间</span>
                            <span className="font-medium">{format(new Date(doc.created_at), 'yyyy-MM-dd HH:mm:ss')}</span>
                          </div>
                        </div>
                      </div>

                      {doc.metadata?.columns && doc.metadata.columns.length > 0 && (
                        <div className="p-4 bg-muted/30 rounded-xl">
                          <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">表格结构</h4>
                          <div className="flex flex-wrap gap-2">
                            {doc.metadata.columns.map((col: string, idx: number) => (
                              <Badge key={idx} variant="outline" className="bg-background">
                                {col}
                              </Badge>
                            ))}
                          </div>
                          {doc.metadata.row_count && (
                            <p className="mt-3 text-sm text-muted-foreground">
                              共 {doc.metadata.row_count} 行数据
                            </p>
                          )}
                        </div>
                      )}

                      <div className="p-4 bg-muted/30 rounded-xl col-span-full">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">存储位置</h4>
                        <div className="flex items-center gap-2 text-sm">
                          <Database size={16} className="text-muted-foreground" />
                          <span className="text-muted-foreground">
                            {doc.doc_type === 'xlsx' ? 'MySQL 数据库（结构化数据）' : 'MongoDB 数据库（非结构化文档）'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))
        ) : (
          <div className="py-20 flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-24 h-24 rounded-full bg-muted flex items-center justify-center text-muted-foreground/30">
              <FileText size={48} />
            </div>
            <div className="space-y-1">
              <p className="text-xl font-bold">空空如也</p>
              <p className="text-muted-foreground">快去上传一份文档，体验 AI 的智能解析能力吧！</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Documents;