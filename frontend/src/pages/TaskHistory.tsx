import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCcw,
  Download,
  FileText,
  FileSpreadsheet,
  Loader2,
  ChevronDown,
  ChevronUp,
  Trash2,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { backendApi } from '@/db/backend-api';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

type Task = {
  task_id: string;
  status: 'pending' | 'processing' | 'success' | 'failure';
  created_at: string;
  completed_at?: string;
  message?: string;
  result?: any;
  error?: string;
  task_type?: string;
};

const TaskHistory: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  // Mock data for demonstration
  useEffect(() => {
    // 模拟任务数据，实际应该从后端获取
    setTasks([
      {
        task_id: 'task-001',
        status: 'success',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        completed_at: new Date(Date.now() - 3500000).toISOString(),
        task_type: 'document_parse',
        message: '文档解析完成',
        result: {
          doc_id: 'doc-001',
          filename: 'report_q1_2026.docx',
          extracted_fields: ['标题', '作者', '日期', '金额']
        }
      },
      {
        task_id: 'task-002',
        status: 'success',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        completed_at: new Date(Date.now() - 7100000).toISOString(),
        task_type: 'excel_analysis',
        message: 'Excel 分析完成',
        result: {
          filename: 'sales_data.xlsx',
          row_count: 1250,
          charts_generated: 3
        }
      },
      {
        task_id: 'task-003',
        status: 'processing',
        created_at: new Date(Date.now() - 600000).toISOString(),
        task_type: 'template_fill',
        message: '正在填充表格...'
      },
      {
        task_id: 'task-004',
        status: 'failure',
        created_at: new Date(Date.now() - 86400000).toISOString(),
        completed_at: new Date(Date.now() - 86390000).toISOString(),
        task_type: 'document_parse',
        message: '解析失败',
        error: '文件格式不支持或文件已损坏'
      }
    ]);
    setLoading(false);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-emerald-500 text-white text-[10px]"><CheckCircle2 size={12} className="mr-1" />成功</Badge>;
      case 'failure':
        return <Badge className="bg-destructive text-white text-[10px]"><XCircle size={12} className="mr-1" />失败</Badge>;
      case 'processing':
        return <Badge className="bg-amber-500 text-white text-[10px]"><Loader2 size={12} className="mr-1 animate-spin" />处理中</Badge>;
      default:
        return <Badge className="bg-gray-500 text-white text-[10px]"><Clock size={12} className="mr-1" />等待</Badge>;
    }
  };

  const getTaskTypeLabel = (type?: string) => {
    switch (type) {
      case 'document_parse':
        return '文档解析';
      case 'excel_analysis':
        return 'Excel 分析';
      case 'template_fill':
        return '智能填表';
      case 'rag_index':
        return 'RAG 索引';
      default:
        return '未知任务';
    }
  };

  const getTaskIcon = (type?: string) => {
    switch (type) {
      case 'document_parse':
      case 'rag_index':
        return <FileText size={20} />;
      case 'excel_analysis':
        return <FileSpreadsheet size={20} />;
      default:
        return <Clock size={20} />;
    }
  };

  const handleRetry = async (taskId: string) => {
    toast.info('任务重试功能开发中...');
  };

  const handleDelete = async (taskId: string) => {
    setTasks(prev => prev.filter(t => t.task_id !== taskId));
    toast.success('任务已删除');
  };

  const stats = {
    total: tasks.length,
    success: tasks.filter(t => t.status === 'success').length,
    processing: tasks.filter(t => t.status === 'processing').length,
    failure: tasks.filter(t => t.status === 'failure').length
  };

  return (
    <div className="space-y-8 pb-10">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight">任务历史</h1>
          <p className="text-muted-foreground">查看和管理您所有的文档处理任务记录</p>
        </div>
        <Button variant="outline" className="rounded-xl gap-2" onClick={() => window.location.reload()}>
          <RefreshCcw size={18} />
          <span>刷新</span>
        </Button>
      </section>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '总任务数', value: stats.total, icon: Clock, color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { label: '成功', value: stats.success, icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
          { label: '处理中', value: stats.processing, icon: Loader2, color: 'text-amber-500', bg: 'bg-amber-500/10' },
          { label: '失败', value: stats.failure, icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10' }
        ].map((stat, i) => (
          <Card key={i} className="border-none shadow-sm">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", stat.bg)}>
                <stat.icon size={24} className={stat.color} />
              </div>
              <div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Task List */}
      <div className="space-y-4">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-2xl" />
          ))
        ) : tasks.length > 0 ? (
          tasks.map((task) => (
            <Card key={task.task_id} className="border-none shadow-sm overflow-hidden">
              <div className="flex flex-col">
                <div className="p-6 flex flex-col md:flex-row md:items-center gap-4">
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center shrink-0",
                    task.status === 'success' ? "bg-emerald-500/10 text-emerald-500" :
                    task.status === 'failure' ? "bg-destructive/10 text-destructive" :
                    "bg-amber-500/10 text-amber-500"
                  )}>
                    {task.status === 'processing' ? (
                      <Loader2 size={24} className="animate-spin" />
                    ) : (
                      getTaskIcon(task.task_type)
                    )}
                  </div>

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h3 className="font-bold">{getTaskTypeLabel(task.task_type)}</h3>
                      {getStatusBadge(task.status)}
                      <Badge variant="outline" className="text-[10px]">
                        {task.task_id}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {task.message || '任务执行中...'}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {format(new Date(task.created_at), 'yyyy-MM-dd HH:mm:ss')}
                      </span>
                      {task.completed_at && (
                        <span>
                          耗时: {Math.round((new Date(task.completed_at).getTime() - new Date(task.created_at).getTime()) / 1000)} 秒
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {task.status === 'failure' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl gap-1 h-9"
                        onClick={() => handleRetry(task.task_id)}
                      >
                        <RefreshCcw size={14} />
                        <span>重试</span>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-lg text-destructive hover:bg-destructive/10"
                      onClick={() => handleDelete(task.task_id)}
                    >
                      <Trash2 size={18} />
                    </Button>
                    {task.result && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="rounded-xl gap-1 h-9"
                        onClick={() => setExpandedTask(expandedTask === task.task_id ? null : task.task_id)}
                      >
                        {expandedTask === task.task_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        <span>详情</span>
                      </Button>
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedTask === task.task_id && task.result && (
                  <div className="px-6 pb-6 pt-2 border-t border-dashed animate-in slide-in-from-top-2 duration-300">
                    <div className="p-4 bg-muted/30 rounded-xl">
                      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">任务结果</p>
                      <pre className="text-sm whitespace-pre-wrap font-mono">
                        {JSON.stringify(task.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Error Details */}
                {task.status === 'failure' && task.error && (
                  <div className="px-6 pb-6 pt-2 border-t border-dashed">
                    <div className="p-4 bg-destructive/5 rounded-xl border border-destructive/20">
                      <p className="text-xs font-bold uppercase tracking-widest text-destructive mb-3 flex items-center gap-2">
                        <AlertCircle size={14} />
                        错误详情
                      </p>
                      <p className="text-sm text-destructive">{task.error}</p>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))
        ) : (
          <div className="py-20 flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-24 h-24 rounded-full bg-muted flex items-center justify-center text-muted-foreground/30">
              <Clock size={48} />
            </div>
            <div className="space-y-1">
              <p className="text-xl font-bold">暂无任务记录</p>
              <p className="text-muted-foreground">上传文档或创建填表任务后，这里会显示处理记录</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskHistory;