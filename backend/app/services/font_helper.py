"""
字体辅助模块 - 处理中文字体检测和配置
"""
import matplotlib
import matplotlib.font_manager as fm
import platform
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_chinese_font() -> str:
    """
    获取可用的中文字体

    Returns:
        str: 可用的中文字体名称
    """
    # 获取系统中所有可用字体
    available_fonts = set([f.name for f in fm.fontManager.ttflist])

    # 定义字体优先级列表
    # Windows 优先
    if platform.system() == 'Windows':
        font_list = [
            'Microsoft YaHei',  # 微软雅黑
            'SimHei',           # 黑体
            'SimSun',           # 宋体
            'KaiTi',           # 楷体
            'FangSong',         # 仿宋
            'STXihei',          # 华文细黑
            'STKaiti',          # 华文楷体
            'STSong',           # 华文宋体
            'STFangsong',       # 华文仿宋
        ]
    # macOS 优先
    elif platform.system() == 'Darwin':
        font_list = [
            'PingFang SC',      # 苹方-简
            'PingFang TC',      # 苹方-繁
            'Heiti SC',        # 黑体-简
            'Heiti TC',        # 黑体-繁
            'STHeiti',          # 华文黑体
            'STSong',           # 华文宋体
            'STKaiti',          # 华文楷体
            'Arial Unicode MS',  # Arial Unicode MS
        ]
    # Linux 优先
    else:
        font_list = [
            'Noto Sans CJK SC', # Noto Sans CJK 简体中文
            'WenQuanYi Micro Hei', # 文泉驿微米黑
            'AR PL UMing CN',   # AR PL UMing
            'AR PL UKai CN',    # AR PL UKai
            'ZCOOL XiaoWei',   # ZCOOL 小薇
        ]

    # 通用备选字体
    font_list.extend([
        'SimHei',
        'Microsoft YaHei',
        'Arial Unicode MS',
        'Droid Sans Fallback',
    ])

    # 查找第一个可用的字体
    for font_name in font_list:
        if font_name in available_fonts:
            logger.info(f"找到中文字体: {font_name}")
            return font_name

    # 如果没找到，尝试获取第一个中文字体
    for font in fm.fontManager.ttflist:
        if 'CJK' in font.name or 'SC' in font.name or 'TC' in font.name:
            logger.info(f"使用找到的中文字体: {font.name}")
            return font.name

    # 最终备选：使用系统默认字体
    logger.warning("未找到合适的中文字体，使用默认字体")
    return 'sans-serif'


def configure_matplotlib_fonts():
    """
    配置 matplotlib 的字体设置
    """
    chinese_font = get_chinese_font()

    # 配置字体
    matplotlib.rcParams['font.sans-serif'] = [chinese_font]
    matplotlib.rcParams['axes.unicode_minus'] = False
    matplotlib.rcParams['figure.dpi'] = 100
    matplotlib.rcParams['savefig.dpi'] = 120

    # 字体大小设置
    matplotlib.rcParams['font.size'] = 10
    matplotlib.rcParams['axes.labelsize'] = 10
    matplotlib.rcParams['axes.titlesize'] = 11
    matplotlib.rcParams['xtick.labelsize'] = 9
    matplotlib.rcParams['ytick.labelsize'] = 9
    matplotlib.rcParams['legend.fontsize'] = 9

    logger.info(f"配置完成，使用字体: {chinese_font}")
    return chinese_font
