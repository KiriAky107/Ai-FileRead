import React from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  TableProperties,
  MessageSquareCode,
  Menu,
  ChevronRight,
  Sparkles,
  Clock,
  FileDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

const navItems = [
  { name: '控制台', path: '/', icon: LayoutDashboard },
  { name: '文档中心', path: '/documents', icon: FileText },
  { name: '智能填表', path: '/form-fill', icon: TableProperties },
  { name: '智能助手', path: '/assistant', icon: MessageSquareCode },
  { name: '文档转PDF', path: '/pdf-converter', icon: FileDown },
  { name: '任务历史', path: '/task-history', icon: Clock },
];

const MainLayout: React.FC = () => {
  const location = useLocation();

  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-sidebar py-6 border-r border-sidebar-border">
      <div className="px-6 mb-10 flex items-center gap-2">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground shadow-lg shadow-primary/20">
          <FileText size={24} />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-lg tracking-tight text-sidebar-foreground">智联文档</span>
          <span className="text-xs text-muted-foreground">多源数据融合平台</span>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                isActive 
                  ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon size={20} className={cn(isActive ? "text-white" : "group-hover:scale-110 transition-transform")} />
              <span className="font-medium">{item.name}</span>
              {isActive && <ChevronRight size={16} className="ml-auto" />}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 mt-auto">
        <div className="bg-sidebar-accent/50 rounded-2xl p-4 border border-sidebar-border/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center border-2 border-primary/10">
              <Sparkles size={20} className="text-primary" />
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="font-semibold text-sm truncate">智联文档</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">多源数据融合</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen w-full bg-background overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-72 shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden fixed top-4 left-4 z-50 bg-background/50 backdrop-blur shadow-sm">
            <Menu size={24} />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-72 border-none">
          <SidebarContent />
        </SheetContent>
      </Sheet>

      <main className="flex-1 overflow-y-auto relative p-6 lg:p-10 pt-20 lg:pt-10">
        <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
