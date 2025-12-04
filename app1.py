import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, MultipleLocator, FuncFormatter
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from adjustText import adjust_text
import io, os, base64
import numpy as np

# ==============================================================================
# 1. 配置与资源加载 (使用 cache_resource 缓存静态资源)
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

@st.cache_resource
def load_fonts():
    """加载字体，只运行一次"""
    font_path = 'SourceHanSansSC-Regular.otf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        return True
    else:
        plt.rcParams['axes.unicode_minus'] = False
        return False

font_loaded = load_fonts()
if font_loaded:
    st.sidebar.info("中文字体加载成功！")
else:
    st.sidebar.warning("未找到字体文件，中文可能显示异常。")

# ==============================================================================
# 2. 核心逻辑函数 (使用 cache_data 缓存计算结果)
# ==============================================================================

@st.cache_data(ttl=3600)
def process_raw_data(file_content, filename):
    """
    读取并清洗数据，计算衍生指标。
    缓存机制：只要文件内容没变，就不会重新计算。
    """
    try:
        df = pd.read_excel(file_content, header=1)
    except Exception:
        return None, "读取Excel失败"

    # 列名清洗
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量":"曝光","阅读量":"观看量","播放量":"观看量","观看数":"观看量",
        "点赞数":"点赞","获赞":"点赞","获赞数":"点赞","点赞次数":"点赞",
        "收藏数":"收藏","评论数":"评论","涨粉数":"涨粉","净涨粉":"涨粉",
        "发布形式":"体裁"
    }
    df.rename(columns=rename_map, inplace=True)
    
    # 检查必要列
    required = ["笔记标题","曝光","观看量","收藏","点赞","评论","涨粉","分享","封面点击率","首次发布时间","体裁"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"缺少必要列：{missing}"

    # 时间与排序
    df["首次发布时间"] = pd.to_datetime(df["首次发布时间"], format='%Y年%m月%d日%H时%M分%S秒', errors='coerce')
    df.dropna(subset=["首次发布时间"], inplace=True)
    df.sort_values(by="首次发布时间", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 序号生成
    df['年月'] = df['首次发布时间'].dt.to_period('M').astype(str)
    df.insert(0, "序号", df.groupby("年月").cumcount() + 1)

    # 数值转换
    cols_to_numeric = ["曝光","封面点击率","点赞","观看量","收藏","评论","涨粉","分享"]
    for c in cols_to_numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)

    # 计算衍生指标
    # 使用 replace(0, np.nan) 避免除以零报错
    views = df["观看量"].replace(0, np.nan)
    interact_base = (df["点赞"] + df["收藏"]).replace(0, np.nan)
    
    df["点赞率"] = df["点赞"] / views
    df["收藏率"] = df["收藏"] / views
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, np.nan)
    df["评论率"] = df["评论"] / views
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / views
    df["有效活跃度"] = df["评论"] / interact_base
    df["转粉率"] = df["涨粉"] / views

    return df, None

# ==============================================================================
# 3. 绘图功能 (将被 generate_html_report 调用)
# ==============================================================================

def plot_lines_static(ax, title, cols, df):
    """绘制折线图的基础函数"""
    if df.empty: return
    for col in cols:
        y_data = pd.to_numeric(df[col], errors='coerce')
        ax.plot(df["序号"], y_data, marker="o", linestyle="-", label=col)
        # 标注逻辑优化：略微减少不必要的标注以提升速度，或者保持原样
        for x, y in zip(df["序号"], y_data):
            if pd.notna(y):
                if col in ["赞藏比", "有效活跃度"] or (y < 1 and y > 0): label = f"{y:.2f}"
                elif '率' in col: label = f"{y:.1%}"
                else: label = f"{int(y)}"
                
                offset = abs(y) * 0.1 if y != 0 else 0.05
                ax.text(x, y + offset, label, ha="center", va="bottom", fontsize=10, 
                        path_effects=[path_effects.withStroke(linewidth=2, foreground="white")])
    ax.margins(y=0.4)
    ax.set_title(title)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)

def plot_core_interaction_static(df):
    """绘制核心互动指标"""
    fig, ax = plt.subplots(figsize=(10, 6)) # 略微缩小尺寸提升速度
    if df.empty:
        ax.text(0.5, 0.5, "无数据", ha='center')
        return fig
        
    cols = ["点赞率", "收藏率", "互动率"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    texts = []
    
    for col, color in zip(cols, colors):
        y_vals = pd.to_numeric(df[col], errors='coerce').values
        ax.plot(df["序号"], y_vals, marker="o", linestyle="-", color=color, label=col)
        
        for x, y in zip(df["序号"], y_vals):
            if pd.notna(y):
                ax.text(x, y, f"{y:.1%}", ha="center", va="bottom", fontsize=10, color=color,
                        path_effects=[path_effects.withStroke(linewidth=2, foreground="white")])

    # 注意：adjust_text 运行较慢，如果想要极致速度可以注释掉下面这行
    # adjust_text(texts, ax=ax) 
    
    ax.set_title("核心互动指标趋势")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    return fig

@st.cache_data(show_spinner=False)
def generate_html_report_content(df, filename):
    """
    生成HTML报告的完整内容（包含Base64图片）。
    缓存此函数是大幅提升速度的关键！
    """
    # 关闭交互模式，后台绘图更快
    plt.ioff()
    
    html_parts = [
        f"<html><head><meta charset='utf-8'><title>{filename} 报告</title>",
        "<style>body{font-family:sans-serif; max-width:1000px; margin:auto; padding:20px;}",
        "h2{color:#2c3e50; border-bottom:2px solid #3498db; margin-top:50px;}",
        "img{max-width:100%;}</style></head><body>",
        f"<h1>📊 {filename} 可视化分析报告</h1>"
    ]

    def fig_to_b64(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100) # dpi=100 平衡速度与质量
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig) # 关键：立即释放内存
        return b64

    # 1. 全局体裁分布
    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(df["体裁"].value_counts(), autopct="%1.1f%%", startangle=90)
    ax_pie.set_title("总体体裁分布")
    html_parts.append(f"<h3>总体体裁分布</h3><img src='data:image/png;base64,{fig_to_b64(fig_pie)}'><hr>")

    # 2. 分月生成图表
    sorted_months = sorted(df['年月'].unique())
    for month in sorted_months:
        df_month = df[df['年月'] == month].copy()
        df_month.sort_values(by="首次发布时间", inplace=True)
        
        html_parts.append(f"<h2>📅 {month} 月度分析 (共 {len(df_month)} 篇)</h2>")
        
        if len(df_month) > 0:
            # 核心指标图
            fig1 = plot_core_interaction_static(df_month)
            html_parts.append(f"<h3>核心互动指标</h3><img src='data:image/png;base64,{fig_to_b64(fig1)}'>")

            # 其他趋势图
            metrics = ["点赞率","收藏率","赞藏比","评论率","互动率","有效活跃度","转粉率"]
            for col in metrics:
                fig, ax = plt.subplots(figsize=(10, 4))
                plot_lines_static(ax, f"{col} 趋势图", [col], df_month)
                html_parts.append(f"<img src='data:image/png;base64,{fig_to_b64(fig)}'>")
        else:
            html_parts.append("<p>无数据</p>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)

# ==============================================================================
# 4. 页面显示逻辑
# ==============================================================================
def display_single_file_analysis(df, filename):
    """渲染单个文件的分析结果"""
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')
    st.markdown(f"**📅 时间范围：{df['首次发布时间'].min().date()} 至 {df['首次发布时间'].max().date()}**")

    # 1. 数据表展示
    st.subheader("数据明细")
    show_cols = ["序号","年月","笔记标题","首次发布时间","体裁","曝光","观看量","封面点击率","点赞","收藏","互动率"]
    st.dataframe(df[show_cols].style.format({
        "首次发布时间": "{:%Y-%m-%d}", "封面点击率": "{:.2%}", "互动率": "{:.2%}",
        "曝光": "{:.0f}", "观看量": "{:.0f}", "点赞": "{:.0f}", "收藏": "{:.0f}"
    }, na_rep="--"), height=300)

    # 2. 核心指标汇总
    st.subheader("📈 月度核心指标均值")
    with st.expander("📋 点击展开：各月份详细数据", expanded=False):
        sorted_months = sorted(df['年月'].unique())
        for month in sorted_months:
            df_m = df[df['年月'] == month]
            m_views = df_m["观看量"].sum()
            
            if m_views > 0:
                ctr = (df_m["封面点击率"] * df_m["曝光"]).sum() / df_m["曝光"].sum() if df_m["曝光"].sum() else 0
                interact = (df_m["点赞"] + df_m["收藏"] + df_m["评论"]).sum() / m_views
                
                st.markdown(f"**{month}**")
                c1, c2 = st.columns(2)
                c1.metric("平均点击率", f"{ctr:.2%}")
                c2.metric("平均互动率", f"{interact:.2%}")
            st.divider()

    # 3. HTML 报告下载
    # 这一步会触发缓存的 HTML 生成函数
    with st.spinner(f"正在生成 {filename} 的可视化报告..."):
        html_content = generate_html_report_content(df, filename)
        st.download_button(
            label=f"⬇️ 下载 {filename} 可视化报告 (HTML)",
            data=html_content,
            file_name=f"{os.path.splitext(filename)[0]}_可视化报告.html",
            mime="text/html"
        )
    return df

# ==============================================================================
# 5. 主程序入口
# ==============================================================================

st.title("📊 小红书数据分析平台 (高速版)")
st.markdown("上传 Excel 文件，自动生成可视化报告与汇总分析。")

uploaded_files = st.file_uploader("请上传小红书后台导出的 Excel 文件", type=["xls","xlsx"], accept_multiple_files=True)

if uploaded_files:
    processed_dfs = {}
    all_data_list = []
    
    # 处理每个文件
    for up_file in uploaded_files:
        # 使用 process_raw_data (带缓存)
        # 这里将文件内容读入 bytes 传递给函数，以确保 key 是唯一的且可哈希
        file_bytes = up_file.getvalue() 
        df_result, error = process_raw_data(io.BytesIO(file_bytes), up_file.name)
        
        if error:
            st.error(f"文件 {up_file.name} 错误: {error}")
            continue
            
        # 显示分析结果
        display_single_file_analysis(df_result, up_file.name)
        
        # 收集数据用于汇总
        account_name = os.path.splitext(up_file.name)[0]
        df_export = df_result.copy()
        df_export.insert(0, "账号名", account_name)
        sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:30] or "Sheet1"
        processed_dfs[sheet_name] = df_export
        all_data_list.append(df_export)

    # 全局汇总部分
    if all_data_list:
        st.header("⚔️ 账号/月份 全景对比", divider="orange")
        df_all = pd.concat(all_data_list, ignore_index=True)
        
        # 简化的对比图表逻辑
        df_trend = df_all.groupby(['账号名', '年月']).agg({
            '涨粉':'sum', '观看量':'sum', '点赞':'sum', '收藏':'sum', '评论':'sum'
        }).reset_index()
        df_trend['互动率'] = (df_trend['点赞']+df_trend['收藏']+df_trend['评论'])/df_trend['观看量'].replace(0, np.nan)
        
        # 让用户选择账号
        accounts = df_trend['账号名'].unique()
        selected = st.multiselect("选择要对比的账号：", accounts, default=accounts)
        
        if selected:
            chart_data = df_trend[df_trend['账号名'].isin(selected)]
            
            st.subheader("互动率趋势")
            # 使用 Streamlit 原生图表代替 Matplotlib，速度更快且交互性更好
            st.line_chart(chart_data, x='年月', y='互动率', color='账号名')
            
            st.subheader("涨粉趋势")
            st.line_chart(chart_data, x='年月', y='涨粉', color='账号名')

        # 汇总下载
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            for name, d in processed_dfs.items():
                d.to_excel(writer, sheet_name=name, index=False)
            df_all.to_excel(writer, sheet_name="所有数据汇总", index=False)
            df_trend.to_excel(writer, sheet_name="月度统计", index=False)
            
        st.download_button(
            "⬇️ 下载最终汇总 Excel",
            data=excel_buffer.getvalue(),
            file_name="小红书分析汇总.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
