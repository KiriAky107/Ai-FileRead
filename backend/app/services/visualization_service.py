"""
数据可视化服务 - 使用 matplotlib/plotly 生成统计图表
"""
import io
import base64
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 使用字体辅助模块配置中文字体
from app.services.font_helper import configure_matplotlib_fonts

configure_matplotlib_fonts()

logger = logging.getLogger(__name__)


class VisualizationService:
    """数据可视化服务类"""

    def __init__(self):
        self.output_dir = Path(__file__).resolve().parent.parent.parent / "data" / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_and_visualize(
        self,
        excel_data: Dict[str, Any],
        analysis_type: str = "statistics"
    ) -> Dict[str, Any]:
        """
        分析数据并生成可视化图表

        Args:
            excel_data: Excel 解析后的数据
            analysis_type: 分析类型

        Returns:
            Dict[str, Any]: 包含图表数据和统计信息的结果
        """
        try:
            columns = excel_data.get("columns", [])
            rows = excel_data.get("rows", [])

            if not columns or not rows:
                return {
                    "success": False,
                    "error": "没有数据可用于分析"
                }

            # 转换为 DataFrame
            # 过滤掉行数与列数不匹配的数据
            valid_rows = [row for row in rows if len(row) == len(columns)]
            if len(valid_rows) < len(rows):
                logger.warning(f"过滤了 {len(rows) - len(valid_rows)} 行无效数据（列数不匹配）")
            df = pd.DataFrame(valid_rows, columns=columns)

            # 根据列类型分类
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_columns = df.select_dtypes(exclude=[np.number]).columns.tolist()

            # 生成统计信息
            statistics = self._generate_statistics(df, numeric_columns, categorical_columns)

            # 生成图表
            charts = self._generate_charts(df, numeric_columns, categorical_columns)

            # 生成数据分布信息
            distributions = self._generate_distributions(df, categorical_columns)

            return {
                "success": True,
                "statistics": statistics,
                "charts": charts,
                "distributions": distributions,
                "row_count": len(df),
                "column_count": len(columns)
            }

        except Exception as e:
            logger.error(f"可视化分析失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_statistics(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str],
        categorical_columns: List[str]
    ) -> Dict[str, Any]:
        """生成统计信息"""
        statistics = {
            "numeric": {},
            "categorical": {}
        }

        # 数值型列统计
        for col in numeric_columns:
            try:
                stats = {
                    "count": int(df[col].count()),
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()) if df[col].count() > 1 else 0,
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "q25": float(df[col].quantile(0.25)),
                    "q75": float(df[col].quantile(0.75)),
                    "missing": int(df[col].isna().sum())
                }
                statistics["numeric"][col] = stats
            except Exception as e:
                logger.warning(f"列 {col} 统计失败: {str(e)}")

        # 分类型列统计
        for col in categorical_columns:
            try:
                value_counts = df[col].value_counts()
                stats = {
                    "unique": int(df[col].nunique()),
                    "most_common": str(value_counts.index[0]) if len(value_counts) > 0 else "",
                    "most_common_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    "missing": int(df[col].isna().sum()),
                    "distribution": {str(k): int(v) for k, v in value_counts.items()}
                }
                statistics["categorical"][col] = stats
            except Exception as e:
                logger.warning(f"列 {col} 统计失败: {str(e)}")

        return statistics

    def _generate_charts(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str],
        categorical_columns: List[str]
    ) -> Dict[str, Any]:
        """生成图表"""
        charts = {}

        # 1. 数值型列的直方图
        charts["numeric_charts"] = []
        for col in numeric_columns[:5]:  # 限制最多 5 个数值列
            chart_data = self._create_histogram(df[col], col)
            if chart_data:
                charts["numeric_charts"].append(chart_data)

        # 2. 分类型列的条形图
        charts["categorical_charts"] = []
        for col in categorical_columns[:5]:  # 限制最多 5 个分类型列
            chart_data = self._create_bar_chart(df[col], col)
            if chart_data:
                charts["categorical_charts"].append(chart_data)

        # 3. 数值型列的箱线图
        charts["box_plots"] = []
        if len(numeric_columns) > 0:
            chart_data = self._create_box_plot(df[numeric_columns[:5]], numeric_columns[:5])
            if chart_data:
                charts["box_plots"].append(chart_data)

        # 4. 相关性热力图
        if len(numeric_columns) >= 2:
            chart_data = self._create_correlation_heatmap(df[numeric_columns], numeric_columns)
            if chart_data:
                charts["correlation"] = chart_data

        return charts

    def _create_histogram(self, series: pd.Series, column_name: str) -> Optional[Dict[str, Any]]:
        """创建直方图"""
        try:
            fig, ax = plt.subplots(figsize=(11, 7))
            ax.hist(series.dropna(), bins=20, edgecolor='black', alpha=0.7, color='#3b82f6')
            ax.set_xlabel(column_name, fontsize=10, labelpad=10)
            ax.set_ylabel('频数', fontsize=10, labelpad=10)
            ax.set_title(f'{column_name} 分布', fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, axis='y')
            ax.tick_params(axis='both', which='major', labelsize=9)

            # 改进布局
            plt.tight_layout(pad=1.5, w_pad=1.0, h_pad=1.0)

            # 转换为 base64
            img_base64 = self._figure_to_base64(fig)

            return {
                "type": "histogram",
                "column": column_name,
                "image": img_base64,
                "stats": {
                    "mean": float(series.mean()),
                    "median": float(series.median()),
                    "std": float(series.std()) if len(series) > 1 else 0
                }
            }
        except Exception as e:
            logger.error(f"创建直方图失败 ({column_name}): {str(e)}")
            return None

    def _create_bar_chart(self, series: pd.Series, column_name: str) -> Optional[Dict[str, Any]]:
        """创建条形图"""
        try:
            value_counts = series.value_counts().head(10)  # 只显示前 10 个
            fig, ax = plt.subplots(figsize=(12, 7))

            # 处理标签显示
            labels = [str(x)[:15] + '...' if len(str(x)) > 15 else str(x) for x in value_counts.index]
            x_pos = range(len(value_counts))
            bars = ax.bar(x_pos, value_counts.values, color='#10b981', alpha=0.8, edgecolor='black', linewidth=0.5)

            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
            ax.set_xlabel(column_name, fontsize=10, labelpad=10)
            ax.set_ylabel('数量', fontsize=10, labelpad=10)
            ax.set_title(f'{column_name} 分布 (Top 10)', fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, axis='y')
            ax.tick_params(axis='both', which='major', labelsize=9)

            # 添加数值标签（位置稍微上移）
            max_val = value_counts.values.max()
            y_offset = max_val * 0.02 if max_val > 0 else 0.5
            for bar, value in zip(bars, value_counts.values):
                ax.text(bar.get_x() + bar.get_width() / 2., value + y_offset,
                        f'{int(value)}',
                        ha='center', va='bottom', fontsize=8, fontweight='bold')

            # 改进布局
            plt.tight_layout(pad=1.5, w_pad=1.0, h_pad=1.0)

            # 转换为 base64
            img_base64 = self._figure_to_base64(fig)

            return {
                "type": "bar_chart",
                "column": column_name,
                "image": img_base64,
                "categories": {str(k): int(v) for k, v in value_counts.items()}
            }
        except Exception as e:
            logger.error(f"创建条形图失败 ({column_name}): {str(e)}")
            return None

    def _create_box_plot(self, df: pd.DataFrame, columns: List[str]) -> Optional[Dict[str, Any]]:
        """创建箱线图"""
        try:
            fig, ax = plt.subplots(figsize=(14, 7))

            # 准备数据
            box_data = [df[col].dropna() for col in columns]
            bp = ax.boxplot(box_data, labels=columns, patch_artist=True,
                          notch=True, showcaps=True, showfliers=True)

            # 美化箱线图
            box_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            for patch, color in zip(bp['boxes'], box_colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
                patch.set_linewidth(1.5)

            # 设置其他元素样式
            for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
                plt.setp(bp[element], linewidth=1.5)

            ax.set_ylabel('值', fontsize=10, labelpad=10)
            ax.set_title('数值型列分布对比', fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, axis='y')

            # 旋转 x 轴标签以避免重叠
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
            ax.tick_params(axis='both', which='major', labelsize=9)

            # 改进布局
            plt.tight_layout(pad=1.5, w_pad=1.5, h_pad=1.0)

            # 转换为 base64
            img_base64 = self._figure_to_base64(fig)

            return {
                "type": "box_plot",
                "columns": columns,
                "image": img_base64
            }
        except Exception as e:
            logger.error(f"创建箱线图失败: {str(e)}")
            return None

    def _create_correlation_heatmap(self, df: pd.DataFrame, columns: List[str]) -> Optional[Dict[str, Any]]:
        """创建相关性热力图"""
        try:
            # 计算相关系数
            corr = df.corr()

            fig, ax = plt.subplots(figsize=(11, 9))
            im = ax.imshow(corr, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

            # 设置刻度
            n_cols = len(corr)
            ax.set_xticks(np.arange(n_cols))
            ax.set_yticks(np.arange(n_cols))

            # 处理过长的列名
            x_labels = [str(col)[:10] + '...' if len(str(col)) > 10 else str(col) for col in corr.columns]
            y_labels = [str(col)[:10] + '...' if len(str(col)) > 10 else str(col) for col in corr.columns]

            ax.set_xticklabels(x_labels, rotation=30, ha='right', fontsize=9)
            ax.set_yticklabels(y_labels, fontsize=9)

            # 添加数值标签，根据相关性值选择颜色
            for i in range(n_cols):
                for j in range(n_cols):
                    value = corr.iloc[i, j]
                    # 根据背景色深浅选择文字颜色
                    text_color = 'white' if abs(value) > 0.5 else 'black'
                    ax.text(j, i, f'{value:.2f}',
                            ha="center", va="center", color=text_color,
                            fontsize=8, fontweight='bold' if abs(value) > 0.7 else 'normal')

            ax.set_title('数值型列相关性热力图', fontsize=12, fontweight='bold', pad=15)
            ax.tick_params(axis='both', which='major', labelsize=9)

            # 添加颜色条
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('相关系数', rotation=270, labelpad=20, fontsize=10)
            cbar.ax.tick_params(labelsize=9)

            # 改进布局
            plt.tight_layout(pad=2.0, w_pad=1.0, h_pad=1.0)

            # 转换为 base64
            img_base64 = self._figure_to_base64(fig)

            return {
                "type": "correlation_heatmap",
                "columns": columns,
                "image": img_base64,
                "correlation_matrix": corr.to_dict()
            }
        except Exception as e:
            logger.error(f"创建相关性热力图失败: {str(e)}")
            return None

    def _generate_distributions(
        self,
        df: pd.DataFrame,
        categorical_columns: List[str]
    ) -> Dict[str, Any]:
        """生成数据分布信息"""
        distributions = {}

        for col in categorical_columns[:5]:
            try:
                value_counts = df[col].value_counts()
                total = len(df)

                distributions[col] = {
                    "categories": {str(k): int(v) for k, v in value_counts.items()},
                    "percentages": {str(k): round(v / total * 100, 2) for k, v in value_counts.items()},
                    "unique_count": len(value_counts)
                }
            except Exception as e:
                logger.warning(f"列 {col} 分布生成失败: {str(e)}")

        return distributions

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
visualization_service = VisualizationService()
