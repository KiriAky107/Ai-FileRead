import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useNavigate, Link } from 'react-router-dom';
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
  Sparkles
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { documentApi, taskApi } from '@/db/api';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

type Document = any;
type FillTask = any;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { profile } = useAuth();
  const [stats, setStats] = useState({ docs: 0, entities: 0, tasks: 0 });
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [recentTasks, setRecentTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile) return;
    const loadData = async () => {
      try {
        const docs = await documentApi.listDocuments((profile as any).id);
        const tasks = await taskApi.listTasks((profile as any).id);
        setRecentDocs(docs.slice(0, 5));
        setRecentTasks(tasks.slice(0, 5));
        
        let entityCount = 0;
        docs.forEach(d => {
          if (d.extracted_entities) entityCount += (d.extracted_entities as any[]).length;
        });

        setStats({
          docs: docs.length,
          entities: entityCount,
          tasks: tasks.length
        });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [profile]);

  return (
    <div className="space-y-8 animate-fade-in">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">
            你好, <span className="text-primary">{((profile as any)?.email)?.split('@')[0] || '用户'}</span> 👋
          </h1>
          <p className="text-muted-foreground">欢迎使用智联文档，今日已为你处理了多个任务。</p>
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
          { label: '已上传文档', value: stats.docs, icon: FileText, color: 'bg-blue-500', trend: '+12% 较上周' },
          { label: '提取实体', value: stats.entities, icon: Layers, color: 'bg-indigo-500', trend: '+25% 较上周' },
          { label: '生成表格', value: stats.tasks, icon: TableProperties, color: 'bg-emerald-500', trend: '+8% 较上周' }
        ].map((stat, i) => (
          <Card key={i} className="border-none shadow-md overflow-hidden group hover:shadow-xl transition-all duration-300">
            <CardContent className="p-0">
              <div className="p-6 flex items-start justify-between">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold tracking-tight">{stat.value}</p>
                  <div className="flex items-center gap-1 text-xs text-emerald-500 font-medium bg-emerald-500/10 px-2 py-1 rounded-full w-fit">
                    <TrendingUp size={12} />
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
              <CardDescription>你最近上传并处理的非结构化文档</CardDescription>
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
                  <div key={doc.id} className="flex items-center gap-4 p-3 rounded-xl border border-transparent hover:border-border hover:bg-muted/30 transition-all group">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center">
                      <FileText size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{doc.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(doc.created_at!), { addSuffix: true, locale: zhCN })}
                      </p>
                    </div>
                    <div className={cn(
                      "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
                      doc.status === 'completed' ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"
                    )}>
                      {doc.status === 'completed' ? '已解析' : '处理中'}
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

        {/* Recent Tasks */}
        <Card className="border-none shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="text-xl flex items-center gap-2">
                <CheckCircle2 className="text-primary" size={20} />
                填表记录
              </CardTitle>
              <CardDescription>自动化生成的表格与汇总结果</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild className="text-primary hover:text-primary/80 hover:bg-primary/5">
              <Link to="/form-fill">查看全部 <ArrowRight size={14} className="ml-1" /></Link>
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4 py-4">
                {[1, 2, 3].map(i => <div key={i} className="h-12 bg-muted rounded-xl animate-pulse" />)}
              </div>
            ) : recentTasks.length > 0 ? (
              <div className="space-y-3">
                {recentTasks.map(task => (
                  <div key={task.id} className="flex items-center gap-4 p-3 rounded-xl border border-transparent hover:border-border hover:bg-muted/30 transition-all">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                      <TableProperties size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{task.templates?.name || '未知模板'}</p>
                      <p className="text-xs text-muted-foreground">
                        关联 {task.document_ids?.length || 0} 个文档 • {formatDistanceToNow(new Date(task.created_at!), { addSuffix: true, locale: zhCN })}
                      </p>
                    </div>
                    <Button variant="ghost" size="icon" className="text-primary h-8 w-8" onClick={() => navigate('/form-fill')}>
                      <ArrowRight size={16} />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                <MessageSquareCode size={48} className="text-muted-foreground/30" />
                <p className="text-muted-foreground italic">暂无任务记录</p>
                <Button variant="outline" size="sm" asChild className="rounded-xl">
                  <Link to="/form-fill">开始填表</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
