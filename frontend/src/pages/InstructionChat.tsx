import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Trash2, FileText, TableProperties, ArrowRight, Search, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Markdown } from '@/components/ui/markdown';
import { backendApi } from '@/db/backend-api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  intent?: string;
  result?: any;
};

const InstructionChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentDocIds, setCurrentDocIds] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string>('');
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // 初始化会话ID
  useEffect(() => {
    const storedId = localStorage.getItem('chat_conversation_id');
    if (storedId) {
      setConversationId(storedId);
    } else {
      const newId = `conv_${Date.now()}_${Math.random().toString(36).substring(7)}`;
      setConversationId(newId);
      localStorage.setItem('chat_conversation_id', newId);
    }
  }, []);

  useEffect(() => {
    // Initial welcome message
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `您好！我是智联文档 AI 助手。

**📄 文档智能操作**
- "提取文档中的医院数量和床位数"
- "帮我找出所有机构的名称"

**📊 数据填表**
- "根据这些数据填表"
- "将提取的信息填写到Excel模板"

**📝 内容处理**
- "总结一下这份文档"
- "对比这两个文档的差异"

**🔍 智能问答**
- "文档里说了些什么？"
- "有多少家医院？"

请告诉我您想做什么？`,
          created_at: new Date().toISOString()
        }
      ]);

      // 获取已上传的文档ID列表
      loadDocuments();
    }
  }, []);

  const loadDocuments = async () => {
    try {
      const result = await backendApi.getDocuments(undefined, 50);
      if (result.success && result.documents) {
        const docIds = result.documents.map((d: any) => d.doc_id);
        setCurrentDocIds(docIds);
        if (docIds.length > 0) {
          console.log(`已加载 ${docIds.length} 个文档`);
        }
      }
    } catch (err) {
      console.error('获取文档列表失败:', err);
    }
  };

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
      // 使用真实的智能指令 API
      const response = await backendApi.instructionChat(
        input.trim(),
        currentDocIds.length > 0 ? currentDocIds : undefined,
        { conversation_id: conversationId }
      );

      // 根据意图类型生成友好响应
      let responseContent = '';
      const resultData = response.result;

      switch (response.intent) {
        case 'extract':
          // 信息提取结果
          const extracted = resultData?.extracted_data || {};
          const keys = Object.keys(extracted);
          if (keys.length > 0) {
            responseContent = `✅ 已提取到 ${keys.length} 个字段的数据：\n\n`;
            for (const [key, value] of Object.entries(extracted)) {
              const values = Array.isArray(value) ? value : [value];
              const displayValues = values.length > 10 ? values.slice(0, 10).join(', ') + ` ...（共${values.length}条）` : values.join(', ');
              responseContent += `**${key}**: ${displayValues}\n`;
            }
            responseContent += `\n💡 可直接使用以上数据，或说"填入表格"继续填表操作。`;
          } else {
            responseContent = resultData?.message || '未能从文档中提取到相关数据。请尝试更明确的字段名称。';
          }
          break;

        case 'fill_table':
          // 填表结果
          const filled = resultData?.result?.filled_data || {};
          const filledKeys = Object.keys(filled);
          if (filledKeys.length > 0) {
            responseContent = `✅ 填表完成！成功填写 ${filledKeys.length} 个字段：\n\n`;
            for (const [key, value] of Object.entries(filled)) {
              const values = Array.isArray(value) ? value : [value];
              const displayValues = values.length > 10 ? values.slice(0, 10).join(', ') + ` ...（共${values.length}条）` : values.join(', ');
              responseContent += `**${key}**: ${displayValues}\n`;
            }
            responseContent += `\n📋 请到【智能填表】页面查看或导出结果。`;
          } else {
            responseContent = resultData?.message || '填表未能提取到数据。请检查模板表头和数据源内容。';
          }
          break;

        case 'summarize':
          // 摘要结果
          if (resultData?.action_needed === 'provide_document' || resultData?.action_needed === 'upload_document') {
            responseContent = `📋 ${resultData.message}\n\n${resultData.suggestion || ''}`;
          } else if (resultData?.ai_summary) {
            // AI 生成的摘要
            responseContent = `📄 **${resultData.filename}** 摘要分析：\n\n${resultData.ai_summary}`;
          } else {
            responseContent = resultData?.message || '未能生成摘要。请确保已上传文档。';
          }
          break;

        case 'question':
          // 问答结果
          if (resultData?.answer) {
            responseContent = `**问题**: ${resultData.question}\n\n**答案**: ${resultData.answer}`;
          } else if (resultData?.context_preview) {
            responseContent = `**问题**: ${resultData.question}\n\n**相关上下文**：\n${resultData.context_preview}`;
          } else {
            responseContent = resultData?.message || '请先上传文档，我才能回答您的问题。';
          }
          break;

        case 'search':
          // 搜索结果
          const searchResults = resultData?.results || [];
          if (searchResults.length > 0) {
            responseContent = `🔍 找到 ${searchResults.length} 条相关内容：\n\n`;
            searchResults.slice(0, 5).forEach((r: any, idx: number) => {
              responseContent += `**${idx + 1}.** ${r.content?.substring(0, 100)}...\n\n`;
            });
          } else {
            responseContent = '未找到相关内容。请尝试其他关键词。';
          }
          break;

        case 'compare':
          // 对比结果
          const comparison = resultData?.comparison || [];
          if (comparison.length > 0) {
            responseContent = `📊 对比了 ${comparison.length} 个文档：\n\n`;
            comparison.forEach((c: any) => {
              responseContent += `- **${c.filename}**: ${c.doc_type}, ${c.content_length} 字\n`;
            });
          } else {
            responseContent = '需要至少2个文档才能进行对比。';
          }
          break;

        case 'edit':
          // 文档编辑结果
          if (resultData?.edited_content) {
            responseContent = `✏️ **${resultData.original_filename}** 编辑完成：\n\n${resultData.edited_content.substring(0, 500)}${resultData.edited_content.length > 500 ? '\n\n...(内容已截断)' : ''}`;
          } else {
            responseContent = resultData?.message || '编辑完成。';
          }
          break;

        case 'transform':
          // 格式转换结果
          if (resultData?.excel_data) {
            responseContent = `🔄 格式转换完成！\n\n已转换为 **Excel** 格式，共 **${resultData.excel_data.length}** 行数据。\n\n${resultData.message || ''}`;
          } else if (resultData?.content) {
            responseContent = `🔄 格式转换完成！\n\n目标格式: **${resultData.target_format?.toUpperCase()}**\n\n${resultData.message || ''}`;
          } else {
            responseContent = resultData?.message || '格式转换完成。';
          }
          break;

        case 'unknown':
          // 检查是否需要用户上传文档
          if (resultData?.suggestion) {
            responseContent = resultData.suggestion;
          } else if (resultData?.message && resultData.message !== '无法理解该指令，请尝试更明确的描述') {
            responseContent = resultData.message;
          } else {
            responseContent = `我理解您想要： "${input.trim()}"\n\n请尝试以下操作：\n\n1. **提取数据**: "提取医院数量和床位数"\n2. **填表**: "根据这些数据填表"\n3. **总结**: "总结这份文档"\n4. **问答**: "文档里说了什么？"\n5. **搜索**: "搜索相关内容"`;
          }
          break;

        default:
          responseContent = response.message || resultData?.message || '已完成您的请求。';
      }

      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'assistant',
        content: responseContent,
        created_at: new Date().toISOString(),
        intent: response.intent,
        result: resultData
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('指令执行失败:', err);
      toast.error(err.message || '请求失败，请重试');

      const errorMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'assistant',
        content: `抱歉，处理您的请求时遇到了问题：${err.message}\n\n请稍后重试，或尝试更简单的指令。`,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([messages[0]]);
    toast.success('对话已清空');
  };

  const quickActions = [
    { label: '提取医院数量', icon: Search, action: () => setInput('提取文档中的医院数量和床位数') },
    { label: '智能填表', icon: TableProperties, action: () => setInput('根据这些数据填表') },
    { label: '总结文档', icon: MessageSquare, action: () => setInput('总结一下这份文档') },
    { label: '智能问答', icon: Bot, action: () => setInput('文档里说了些什么？') }
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
                    {m.role === 'assistant' ? (
                      <Markdown content={m.content} className="text-sm leading-relaxed prose prose-sm max-w-none" />
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">{m.content}</p>
                    )}
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