import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  FileText,
  TableProperties,
  MessageSquareCode,
  TrendingUp,
  Clock,
  CheckCircle2,
  ArrowRight,
  UploadCloud,
  Layers,
  Sparkles,
  Database,
  FileSpreadsheet,
  RefreshCcw,
  Trash2
} from 'lucide-react';
import { backendApi } from '@/db/backend-api';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

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

type TaskItem = {
  task_id: string;
  status: string;
  created_at: string;
  message?: string;
};

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({ docs: 0, excelFiles: 0, tasks: 0 });
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [recentTasks, setRecentTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      // 获取文档列表
      const docsResult = await backendApi.getDocuments(undefined, 50);
      if (docsResult.success && docsResult.documents) {
        setRecentDocs(docsResult.documents.slice(0, 5));

        // 分类统计
        const docxMdTxt = docsResult.documents.filter((d: DocumentItem) =>
          ['docx', 'md', 'txt'].includes(d.doc_type)
        ).length;
        const xlsx = docsResult.documents.filter((d: DocumentItem) =>
          d.doc_type === 'xlsx'
        ).length;

        setStats({
          docs: docxMdTxt,
          excelFiles: xlsx,
          tasks: 0  // TODO: 后端任务接口
        });
      }
    } catch (err) {
      console.error('加载数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">
            欢迎使用 <span className="text-primary">智联文档</span> 系统 👋
          </h1>
          <p className="text-muted-foreground">基于大语言模型的文档理解与多源数据融合系统</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-xl" asChild>
            <Link to="/documents">管理文档</Link>
          </Button>
          <Button className="rounded-xl shadow-lg shadow-primary/20" asChild>
            <Link to="/assistant" className="gap-2">
              <Sparkles size={18} />
              <span>智能助手</span>
            </Link>
          </Button>
        </div>
      </section>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: '已上传文档', value: stats.docs, icon: FileText, color: 'bg-blue-500', trend: '非结构化文档', link: '/documents' },
          { label: 'Excel 文件', value: stats.excelFiles, icon: FileSpreadsheet, color: 'bg-emerald-500', trend: '结构化数据', link: '/documents' },
          { label: '填表任务', value: stats.tasks, icon: TableProperties, color: 'bg-indigo-500', trend: '待实现', link: '/form-fill' }
        ].map((stat, i) => (
          <Card key={i} className="border-none shadow-md overflow-hidden group hover:shadow-xl transition-all duration-300">
            <CardContent className="p-0">
              <div className="p-6 flex items-start justify-between">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold tracking-tight">{stat.value}</p>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded-full w-fit">
                    <span>{stat.trend}</span>
                  </div>
                </div>
                <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg", stat.color)}>
                  <stat.icon size={24} />
                </div>
              </div>
              <div className="h-1 bg-muted group-hover:bg-primary transition-colors" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Documents */}
        <Card className="border-none shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="text-xl flex items-center gap-2">
                <Clock className="text-primary" size={20} />
                最近上传
              </CardTitle>
              <CardDescription>您最近上传的文档文件</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild className="text-primary hover:text-primary/80 hover:bg-primary/5">
              <Link to="/documents">查看全部 <ArrowRight size={14} className="ml-1" /></Link>
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4 py-4">
                {[1, 2, 3].map(i => <div key={i} className="h-12 bg-muted rounded-xl animate-pulse" />)}
              </div>
            ) : recentDocs.length > 0 ? (
              <div className="space-y-3">
                {recentDocs.map(doc => (
                  <div key={doc.doc_id} className="flex items-center gap-4 p-3 rounded-xl border border-transparent hover:border-border hover:bg-muted/30 transition-all group">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center">
                      <FileText size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{doc.original_filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.doc_type.toUpperCase()} • {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true, locale: zhCN })}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-muted">
                        {doc.doc_type}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 text-destructive hover:bg-destructive/10 transition-opacity"
                        onClick={async (e) => {
                          e.stopPropagation();
                          if (!confirm(`确定要删除 "${doc.original_filename}" 吗？`)) return;
                          try {
                            const result = await backendApi.deleteDocument(doc.doc_id);
                            if (result.success) {
                              setRecentDocs(prev => prev.filter(d => d.doc_id !== doc.doc_id));
                              toast.success('文档已删除');
                            }
                          } catch (err: any) {
                            toast.error(err.message || '删除失败');
                          }
                        }}
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                <UploadCloud size={48} className="text-muted-foreground/30" />
                <p className="text-muted-foreground italic">暂无文档，立即上传开始体验</p>
                <Button variant="outline" size="sm" asChild className="rounded-xl">
                  <Link to="/documents">去上传</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="border-none shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="text-xl flex items-center gap-2">
                <Sparkles className="text-primary" size={20} />
                快速开始
              </CardTitle>
              <CardDescription>选择您需要的服务开始使用</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { title: '上传文档', desc: '支持 docx/md/txt', icon: FileText, link: '/documents', color: 'bg-blue-500' },
                { title: '解析 Excel', desc: '上传并分析数据', icon: FileSpreadsheet, link: '/documents', color: 'bg-emerald-500' },
                { title: '智能填表', desc: '自动填写表格模板', icon: TableProperties, link: '/form-fill', color: 'bg-indigo-500' },
                { title: 'AI 助手', desc: '自然语言交互', icon: MessageSquareCode, link: '/assistant', color: 'bg-amber-500' }
              ].map((item, i) => (
                <Link
                  key={i}
                  to={item.link}
                  className="flex items-center gap-4 p-4 rounded-2xl border border-transparent hover:border-border hover:bg-muted/30 transition-all group"
                >
                  <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-lg", item.color)}>
                    <item.icon size={24} />
                  </div>
                  <div>
                    <p className="font-semibold group-hover:text-primary transition-colors">{item.title}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                  <ArrowRight size={16} className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Status */}
      <Card className="border-none shadow-md">
        <CardHeader className="pb-2">
          <CardTitle className="text-xl flex items-center gap-2">
            <Database className="text-primary" size={20} />
            系统状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-4 rounded-xl bg-muted/30">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <div>
                <p className="font-semibold text-sm">MySQL</p>
                <p className="text-xs text-muted-foreground">结构化数据存储</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-xl bg-muted/30">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <div>
                <p className="font-semibold text-sm">MongoDB</p>
                <p className="text-xs text-muted-foreground">非结构化数据存储</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-xl bg-muted/30">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <div>
                <p className="font-semibold text-sm">Faiss + RAG</p>
                <p className="text-xs text-muted-foreground">向量检索索引</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;