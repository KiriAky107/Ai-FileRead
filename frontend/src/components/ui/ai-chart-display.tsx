import React, { useState } from 'react';
import { Download, Maximize2, X, Table, FileText, TrendingUp, BarChart3, Info, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface AIChartDisplayProps {
  charts?: any;
  statistics?: any;
  tablePreview?: any;
  className?: string;
}

export const AIChartDisplay: React.FC<AIChartDisplayProps> = ({ charts, statistics, tablePreview, className }) => {
  const [previewChart, setPreviewChart] = useState<{ image: string; title: string } | null>(null);

  const downloadChart = (imageData: string, title: string) => {
    try {
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

  const openPreview = (image: string, title: string) => {
    setPreviewChart({ image, title });
  };

  const closePreview = () => {
    setPreviewChart(null);
  };

  const getChartIcon = (type: string) => {
    switch (type) {
      case 'bar':
        return <Table size={20} className="text-blue-500" />;
      case 'pie':
        return <ExternalLink size={20} className="text-pink-500" />;
      case 'barh':
        return <FileText size={20} className="text-emerald-500" />;
      case 'time_series':
        return <TrendingUp size={20} className="text-purple-500" />;
      case 'comparison':
        return <BarChart3 size={20} className="text-amber-500" />;
      default:
        return <Table size={20} className="text-gray-500" />;
    }
  };

  return (
    <div className={className}>
      {/* 数值型数据图表 */}
      {charts?.numeric_charts && charts.numeric_charts.length > 0 && (
        <div className="space-y-4 mb-6">
          <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
            <Table size={18} className="text-blue-500" />
            数值型数据图表
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {charts.numeric_charts.map((chart: any, idx: number) => (
              <Card key={idx} className="border shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{chart.title}</CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => downloadChart(chart.image, chart.title)}
                        title="下载图表"
                      >
                        <Download size={14} />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => openPreview(chart.image, chart.title)}
                        title="放大查看"
                      >
                        <Maximize2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-3 bg-white">
                  <img src={chart.image} alt={chart.title} className="w-full h-auto object-contain rounded-lg" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* 分类数据图表 */}
      {charts?.categorical_charts && charts.categorical_charts.length > 0 && (
        <div className="space-y-4 mb-6">
          <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
            <FileText size={18} className="text-emerald-500" />
            分类数据图表
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {charts.categorical_charts.map((chart: any, idx: number) => (
              <Card key={idx} className="border shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{chart.title}</CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => downloadChart(chart.image, chart.title)}
                        title="下载图表"
                      >
                        <Download size={14} />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => openPreview(chart.image, chart.title)}
                        title="放大查看"
                      >
                        <Maximize2 size={14} />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-3 bg-white">
                  <img src={chart.image} alt={chart.title} className="w-full h-auto object-contain rounded-lg" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* 时间序列图表 */}
      {charts?.time_series_chart && (
        <div className="space-y-4 mb-6">
          <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
            <TrendingUp size={18} className="text-purple-500" />
            时间序列图表
          </h4>
          <Card className="border shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{charts.time_series_chart.title}</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => downloadChart(charts.time_series_chart.image, charts.time_series_chart.title)}
                    title="下载图表"
                  >
                    <Download size={14} />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => openPreview(charts.time_series_chart.image, charts.time_series_chart.title)}
                    title="放大查看"
                  >
                    <Maximize2 size={14} />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-3 bg-white">
              <img src={charts.time_series_chart.image} alt={charts.time_series_chart.title} className="w-full h-auto object-contain rounded-lg" />
            </CardContent>
          </Card>
        </div>
      )}

      {/* 对比数据图表 */}
      {charts?.comparison_chart && (
        <div className="space-y-4 mb-6">
          <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
            <BarChart3 size={18} className="text-orange-500" />
            对比数据图表
          </h4>
          <Card className="border shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{charts.comparison_chart.title}</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => downloadChart(charts.comparison_chart.image, charts.comparison_chart.title)}
                    title="下载图表"
                  >
                    <Download size={14} />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => openPreview(charts.comparison_chart.image, charts.comparison_chart.title)}
                    title="放大查看"
                  >
                    <Maximize2 size={14} />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-3 bg-white">
              <img src={charts.comparison_chart.image} alt={charts.comparison_chart.title} className="w-full h-auto object-contain rounded-lg" />
            </CardContent>
          </Card>
        </div>
      )}

      {/* 数值摘要 */}
      {statistics?.numeric_summary && (
        <Card className="border shadow-sm mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Info size={18} className="text-primary" />
              数值摘要统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">数量</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.count}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">总和</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.sum?.toLocaleString()}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">平均值</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.mean?.toFixed(2)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">中位数</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.median?.toFixed(2)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">最小值</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.min?.toLocaleString()}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">最大值</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.max?.toLocaleString()}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">标准差</p>
                <p className="text-lg font-bold">{statistics.numeric_summary.std?.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 表格预览 */}
      {tablePreview && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">提取的表格数据</CardTitle>
              <Badge variant="outline">
                共 {tablePreview.total_rows} 行
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              显示前 {tablePreview.preview_rows} 行数据，共 {tablePreview.total_rows} 行
            </p>
            <div className="max-h-80 overflow-y-auto border rounded">
              <table className="w-full text-sm">
                <thead className="bg-muted sticky top-0">
                  <tr>
                    <th className="p-2 text-left border">序号</th>
                    {tablePreview.columns.map((col: string, idx: number) => (
                      <th key={idx} className="p-2 text-left border">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tablePreview.rows.slice(0, 20).map((row: any, rowIdx: number) => (
                    <tr key={rowIdx} className="border-b">
                      <td className="p-2 text-muted-foreground font-medium border">{rowIdx + 1}</td>
                      {tablePreview.columns.map((col: string, colIdx: number) => (
                        <td key={colIdx} className="p-2 border">
                          {row[col] ?? '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
                src={previewChart.image}
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
