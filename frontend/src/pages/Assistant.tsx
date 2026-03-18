import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  MessageSquareCode, 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  RefreshCcw, 
  Trash2, 
  Zap, 
  FileText, 
  TableProperties, 
  ChevronRight,
  ArrowRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { useAuth } from '@/context/AuthContext';
import { supabase } from '@/db/supabase';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

type ChatMessage = any;

const Assistant: React.FC = () => {
  const navigate = useNavigate();
  const { profile } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial message
    if (messages.length === 0) {
      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: '您好！我是智联文档 AI 助手。您可以告诉我您想对文档进行的操作，例如：\n- "帮我列出最近上传的所有 docx 文档"\n- "从 2026 财报文档中提取出关键的利润数据"\n- "帮我创建一个汇总各部门报销单的填表任务"\n\n请问有什么我可以帮您的？',
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
    if (!input.trim() || !profile) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      role: 'user',
      content: input,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await supabase.functions.invoke('chat-assistant', {
        body: { 
          messages: [...messages, userMessage].slice(-6).map(m => ({ role: m.role, content: m.content })),
          userId: (profile as any).id
        }
      });

      if (response.error) throw response.error;

      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'assistant',
        content: response.data.choices[0].message.content,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      toast.error('对话请求失败');
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([messages[0]]);
    toast.success('对话已清空');
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-6 animate-fade-in relative">
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
            <Sparkles className="text-primary animate-pulse" />
            智能交互
          </h1>
          <p className="text-muted-foreground">通过自然语言指令，极速操控您的整个文档数据库。</p>
        </div>
        <Button variant="outline" size="sm" className="rounded-xl gap-2 h-10 border-none bg-card shadow-sm hover:bg-destructive/10 hover:text-destructive" onClick={clearChat}>
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

          <CardFooter className="p-6 bg-white/50 backdrop-blur-xl border-t border-border/50">
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="w-full flex gap-3 bg-muted/30 p-2 rounded-2xl border border-border/50 focus-within:border-primary/50 transition-all shadow-inner"
            >
              <Input 
                placeholder="尝试输入：帮我从 2026 财报文档中提取..." 
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
          </CardFooter>
        </Card>

        {/* Quick Actions Panel */}
        <aside className="w-full lg:w-80 space-y-6">
          <Card className="border-none shadow-lg rounded-3xl bg-gradient-to-br from-primary/5 via-background to-background">
            <CardHeader className="p-6">
              <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary flex items-center gap-2">
                <Zap size={16} />
                快速操作提示
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 space-y-3">
              {[
                { label: '列出所有 Excel', icon: TableProperties, color: 'text-emerald-500' },
                { label: '分析文档库中实体', icon: FileText, color: 'text-blue-500' },
                { label: '自动纠正排版错误', icon: Sparkles, color: 'text-amber-500' },
                { label: '重命名最近上传', icon: ChevronRight, color: 'text-indigo-500' }
              ].map((action, i) => (
                <button 
                  key={i}
                  className="w-full flex items-center gap-3 p-3 rounded-2xl hover:bg-white hover:shadow-md transition-all group text-left border border-transparent hover:border-primary/10"
                  onClick={() => setInput(action.label)}
                >
                  <div className={cn("w-8 h-8 rounded-lg bg-current/10 flex items-center justify-center shrink-0", action.color)}>
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
               <CardTitle className="text-lg font-bold">AI 填表黑科技</CardTitle>
               <CardDescription className="text-indigo-700/70 font-medium">现在支持通过对话发起多源数据自动聚合填表任务。</CardDescription>
             </CardHeader>
             <CardFooter className="p-6 pt-0 relative z-10">
               <Button className="w-full rounded-2xl bg-indigo-600 hover:bg-indigo-700 h-10 shadow-lg shadow-indigo-200" onClick={() => navigate('/form-fill')}>
                 立即开启
               </Button>
             </CardFooter>
          </Card>
        </aside>
      </div>
    </div>
  );
};

export default Assistant;
