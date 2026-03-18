"""
测试字体配置是否正常工作
"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from app.services.font_helper import configure_matplotlib_fonts
import io
import base64

# 配置字体
font_name = configure_matplotlib_fonts()

print(f"当前使用字体: {font_name}")
print(f"matplotlib 中文字体设置: {matplotlib.rcParams['font.sans-serif']}")

# 创建测试图表
fig, ax = plt.subplots(figsize=(10, 6))

# 测试数据
x = ['销售', '库存', '采购', '退货', '其他']
y = [150, 200, 180, 50, 30]

bars = ax.bar(x, y, color='#3b82f6', alpha=0.8)
ax.set_xlabel('类别', fontsize=12, labelpad=10)
ax.set_ylabel('数值', fontsize=12, labelpad=10)
ax.set_title('测试图表 - 中文显示', fontsize=14, fontweight='bold', pad=15)
ax.tick_params(axis='both', which='major', labelsize=10)

# 添加数值标签
for bar, value in zip(bars, y):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2., height,
           f'{value}',
           ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.grid(axis='y', alpha=0.3)
plt.tight_layout(pad=1.5)

# 转换为 base64
buf = io.BytesIO()
fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.3, facecolor='white')
plt.close(fig)

buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')
data_url = f"data:image/png;base64,{img_base64}"

print("\n=== 测试完成 ===")
print(f"图表大小: {len(img_base64)} 字符")
print("如果看到字体警告，请检查系统是否有安装中文字体")

# 尝试获取所有可用字体
import matplotlib.font_manager as fm
available_fonts = set([f.name for f in fm.fontManager.ttflist])

print(f"\n=== 可用字体列表（部分）===")
chinese_fonts = [f for f in available_fonts if 'CJK' in f or 'Chinese' in f or 'YaHei' in f or 'SimHei' in f or 'PingFang' in f]
for font in sorted(chinese_fonts)[:10]:
    print(f"  - {font}")

if not chinese_fonts:
    print("  未找到中文字体！")

print("\n=== 推荐安装的中文字体 ===")
print("Windows: Microsoft YaHei (系统自带)")
print("macOS: PingFang SC (系统自带)")
print("Linux: fonts-noto-cjk 或 fonts-wqy-zenhei")

print("\n=== 生成的 base64 数据（前100字符）===")
print(data_url[:100] + "...")
