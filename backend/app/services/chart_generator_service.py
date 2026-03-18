"""
图表生成服务 - 根据结构化数据生成图表
"""
import io
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 使用字体辅助模块配置中文字体
from app.services.font_helper import configure_matplotlib_fonts

configure_matplotlib_fonts()

logger = logging.getLogger(__name__)


class ChartGeneratorService:
    """图表生成服务类"""

    def __init__(self):
        self.output_dir = Path(__file__).resolve().parent.parent.parent / "data" / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_charts_from_analysis(
        self,
        structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据提取的结构化数据生成图表

        Args:
            structured_data: 从 AI 分析结果中提取的结构化数据

        Returns:
            Dict[str, Any]: 包含图表数据的结果
        """
        if not structured_data.get("success"):
            return {
                "success": False,
                "error": structured_data.get("error", "数据提取失败")
            }

        data = structured_data.get("data", {})
        charts = {}
        statistics = {}

        try:
            # 1. 数值型数据图表
            numeric_data = data.get("numeric_data", [])
            if numeric_data:
                charts["numeric_charts"] = self._create_numeric_charts(numeric_data)
                statistics["numeric_summary"] = self._create_numeric_summary(numeric_data)

            # 2. 分类数据图表
            categorical_data = data.get("categorical_data", [])
            if categorical_data:
                charts["categorical_charts"] = self._create_categorical_charts(categorical_data)

            # 3. 时间序列图表
            time_series_data = data.get("time_series_data", [])
            if time_series_data:
                charts["time_series_chart"] = self._create_time_series_chart(time_series_data)

            # 4. 对比数据图表
            comparison_data = data.get("comparison_data", [])
            if comparison_data:
                charts["comparison_chart"] = self._create_comparison_chart(comparison_data)

            # 5. 表格数据可视化
            table_data = data.get("table_data")
            if table_data:
                charts["table_preview"] = self._create_table_preview(table_data)

            # 元数据
            metadata = data.get("metadata", {})

            return {
                "success": True,
                "charts": charts,
                "statistics": statistics,
                "metadata": metadata,
                "data_source": "ai_analysis"
            }

        except Exception as e:
            logger.error(f"生成图表失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _create_numeric_charts(self, numeric_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建数值型数据图表"""
        charts = []

        # 提取数值和标签
        names = [item.get("name", f"项{i}") for i, item in enumerate(numeric_data)]
        values = [item.get("value", 0) for item in numeric_data]

        if not values:
            return charts

        # 1. 柱状图
        try:
            fig, ax = plt.subplots(figsize=(12, 7))
            colors = plt.cm.Set3(np.linspace(0, 1, len(values)))
            bars = ax.bar(names, values, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)

            # 添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                       f'{value:,.0f}',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

            ax.set_xlabel('项目', fontsize=10, labelpad=10, fontweight='bold')
            ax.set_ylabel('数值', fontsize=10, labelpad=10, fontweight='bold')
            ax.set_title('数值型数据对比', fontsize=12, fontweight='bold', pad=15)
            ax.set_xticklabels(names, rotation=30, ha='right', fontsize=9)
            ax.tick_params(axis='both', which='major', labelsize=9)
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout(pad=1.5)

            img_base64 = self._figure_to_base64(fig)
            charts.append({
                "type": "bar",
                "title": "数值型数据对比",
                "image": img_base64,
                "data": [{"name": n, "value": v} for n, v in zip(names, values)]
            })
        except Exception as e:
            logger.error(f"创建柱状图失败: {str(e)}")

        # 2. 饼图
        if len(values) > 0 and len(values) <= 10:
            try:
                fig, ax = plt.subplots(figsize=(10, 10))
                wedges, texts, autotexts = ax.pie(values, labels=names, autopct='%1.1f%%',
                                                   startangle=90, colors=plt.cm.Set3.colors[:len(values)])

                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(9)
                    autotext.set_fontweight('bold')

                ax.set_title('数值型数据占比', fontsize=12, fontweight='bold', pad=15)

                img_base64 = self._figure_to_base64(fig)
                charts.append({
                    "type": "pie",
                    "title": "数值型数据占比",
                    "image": img_base64,
                    "data": [{"name": n, "value": v} for n, v in zip(names, values)]
                })
            except Exception as e:
                logger.error(f"创建饼图失败: {str(e)}")

        return charts

    def _create_categorical_charts(self, categorical_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建分类数据图表"""
        charts = []

        # 提取数据
        names = [item.get("name", f"类{i}") for i, item in enumerate(categorical_data)]
        counts = [item.get("count", 1) for item in categorical_data]

        if not names or not counts:
            return charts

        # 水平条形图
        try:
            fig, ax = plt.subplots(figsize=(10, max(6, len(names) * 0.8)))
            y_pos = np.arange(len(names))

            bars = ax.barh(y_pos, counts, align='center', color='#10b981', alpha=0.8, edgecolor='black', linewidth=0.5)

            # 添加数值标签
            for bar, count in zip(bars, counts):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2.,
                       f'{count}',
                       ha='left', va='center', fontsize=10, fontweight='bold')

            ax.set_yticks(y_pos)
            ax.set_yticklabels(names, fontsize=10)
            ax.invert_yaxis()
            ax.set_xlabel('数量', fontsize=10, labelpad=10, fontweight='bold')
            ax.set_title('分类数据分布', fontsize=12, fontweight='bold', pad=15)
            ax.tick_params(axis='both', which='major', labelsize=9)
            ax.grid(axis='x', alpha=0.3)
            plt.tight_layout(pad=1.5)

            img_base64 = self._figure_to_base64(fig)
            charts.append({
                "type": "barh",
                "title": "分类数据分布",
                "image": img_base64,
                "data": [{"name": n, "count": c} for n, c in zip(names, counts)]
            })
        except Exception as e:
            logger.error(f"创建分类图表失败: {str(e)}")

        return charts

    def _create_time_series_chart(self, time_series_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """创建时间序列图表"""
        if not time_series_data:
            return None

        try:
            names = [item.get("name", f"时间{i}") for i, item in enumerate(time_series_data)]
            values = [item.get("value", 0) for item in time_series_data]

            if len(values) < 2:
                return None

            fig, ax = plt.subplots(figsize=(14, 7))

            # 绘制折线图和柱状图
            x_pos = np.arange(len(names))
            bars = ax.bar(x_pos, values, width=0.4, label='数值', color='#3b82f6', alpha=0.7)

            # 添加折线
            line = ax.plot(x_pos, values, 'o-', color='#ef4444', linewidth=2.5, markersize=8, label='趋势')

            ax.set_xticks(x_pos)
            ax.set_xticklabels(names, rotation=30, ha='right', fontsize=9)
            ax.set_ylabel('数值', fontsize=10, labelpad=10, fontweight='bold')
            ax.set_title('时间序列数据', fontsize=12, fontweight='bold', pad=15)
            ax.legend(loc='best', fontsize=9)
            ax.tick_params(axis='both', which='major', labelsize=9)
            ax.grid(True, alpha=0.3)
            plt.tight_layout(pad=1.5)

            img_base64 = self._figure_to_base64(fig)
            return {
                "type": "time_series",
                "title": "时间序列数据",
                "image": img_base64,
                "data": [{"name": n, "value": v} for n, v in zip(names, values)]
            }
        except Exception as e:
            logger.error(f"创建时间序列图表失败: {str(e)}")
            return None

    def _create_comparison_chart(self, comparison_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """创建对比图表"""
        if not comparison_data:
            return None

        try:
            names = [item.get("name", f"对比{i}") for i, item in enumerate(comparison_data)]
            values = [item.get("value", 0) for item in comparison_data]

            fig, ax = plt.subplots(figsize=(10, 7))

            # 区分正负值
            colors = ['#10b981' if v >= 0 else '#ef4444' for v in values]
            bars = ax.bar(names, values, color=colors, alpha=0.8, edgecolor='black', linewidth=0.8)

            # 添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                       f'{value:,.1f}',
                       ha='center', va='bottom' if value >= 0 else 'top',
                       fontsize=10, fontweight='bold')

            # 添加零线
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

            ax.set_ylabel('值', fontsize=10, labelpad=10, fontweight='bold')
            ax.set_title('对比数据', fontsize=12, fontweight='bold', pad=15)
            ax.set_xticklabels(names, rotation=30, ha='right', fontsize=9)
            ax.tick_params(axis='both', which='major', labelsize=9)
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout(pad=1.5)

            img_base64 = self._figure_to_base64(fig)
            return {
                "type": "comparison",
                "title": "对比数据",
                "image": img_base64,
                "data": [{"name": n, "value": v} for n, v in zip(names, values)]
            }
        except Exception as e:
            logger.error(f"创建对比图表失败: {str(e)}")
            return None

    def _create_table_preview(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建表格预览数据"""
        if not table_data:
            return {}

        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])

        return {
            "columns": columns,
            "rows": rows[:50],  # 限制显示前50行
            "total_rows": len(rows),
            "preview_rows": min(50, len(rows))
        }

    def _create_numeric_summary(self, numeric_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建数值型数据摘要"""
        values = [item.get("value", 0) for item in numeric_data if isinstance(item.get("value"), (int, float))]

        if not values:
            return {}

        return {
            "count": len(values),
            "sum": float(sum(values)),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "min": float(min(values)),
            "max": float(max(values)),
            "std": float(np.std(values)) if len(values) > 1 else 0
        }

    def _figure_to_base64(self, fig) -> str:
        """将 matplotlib 图形转换为 base64 字符串"""
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format='png',
            dpi=120,
            bbox_inches='tight',
            pad_inches=0.3,
            facecolor='white',
            edgecolor='none',
            transparent=False
        )
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"


# 全局单例
chart_generator_service = ChartGeneratorService()
