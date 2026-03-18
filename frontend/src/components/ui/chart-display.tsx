import React, { useState } from 'react';
import { Image as ImageIcon, Maximize2, Download, BarChart3, ScatterChart, Grid3x3, X, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface ChartDisplayProps {
  charts?: any;
  className?: string;
}

type ChartType = 'histogram' | 'bar_chart' | 'box_plot' | 'correlation_heatmap' | 'bar' | 'pie' | 'barh' | 'time_series' | 'comparison';

export const ChartDisplay: React.FC<ChartDisplayProps> = ({ charts, className }) => {
  const [expandedCharts, setExpandedCharts] = useState<Record<string, boolean>>({});
  const [previewChart, setPreviewChart] = useState<{ type: string; data: any; title: string } | null>(null);

  const toggleChart = (key: string) => {
    setExpandedCharts(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const downloadChart = (imageData: string, title: string) => {
    try {
      // 提取 base64 数据
      const base64Data = imageData.split(',')[1];
      const binaryData = atob(base64Data);
      const bytes = new Uint8Array(binaryData.length);

      for (let i = 0; i < binaryData.length; i++) {
        bytes[i] = binaryData.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: 'image/png' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = `${title}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success('图表已下载');
    } catch (error) {
      console.error('下载失败:', error);
      toast.error('下载失败，请稍后重试');
    }
  };

  const openPreview = (type: string, data: any, title: string) => {
    setPreviewChart({ type, data, title });
  };

  const closePreview = () => {
    setPreviewChart(null);
  };

  const getChartIcon = (type: ChartType) => {
    switch (type) {
      case 'histogram':
      case 'bar':
        return <BarChart3 size={20} className="text-blue-500" />;
      case 'bar_chart':
      case 'barh':
        return <BarChart3 size={20} className="text-emerald-500" />;
      case 'box_plot':
        return <Grid3x3 size={20} className="text-purple-500" />;
      case 'correlation_heatmap':
        return <ScatterChart size={20} className="text-orange-500" />;
      case 'pie':
        return <ExternalLink size={20} className="text-pink-500" />;
      case 'time_series':
        return <ScatterChart size={20} className="text-cyan-500" />;
      case 'comparison':
        return <BarChart3 size={20} className="text-amber-500" />;
      default:
        return <ImageIcon size={20} className="text-gray-500" />;
    }
  };

  const getChartLabel = (type: ChartType) => {
    const labels = {
      'histogram': '直方图',
      'bar_chart': '条形图',
      'box_plot': '箱线图',
      'correlation_heatmap': '相关性热力图',
      'bar': '柱状图',
      'pie': '饼图',
      'barh': '水平条形图',
      'time_series': '时间序列图',
      'comparison': '对比图'
    };
    return labels[type] || type;
  };

  const getChartColor = (type: ChartType) => {
    const colors = {
      'histogram': 'bg-blue-500/10 border-blue-500/20',
      'bar_chart': 'bg-emerald-500/10 border-emerald-500/20',
      'box_plot': 'bg-purple-500/10 border-purple-500/20',
      'correlation_heatmap': 'bg-orange-500/10 border-orange-500/20',
      'bar': 'bg-blue-500/10 border-blue-500/20',
      'pie': 'bg-pink-500/10 border-pink-500/20',
      'barh': 'bg-emerald-500/10 border-emerald-500/20',
      'time_series': 'bg-cyan-500/10 border-cyan-500/20',
      'comparison': 'bg-amber-500/10 border-amber-500/20'
    };
    return colors[type] || 'bg-gray-500/10 border-gray-500/20';
  };

  if (!charts || Object.keys(charts).length === 0) {
    return (
      <div className={className}>
        <Card className="border-none shadow-sm">
          <CardContent className="p-12 text-center text-muted-foreground">
            <BarChart3 size={48} className="mx-auto mb-4 text-muted-foreground/30" />
            <p className="text-sm">暂无图表数据</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* 直方图 */}
      {charts.histograms && charts.histograms.length > 0 && (
        <Card className="border-none shadow-md mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="text-blue-500" size={20} />
              直方图分布
            </CardTitle>
            <CardDescription>数值型列的分布情况</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {charts.histograms.map((chart: any, idx: number) => (
                <div key={idx} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm truncate flex-1" title={chart.column}>
                      {chart.column}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => downloadChart(chart.image, `${chart.column}_histogram`)}
                        title="下载图表"
                      >
                        <Download size={14} />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => openPreview('histogram', chart, `${chart.column} - 直方图`)}
                        title="放大查看"
                      >
                        <Maximize2 size={14} />
                      </Button>
                    </div>
                  </div>
                  {chart.stats && (
                    <div className="flex gap-4 text-xs text-muted-foreground bg-muted/30 px-3 py-2 rounded-md">
                      <span>均值: {chart.stats.mean?.toFixed(2)}</span>
                      <span>中位数: {chart.stats.median?.toFixed(2)}</span>
                      <span>标准差: {chart.stats.std?.toFixed(2)}</span>
                    </div>
                  )}
                  <div
                    className={cn(
                      "border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-lg hover:border-blue-400",
                      expandedCharts[`hist_${idx}`] ? "ring-2 ring-blue-400" : ""
                    )}
                    onClick={() => toggleChart(`hist_${idx}`)}
                  >
                    {expandedCharts[`hist_${idx}`] ? (
                      <div className="p-2 bg-white">
                        <img src={chart.image} alt={chart.column} className="w-full h-auto object-contain" />
                      </div>
                    ) : (
                      <div className="h-52 bg-gradient-to-b from-blue-500/20 to-blue-500/5 flex flex-col items-center justify-center gap-2">
                        <BarChart3 size={40} className="text-blue-500/30" />
                        <span className="text-xs text-blue-500/50">点击展开图表</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 条形图 */}
      {charts.bar_charts && charts.bar_charts.length > 0 && (
        <Card className="border-none shadow-md mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="text-emerald-500" size={20} />
              条形图分布
            </CardTitle>
            <CardDescription>分类列的频次分布（Top 10）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {charts.bar_charts.map((chart: any, idx: number) => (
                <div key={idx} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm truncate flex-1" title={chart.column}>
                      {chart.column}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => downloadChart(chart.image, `${chart.column}_bar_chart`)}
                        title="下载图表"
                      >
                        <Download size={14} />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => openPreview('bar_chart', chart, `${chart.column} - 条形图`)}
                        title="放大查看"
                      >
                        <Maximize2 size={14} />
                      </Button>
                    </div>
                  </div>
                  <div
                    className={cn(
                      "border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-lg hover:border-emerald-400",
                      expandedCharts[`bar_${idx}`] ? "ring-2 ring-emerald-400" : ""
                    )}
                    onClick={() => toggleChart(`bar_${idx}`)}
                  >
                    {expandedCharts[`bar_${idx}`] ? (
                      <div className="p-2 bg-white">
                        <img src={chart.image} alt={chart.column} className="w-full h-auto object-contain" />
                      </div>
                    ) : (
                      <div className="h-52 bg-gradient-to-b from-emerald-500/20 to-emerald-500/5 flex flex-col items-center justify-center gap-2">
                        <BarChart3 size={40} className="text-emerald-500/30" />
                        <span className="text-xs text-emerald-500/50">点击展开图表</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 箱线图 */}
      {charts.box_plots && charts.box_plots.length > 0 && (
        <Card className="border-none shadow-md mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Grid3x3 className="text-purple-500" size={20} />
              箱线图对比
            </CardTitle>
            <CardDescription>数值型列的四分位数和异常值对比</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {charts.box_plots.map((boxPlot: any, idx: number) => (
              <div key={idx} className="space-y-3">
                <div className="flex items-end justify-end">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => downloadChart(boxPlot.image, 'box_plot')}
                      title="下载图表"
                    >
                      <Download size={14} />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => openPreview('box_plot', boxPlot, '箱线图对比')}
                      title="放大查看"
                    >
                      <Maximize2 size={14} />
                    </Button>
                  </div>
                </div>
                <div
                  className={cn(
                    "border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-lg hover:border-purple-400",
                    expandedCharts[`box_plot_${idx}`] ? "ring-2 ring-purple-400" : ""
                  )}
                  onClick={() => toggleChart(`box_plot_${idx}`)}
                >
                  {expandedCharts[`box_plot_${idx}`] ? (
                    <div className="p-2 bg-white">
                      <img src={boxPlot.image} alt="箱线图" className="w-full h-auto object-contain" />
                    </div>
                  ) : (
                    <div className="h-56 bg-gradient-to-b from-purple-500/20 to-purple-500/5 flex flex-col items-center justify-center gap-2">
                      <Grid3x3 size={48} className="text-purple-500/30" />
                      <span className="text-xs text-purple-500/50">点击展开图表</span>
                    </div>
                  )}
                </div>
                {boxPlot.columns && (
                  <div className="flex flex-wrap gap-2">
                    {boxPlot.columns.map((col: string) => (
                      <Badge key={col} variant="secondary" className="text-xs">
                        {col}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 相关性热力图 */}
      {charts.correlation && (
        <Card className="border-none shadow-md mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <ScatterChart className="text-orange-500" size={20} />
              相关性热力图
            </CardTitle>
            <CardDescription>数值型列之间的相关系数矩阵</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-end justify-end">
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => downloadChart(charts.correlation.image, 'correlation_heatmap')}
                  title="下载图表"
                >
                  <Download size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => openPreview('correlation_heatmap', charts.correlation, '相关性热力图')}
                  title="放大查看"
                >
                  <Maximize2 size={14} />
                </Button>
              </div>
            </div>
            <div
              className={cn(
                "border rounded-lg overflow-hidden cursor-pointer transition-all hover:shadow-lg hover:border-orange-400",
                expandedCharts['correlation'] ? "ring-2 ring-orange-400" : ""
              )}
              onClick={() => toggleChart('correlation')}
            >
              {expandedCharts['correlation'] ? (
                <div className="p-2 bg-white">
                  <img src={charts.correlation.image} alt="相关性热力图" className="w-full h-auto object-contain" />
                </div>
              ) : (
                <div className="h-64 bg-gradient-to-b from-orange-500/20 to-orange-500/5 flex flex-col items-center justify-center gap-2">
                  <ScatterChart size={56} className="text-orange-500/30" />
                  <span className="text-xs text-orange-500/50">点击展开图表</span>
                </div>
              )}
            </div>
            {charts.correlation.columns && (
              <div className="flex flex-wrap gap-2">
                {charts.correlation.columns.map((col: string) => (
                  <Badge key={col} variant="secondary" className="text-xs">
                    {col}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 图表预览对话框 */}
      <Dialog open={previewChart !== null} onOpenChange={closePreview}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between w-full pr-8">
              <DialogTitle className="text-xl">{previewChart?.title}</DialogTitle>
              <Button variant="ghost" size="icon" onClick={closePreview}>
                <X size={20} />
              </Button>
            </div>
          </DialogHeader>
          <div className="p-4 bg-white rounded-lg">
            {previewChart && (
              <img
                src={previewChart.data.image}
                alt={previewChart.title}
                className="w-full h-auto object-contain max-w-full"
                style={{ maxHeight: '70vh' }}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export const StatisticsDisplay: React.FC<{ statistics: any }> = ({ statistics }) => {
  if (!statistics) {
    return null;
  }

  return (
    <Card className="border-none shadow-md mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="text-primary" size={20} />
          统计信息
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="numeric" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="numeric">数值型列</TabsTrigger>
            <TabsTrigger value="categorical">分类型列</TabsTrigger>
          </TabsList>

          <TabsContent value="numeric" className="mt-4">
            {statistics.numeric && Object.keys(statistics.numeric).length > 0 ? (
              <ScrollArea className="h-96 pr-2">
                <div className="space-y-3">
                  {Object.entries(statistics.numeric).map(([col, stats]: [string, any]) => (
                    <div key={col} className="p-4 bg-muted/30 rounded-xl border">
                      <div className="font-semibold text-sm mb-3 truncate" title={col}>{col}</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">数量</span>
                          <span className="font-medium text-base">{stats.count}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">均值</span>
                          <span className="font-medium text-base">{stats.mean?.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">中位数</span>
                          <span className="font-medium text-base">{stats.median?.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">标准差</span>
                          <span className="font-medium text-base">{stats.std?.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">最小值</span>
                          <span className="font-medium text-base">{stats.min}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">最大值</span>
                          <span className="font-medium text-base">{stats.max}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">Q25</span>
                          <span className="font-medium text-base">{stats.q25?.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-muted-foreground mb-1">Q75</span>
                          <span className="font-medium text-base">{stats.q75?.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">
                暂无数值型列数据
              </div>
            )}
          </TabsContent>

          <TabsContent value="categorical" className="mt-4">
            {statistics.categorical && Object.keys(statistics.categorical).length > 0 ? (
              <ScrollArea className="h-96 pr-2">
                <div className="space-y-3">
                  {Object.entries(statistics.categorical).map(([col, stats]: [string, any]) => (
                    <div key={col} className="p-4 bg-muted/30 rounded-xl border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="font-semibold text-sm truncate flex-1 mr-2" title={col}>{col}</div>
                        <Badge variant="secondary" className="text-xs">
                          {stats.unique} 个唯一值
                        </Badge>
                      </div>
                      <div className="text-xs space-y-2">
                        <div className="flex items-center">
                          <span className="text-muted-foreground w-16 flex-shrink-0">最常见:</span>
                          <span className="font-medium ml-1 truncate" title={stats.most_common}>
                            {stats.most_common}
                          </span>
                          <span className="text-muted-foreground ml-1 flex-shrink-0">
                            ({stats.most_common_count} 次)
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span className="text-muted-foreground w-16 flex-shrink-0">缺失值:</span>
                          <span className={stats.missing > 0 ? "text-destructive font-medium" : "text-muted-foreground"}>
                            {stats.missing}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">
                暂无分类型列数据
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};
