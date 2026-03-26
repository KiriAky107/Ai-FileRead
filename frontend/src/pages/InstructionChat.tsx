import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  Trash2,
  RefreshCcw,
  FileText,
  TableProperties,
  ChevronRight,
  ArrowRight,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { backendApi } from '@/db/backend-api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
};

const InstructionChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial welcome message
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `您好！我是智联文档 AI 助手。

我可以帮您完成以下操作：

📄 **文档管理**
- "帮我列出最近上传的所有文档"
- "删除三天前的 docx 文档"

📊 **Excel 分析**
- "分析一下最近上传的 Excel 文件"
- "帮我统计销售报表中的数据"

📝 **智能填表**
- "根据员工信息表创建一个考勤汇总表"
- "用财务文档填充报销模板"

请告诉我您想做什么？`,
          created_at: new Date().toISOString()
        }
      ]);
    }
  }, []);

  useEffect(() => {
    // Scroll to bottom
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // TODO: 后端对话接口，暂用模拟响应
      await new Promise(resolve => setTimeout(resolve, 1500));

      // 简单的命令解析演示
      const userInput = userMessage.content.toLowerCase();
      let response = '';

      if (userInput.includes('列出') || userInput.includes('列表')) {
        const result = await backendApi.getDocuments(undefined, 10);
        if (result.success && result.documents && result.documents.length > 0) {
          response = `已为您找到 ${result.documents.length} 个文档：\n\n`;
          result.documents.slice(0, 5).forEach((doc: any, idx: number) => {
            response += `${idx + 1}. **${doc.original_filename}** (${doc.doc_type.toUpperCase()})\n`;
            response += `   - 大小: ${(doc.file_size / 1024).toFixed(1)} KB\n`;
            response += `   - 时间: ${new Date(doc.created_at).toLocaleDateString()}\n\n`;
          });
          if (result.documents.length > 5) {
            response += `...还有 ${result.documents.length - 5} 个文档`;
          }
        } else {
          response = '暂未找到已上传的文档，您可以先上传一些文档试试。';
        }
      } else if (userInput.includes('分析') || userInput.includes('excel') || userInput.includes('报表')) {
        response = `好的，我可以帮您分析 Excel 文件。

请告诉我：
1. 您想分析哪个 Excel 文件？
2. 需要什么样的分析？（数据摘要/统计分析/图表生成）

或者您可以直接告诉我您想从数据中了解什么，我来为您生成分析。`;
      } else if (userInput.includes('填表') || userInput.includes('模板')) {
        response = `好的，要进行智能填表，我需要：

1. **上传表格模板** - 您要填写的表格模板文件（Excel 或 Word 格式）
2. **选择数据源** - 包含要填写内容的源文档

您可以去【智能填表】页面完成这些操作，或者告诉我您具体想填什么类型的表格，我来指导您操作。`;
      } else if (userInput.includes('删除')) {
        response = `要删除文档，请告诉我：

- 要删除的文件名是什么？
- 或者您可以到【文档中心】页面手动选择并删除文档

⚠️ 删除操作不可恢复，请确认后再操作。`;
      } else if (userInput.includes('帮助') || userInput.includes('help')) {
        response = `**我可以帮您完成以下操作：**

📄 **文档管理**
- 列出/搜索已上传的文档
- 查看文档详情和元数据
- 删除不需要的文档

📊 **Excel 处理**
- 分析 Excel 文件内容
- 生成数据统计和图表
- 导出处理后的数据

📝 **智能填表**
- 上传表格模板
- 从文档中提取信息填入模板
- 导出填写完成的表格

📋 **任务历史**
- 查看历史处理任务
- 重新执行或导出结果

请直接告诉我您想做什么！`;
      } else {
        response = `我理解您想要： "${input.trim()}"

目前我还在学习如何更好地理解您的需求。您可以尝试：

1. **上传文档** - 去【文档中心】上传 docx/md/txt 文件
2. **分析 Excel** - 去【Excel解析】上传并分析 Excel 文件
3. **智能填表** - 去【智能填表】创建填表任务

或者您可以更具体地描述您想做的事情，我会尽力帮助您！`;
      }

      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'assistant',
        content: response,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      toast.error('请求失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([messages[0]]);
    toast.success('对话已清空');
  };

  const quickActions = [
    { label: '列出所有文档', icon: FileText, action: () => setInput('列出所有已上传的文档') },
    { label: '分析 Excel 数据', icon: TableProperties, action: () => setInput('分析一下 Excel 文件') },
    { label: '智能填表', icon: Sparkles, action: () => setInput('我想进行智能填表') },
    { label: '帮助', icon: Sparkles, action: () => setInput('帮助') }
  ];

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-6 animate-fade-in relative">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
            <Sparkles className="text-primary animate-pulse" />
            智能助手
          </h1>
          <p className="text-muted-foreground">通过自然语言指令，极速操控您的整个文档数据库。</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl gap-2 h-10 border-none bg-card shadow-sm hover:bg-destructive/10 hover:text-destructive"
          onClick={clearChat}
        >
          <Trash2 size={16} />
          <span>清除历史</span>
        </Button>
      </section>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        {/* Chat Area */}
        <Card className="flex-1 flex flex-col border-none shadow-xl overflow-hidden rounded-3xl bg-card/50 backdrop-blur-sm">
          <ScrollArea className="flex-1 p-6" ref={scrollAreaRef}>
            <div className="space-y-8 pb-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "flex gap-4 max-w-[85%]",
                    m.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
                  )}
                >
                  <div className={cn(
                    "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg",
                    m.role === 'user' ? "bg-primary text-primary-foreground" : "bg-white text-primary border border-primary/20"
                  )}>
                    {m.role === 'user' ? <User size={20} /> : <Bot size={22} />}
                  </div>
                  <div className={cn(
                    "space-y-2 p-5 rounded-3xl",
                    m.role === 'user'
                      ? "bg-primary text-primary-foreground shadow-xl shadow-primary/20 rounded-tr-none"
                      : "bg-white border border-border/50 shadow-md rounded-tl-none"
                  )}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">
                      {m.content}
                    </p>
                    <span className={cn(
                      "text-[10px] block opacity-50 font-bold tracking-widest",
                      m.role === 'user' ? "text-right" : "text-left"
                    )}>
                      {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-4 mr-auto max-w-[85%] animate-pulse">
                  <div className="w-10 h-10 rounded-2xl bg-muted flex items-center justify-center shrink-0 border border-border/50">
                    <Bot size={22} className="text-muted-foreground" />
                  </div>
                  <div className="p-5 rounded-3xl rounded-tl-none bg-muted/50 border border-border/50">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          <CardContent className="p-6 bg-white/50 backdrop-blur-xl border-t border-border/50">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="w-full flex gap-3 bg-muted/30 p-2 rounded-2xl border border-border/50 focus-within:border-primary/50 transition-all shadow-inner"
            >
              <Input
                placeholder="尝试输入：帮我分析最近上传的 Excel 文件..."
                className="flex-1 bg-transparent border-none focus-visible:ring-0 shadow-none h-12 text-base font-medium"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <Button
                type="submit"
                size="icon"
                className="w-12 h-12 rounded-xl bg-primary hover:scale-105 transition-all shadow-lg shadow-primary/20"
                disabled={loading || !input.trim()}
              >
                <Send size={20} />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Quick Actions Panel */}
        <aside className="w-full lg:w-80 space-y-6">
          <Card className="border-none shadow-lg rounded-3xl bg-gradient-to-br from-primary/5 via-background to-background">
            <CardHeader className="p-6">
              <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary flex items-center gap-2">
                <Sparkles size={16} />
                快捷操作
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 space-y-3">
              {quickActions.map((action, i) => (
                <button
                  key={i}
                  className="w-full flex items-center gap-3 p-3 rounded-2xl hover:bg-white hover:shadow-md transition-all group text-left border border-transparent hover:border-primary/10"
                  onClick={action.action}
                >
                  <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <action.icon size={16} />
                  </div>
                  <span className="text-sm font-semibold truncate group-hover:text-primary transition-colors">{action.label}</span>
                  <ArrowRight size={14} className="ml-auto opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="border-none shadow-lg rounded-3xl bg-gradient-to-br from-indigo-500/10 to-blue-500/10 overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-20">
              <Sparkles size={100} />
            </div>
            <CardHeader className="p-6 relative z-10">
              <CardTitle className="text-lg font-bold">功能说明</CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 relative z-10 space-y-4 text-sm text-muted-foreground">
              <div className="flex items-start gap-2">
                <FileText size={16} className="mt-0.5 text-blue-500 shrink-0" />
                <span>上传 docx/md/txt 文档到 MongoDB</span>
              </div>
              <div className="flex items-start gap-2">
                <TableProperties size={16} className="mt-0.5 text-emerald-500 shrink-0" />
                <span>上传 xlsx 文档到 MySQL</span>
              </div>
              <div className="flex items-start gap-2">
                <Sparkles size={16} className="mt-0.5 text-indigo-500 shrink-0" />
                <span>使用 RAG 智能检索和填表</span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
};

export default InstructionChat;