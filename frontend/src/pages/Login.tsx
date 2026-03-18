import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Lock, User, CheckCircle2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return toast.error('请输入用户名和密码');
    
    setLoading(true);
    try {
      const email = `${username}@miaoda.com`;
      const { error } = await signIn(email, password);
      if (error) throw error;
      toast.success('登录成功');
      navigate('/');
    } catch (err: any) {
      toast.error(err.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return toast.error('请输入用户名和密码');
    
    setLoading(true);
    try {
      const email = `${username}@miaoda.com`;
      const { error } = await signUp(email, password);
      if (error) throw error;
      toast.success('注册成功，请登录');
    } catch (err: any) {
      toast.error(err.message || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-primary/10 via-background to-background p-4 relative overflow-hidden">
      {/* Decorative elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl translate-x-1/3 translate-y-1/3" />

      <div className="w-full max-w-md space-y-8 relative animate-fade-in">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary text-primary-foreground shadow-2xl shadow-primary/30 mb-4 animate-slide-in">
            <FileText size={32} />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight gradient-text">智联文档</h1>
          <p className="text-muted-foreground">多源数据融合与智能文档处理系统</p>
        </div>

        <Card className="border-border/50 shadow-2xl backdrop-blur-sm bg-card/95">
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 rounded-t-xl h-12 bg-muted/50 p-1">
              <TabsTrigger value="login" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm">登录</TabsTrigger>
              <TabsTrigger value="signup" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm">注册</TabsTrigger>
            </TabsList>
            
            <TabsContent value="login">
              <form onSubmit={handleLogin}>
                <CardHeader>
                  <CardTitle>欢迎回来</CardTitle>
                  <CardDescription>使用您的账号登录智联文档系统</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">用户名</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="username" 
                        placeholder="请输入用户名" 
                        className="pl-9 bg-muted/30 border-none focus-visible:ring-primary"
                        value={username} 
                        onChange={(e) => setUsername(e.target.value)} 
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">密码</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="password" 
                        type="password" 
                        placeholder="请输入密码" 
                        className="pl-9 bg-muted/30 border-none focus-visible:ring-primary"
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                      />
                    </div>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button className="w-full h-11 text-lg font-semibold rounded-xl" type="submit" disabled={loading}>
                    {loading ? '登录中...' : '立即登录'}
                  </Button>
                </CardFooter>
              </form>
            </TabsContent>

            <TabsContent value="signup">
              <form onSubmit={handleSignUp}>
                <CardHeader>
                  <CardTitle>创建账号</CardTitle>
                  <CardDescription>开启智能文档处理的新体验</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="signup-username">用户名</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signup-username" 
                        placeholder="仅字母、数字和下划线" 
                        className="pl-9 bg-muted/30 border-none focus-visible:ring-primary"
                        value={username} 
                        onChange={(e) => setUsername(e.target.value)} 
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-password">密码</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signup-password" 
                        type="password" 
                        placeholder="不少于 6 位" 
                        className="pl-9 bg-muted/30 border-none focus-visible:ring-primary"
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                      />
                    </div>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button className="w-full h-11 text-lg font-semibold rounded-xl" type="submit" disabled={loading}>
                    {loading ? '注册中...' : '注册账号'}
                  </Button>
                </CardFooter>
              </form>
            </TabsContent>
          </Tabs>
        </Card>

        <div className="grid grid-cols-2 gap-4 text-center text-xs text-muted-foreground">
          <div className="flex flex-col items-center gap-1">
            <CheckCircle2 size={16} className="text-primary" />
            <span>智能解析</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <CheckCircle2 size={16} className="text-primary" />
            <span>极速填表</span>
          </div>
        </div>

        <div className="text-center text-sm text-muted-foreground">
          &copy; 2026 智联文档 | 多源数据融合系统
        </div>
      </div>
    </div>
  );
};

export default Login;
