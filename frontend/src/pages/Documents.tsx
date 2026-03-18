import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  FileText, 
  Upload, 
  Search, 
  Filter, 
  Trash2, 
  RefreshCcw, 
  CheckCircle2, 
  Clock,
  ChevronDown,
  ChevronUp,
  Database
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import { documentApi } from '@/db/api';
import { supabase } from '@/db/supabase';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

type Document = any;
type ExtractedEntity = any;

const Documents: React.FC = () => {
  const { profile } = useAuth();
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const loadDocuments = useCallback(async () => {
    if (!profile) return;
    try {
      const data = await documentApi.listDocuments((profile as any).id);
      setDocuments(data);
    } catch (err: any) {
      toast.error('加载文档失败');
    } finally {
      setLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const onDrop = async (acceptedFiles: File[]) => {
    if (!profile) return;
    setUploading(true);
    try {
      for (const file of acceptedFiles) {
        const doc = await documentApi.uploadDocument(file, (profile as any).id);
        if (doc) {
          toast.success(`文件 ${file.name} 上传成功，开始智能提取...`);
          // Call Edge Function
          supabase.functions.invoke('process-document', {
            body: { documentId: doc.id }
          }).then(({ error }) => {
            if (error) toast.error(`提取失败: ${file.name}`);
            else {
              toast.success(`提取完成: ${file.name}`);
              loadDocuments();
            }
          });
        }
      }
      loadDocuments();
    } catch (err: any) {
      toast.error('上传失败');
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt']
    }
  });

  const handleDelete = async (id: string) => {
    try {
      const { error } = await supabase.from('documents').delete().eq('id', id);
      if (error) throw error;
      setDocuments(prev => prev.filter(d => d.id !== id));
      toast.success('文档已删除');
    } catch (err) {
      toast.error('删除失败');
    }
  };

  const filteredDocs = documents.filter(doc => 
    doc.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">文档中心</h1>
          <p className="text-muted-foreground">上传并管理您的非结构化文档，系统将自动进行深度理解与提取。</p>
        </div>
      </section>

      {/* Upload Zone */}
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
            支持 docx, xlsx, md, txt 格式文档，系统将自动识别关键信息
          </p>
        </div>
        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/20 backdrop-blur-[2px] rounded-3xl">
            <Badge variant="secondary" className="px-4 py-2 gap-2 text-sm shadow-lg border-primary/20">
              正在极速上传并分析文档...
            </Badge>
          </div>
        )}
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
        <div className="flex gap-2">
          <Button variant="outline" className="h-11 rounded-xl px-4 gap-2 border-none bg-card shadow-sm hover:bg-primary/5 hover:text-primary" onClick={() => toast.info('过滤器暂未启用，请直接搜索。')}>
            <Filter size={18} />
            <span>筛选</span>
          </Button>
          <Button 
            variant="outline" 
            className="h-11 rounded-xl px-4 gap-2 border-none bg-card shadow-sm hover:bg-primary/5 hover:text-primary"
            onClick={loadDocuments}
          >
            <RefreshCcw size={18} />
          </Button>
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
            <Card key={doc.id} className="border-none shadow-sm overflow-hidden group hover:shadow-md transition-all">
              <div className="flex flex-col">
                <div className="p-6 flex flex-col md:flex-row md:items-center gap-6">
                  <div className="w-14 h-14 rounded-2xl bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
                    <FileText size={28} />
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold text-lg truncate">{doc.name}</h3>
                      <Badge variant="secondary" className="bg-muted text-muted-foreground text-[10px] uppercase tracking-widest">{doc.type}</Badge>
                      <Badge className={cn(
                        "text-[10px] uppercase font-bold",
                        doc.status === 'completed' ? "bg-emerald-500 text-white" : "bg-amber-500 text-white"
                      )}>
                        {doc.status === 'completed' ? '已解析' : '处理中'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1"><Clock size={14} /> {format(new Date(doc.created_at!), 'yyyy-MM-dd HH:mm')}</span>
                      <span className="flex items-center gap-1 text-primary"><Database size={14} /> {doc.extracted_entities?.length || 0} 个识别项</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="rounded-xl gap-2 text-primary hover:bg-primary/10"
                      onClick={() => setExpandedDoc(expandedDoc === doc.id ? null : doc.id)}
                    >
                      {expandedDoc === doc.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      <span>{expandedDoc === doc.id ? '收起详情' : '查看结果'}</span>
                    </Button>
                    <Button variant="ghost" size="icon" className="rounded-lg text-destructive hover:bg-destructive/10" onClick={() => handleDelete(doc.id)}>
                      <Trash2 size={18} />
                    </Button>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedDoc === doc.id && (
                  <div className="px-6 pb-6 pt-2 border-t border-dashed animate-in slide-in-from-top-2 duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {doc.extracted_entities && doc.extracted_entities.length > 0 ? (
                        doc.extracted_entities.map((entity: any) => (
                          <div key={entity.id} className="p-3 bg-muted/30 rounded-xl border border-border/50 flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-primary uppercase tracking-wider">{entity.entity_type}</span>
                            <span className="text-sm font-semibold">{entity.entity_value}</span>
                            {entity.confidence && (
                              <div className="mt-1 w-full bg-muted h-1 rounded-full overflow-hidden">
                                <div 
                                  className="bg-primary h-full transition-all duration-1000" 
                                  style={{ width: `${entity.confidence * 100}%` }}
                                />
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="col-span-full py-6 text-center text-muted-foreground italic text-sm">
                          暂无识别到的关键信息，请点击重新提取。
                        </div>
                      )}
                    </div>
                    <div className="mt-6 p-4 bg-muted/50 rounded-xl">
                      <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">文档原文摘要</h4>
                      <p className="text-sm line-clamp-4 text-muted-foreground">
                        {doc.content_text || '尚未提取原文内容...'}
                      </p>
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
