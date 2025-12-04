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
# 1. 基础配置与资源加载 (只运行一次)
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

@st.cache_resource
def load_fonts():
    """加载字体，使用缓存避免重复加载"""
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

fonts_loaded = load_fonts()
if fonts_loaded:
    st.sidebar.info("中文字体加载成功！")
else:
    st.sidebar.warning("未找到专用字体文件，使用系统默认字体。")

# ==============================================================================
# 2. 绘图辅助函数 (保持原有逻辑)
# ==============================================================================
def save_fig_to_base64(fig):
    """将matplotlib图片转为base64字符串，用于HTML嵌入"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig) # 及时释放内存
    return b64

def plot_lines(ax, title, cols, df):
    """绘制折线图"""
    if df.empty: return
    for col in cols:
        y_data = pd.to_numeric(df[col], errors='coerce')
        ax.plot(df["序号"], y_data, marker="o", linestyle="-", label=col)
        for x, y in zip(df["序号"], y_data):
            if pd.notna(y): 
                label = f"{y:.1%}" if '率' in col else (f"{y:.2f}" if y < 1 and y > 0 or col in ["赞藏比", "有效活跃度"] else f"{int(y)}")
                offset = abs(y) * 0.1 if y != 0 else 0.05
                ax.text(x, y + offset, label, ha="center", va="bottom", fontsize=12, color='black',
                        path_effects=[path_effects.withStroke(linewidth=3, foreground="white")])
    ax.margins(y=0.4)
    ax.set_xlabel("本月发布顺序 (序号)", fontsize=12) 
    ax.set_ylabel("数值")
    ax.set_title(title)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)

def plot_core_interaction(df):
    """绘制核心互动指标"""
    fig, ax = plt.subplots(figsize=(12, 8))
    if df.empty:
        ax.text(0.5, 0.5, "无有效数据", ha='center', va='center')
        return fig
    
    cols = ["点赞率", "收藏率", "互动率"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    texts = []
    line_data = {}
    for col, color in zip(cols, colors):
        y_vals = pd.to_numeric(df[col], errors='coerce').values
        ax.plot(df["序号"], y_vals, marker="o", linestyle="-", color=color, label=col)
        line_data[col] = y_vals
    
    avg_values = {col: pd.Series(vals).mean(skipna=True) for col, vals in line_data.items()}
    bottom_line = min(avg_values, key=avg_values.get) if avg_values else cols[0]

    for col, color in zip(cols, colors):
        y_vals = pd.to_numeric(df[col], errors='coerce')
        for x, y in zip(df["序号"], y_vals):
            if pd.notna(y):
                offset = -0.06 if col == bottom_line else 0.04
                va = "top" if col == bottom_line else "bottom"
                text = ax.text(x, y + offset, f"{y:.1%}", ha="center", va=va, fontsize=12, color=color,
                               path_effects=[path_effects.withStroke(linewidth=3, foreground="white")])
                texts.append(text)
    
    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", lw=0.4, color='gray'))
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.margins(y=0.3)
    ax.set_xlabel("本月发布顺序 (序号)", fontsize=12)
    ax.set_title("核心互动指标趋势")
    ax.legend(title=f"最下面的线：{bottom_line}", title_fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    return fig

# ==============================================================================
# 3. 数据处理核心逻辑 (带缓存)
# ==============================================================================
@st.cache_data(show_spinner=False)
def process_raw_dataframe(df_raw):
    """清洗和计算衍生指标，缓存结果防止重复计算"""
    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量":"曝光","阅读量":"观看量","播放量":"观看量","观看数":"观看量",
        "点赞数":"点赞","获赞":"点赞","获赞数":"点赞","点赞次数":"点赞",
        "收藏数":"收藏","评论数":"评论","涨粉数":"涨粉","净涨粉":"涨粉",
        "发布形式":"体裁"
    }
    df.rename(columns=rename_map, inplace=True)
    
    required = ["笔记标题","曝光","观看量","收藏","点赞","评论","涨粉","分享","封面点击率","首次发布时间","体裁"]
    if any(c not in df.columns for c in required):
        return None  # 缺失列

    # 时间处理
    df["首次发布时间"] = pd.to_datetime(df["首次发布时间"], format='%Y年%m月%d日%H时%M分%S秒', errors='coerce')
    df.dropna(subset=["首次发布时间"], inplace=True)
    df.sort_values(by="首次发布时间", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # 序号生成
    df['年月'] = df['首次发布时间'].dt.to_period('M').astype(str)
    df.insert(0, "序号", df.groupby("年月").cumcount() + 1)

    # 数值转换
    for c in ["曝光","封面点击率","点赞","观看量","收藏","评论","涨粉","分享"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)
        
    # 衍生指标
    df["点赞率"] = df["点赞"] / df["观看量"].replace(0, np.nan)
    df["收藏率"] = df["收藏"] / df["观看量"].replace(0, np.nan)
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, np.nan)
    df["评论率"] = df["评论"] / df["观看量"].replace(0, np.nan)
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / df["观看量"].replace(0, np.nan)
    df["有效活跃度"] = df["评论"] / (df["点赞"] + df["收藏"]).replace(0, np.nan)
    df["转粉率"] = df["涨粉"] / df["观看量"].replace(0, np.nan)
    
    return df

@st.cache_data(show_spinner=False)
def generate_html_report_content(df, filename):
    """
    🔥🔥 核心优化点：生成HTML报告。
    加上 @st.cache_data 后，只要数据没变，就不会重新画几十张图。
    极大提升页面交互时的响应速度。
    """
    html_parts = [
        f"<html><head><meta charset='utf-8'><title>{filename} 可视化报告</title>",
        "<style>body{font-family:sans-serif; max-width:1000px; margin:auto; padding:20px;}",
        "h2{color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:10px; margin-top:50px;}",
        "h3{color:#555; margin-top:30px;}</style></head><body>",
        f"<h1>📊 {filename} 可视化分析报告</h1>"
    ]

    # 总体体裁分布
    fig_pie, ax_pie = plt.subplots(figsize=(6,6))
    pie_data = df["体裁"].value_counts()
    ax_pie.pie(pie_data, autopct="%1.1f%%", startangle=90, colors=["#ff9999","#66b3ff"])
    ax_pie.set_title("总体 图文 vs 视频比例")
    html_parts.append(f"<h3>总体体裁分布</h3><img src='data:image/png;base64,{save_fig_to_base64(fig_pie)}' style='max-width:100%;'><hr>")

    # 分月图表
    sorted_months = sorted(df['年月'].unique())
    for month in sorted_months:
        df_month = df[df['年月'] == month].copy()
        df_month.sort_values(by="首次发布时间", ascending=True, inplace=True)
        
        html_parts.append(f"<h2>📅 {month} 月度分析 (共 {len(df_month)} 篇笔记)</h2>")

        if len(df_month) > 0:
            # 核心互动趋势
            fig1 = plot_core_interaction(df_month)
            html_parts.append(f"<h3>{month} - 核心互动指标趋势</h3><img src='data:image/png;base64,{save_fig_to_base64(fig1)}' style='max-width:100%;'><hr>")

            # 其他单项指标
            for col in ["点赞率","收藏率","赞藏比","评论率","互动率","有效活跃度","转粉率"]:
                fig, ax = plt.subplots(figsize=(12,4))
                plot_lines(ax, f"{month} - {col} 趋势图", [col], df_month)
                html_parts.append(f"<h3>{month} - {col} 趋势图</h3><img src='data:image/png;base64,{save_fig_to_base64(fig)}' style='max-width:100%;'><hr>")
        else:
            html_parts.append("<p>该月无有效数据。</p>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)

# ==============================================================================
# 4. 界面展示逻辑
# ==============================================================================
def display_single_file_analysis(df, filename):
    """展示单个文件的分析结果"""
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')
    st.markdown(f"**📅 数据时间范围：{df['首次发布时间'].min().date()} 至 {df['首次发布时间'].max().date()}**")

    # 数据表展示
    st.subheader("分析后的数据表")
    show_cols = [
        "序号","年月","笔记标题","首次发布时间","体裁","曝光","观看量","封面点击率",
        "点赞","评论","收藏","涨粉","分享",
        "点赞率","收藏率","互动率","转粉率","赞藏比","有效活跃度"
    ]
    st.dataframe(df[show_cols].style.format({
        "首次发布时间": "{:%Y-%m-%d %H:%M}", "封面点击率": "{:.2%}", "点赞率": "{:.2%}", 
        "收藏率": "{:.2%}", "互动率": "{:.2%}", "转粉率": "{:.2%}", "赞藏比": "{:.2f}", 
        "有效活跃度": "{:.2f}", "曝光": "{:.0f}", "观看量": "{:.0f}", "点赞": "{:.0f}",
        "评论": "{:.0f}", "收藏": "{:.0f}", "涨粉": "{:.0f}", "分享": "{:.0f}"
    }, na_rep="--"))

    # 核心指标平均值 (含折叠)
    st.subheader("📈 核心指标平均值")
    with st.expander("📋 点击收起/展开：各月份详细平均指标数据", expanded=False):
        sorted_months = sorted(df['年月'].unique())
        for month in sorted_months:
            df_month = df[df['年月'] == month]
            m_views = df_month["观看量"].sum()
            m_expo = df_month["曝光"].sum()
            m_likes = df_month["点赞"].sum()
            m_favs = df_month["收藏"].sum()
            m_comms = df_month["评论"].sum()

            m_ctr = ((df_month["封面点击率"] * df_month["曝光"]).sum() / m_expo) if m_expo else 0
            m_like_r = (m_likes / m_views) if m_views else 0
            m_fav_r = (m_favs / m_views) if m_views else 0
            m_eng_r = ((m_likes + m_comms + m_favs) / m_views) if m_views else 0

            st.markdown(f"**🗓️ {month} 月度表现 (共 {len(df_month)} 篇)**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"平均点击率", f"{m_ctr:.2%}")
            c2.metric(f"平均点赞率", f"{m_like_r:.2%}")
            c3.metric(f"平均收藏率", f"{m_fav_r:.2%}")
            c4.metric(f"平均互动率", f"{m_eng_r:.2%}")
            st.markdown("---")

    # HTML 报告生成与下载
    with st.spinner(f"正在为 {filename} 生成可视化报告，请稍候..."):
        # 调用缓存函数生成HTML内容
        html_content = generate_html_report_content(df, filename)
        
        # 保存文件供下载
        html_dir = "html_reports"
        os.makedirs(html_dir, exist_ok=True)
        html_path = os.path.join(html_dir, f"{os.path.splitext(filename)[0]}_可视化报告.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        st.success(f"✅ 可视化报告已生成")
        st.download_button(f"下载 {filename} 的可视化HTML报告", data=html_content, file_name=os.path.basename(html_path), mime="text/html")

# ==============================================================================
# 5. 主逻辑
# ==============================================================================
def main():
    st.title("📊 小红书数据分析平台")
    st.markdown("上传 Excel 文件，系统会生成**可视化 HTML 报告**与汇总 Excel。")
    st.info("💡 提示：已启用高速缓存，切换下方图表时不再卡顿。")

    uploaded_files = st.file_uploader("请上传小红书后台导出的 Excel 文件", type=["xls","xlsx"], accept_multiple_files=True)

    if uploaded_files:
        placeholder_top = st.empty()
        processed_dfs = {}
        all_data_list = []

        # 处理每个上传的文件
        for up_file in uploaded_files:
            try:
                df_raw = pd.read_excel(up_file, header=1)
                # 使用缓存的处理函数
                df_processed = process_raw_dataframe(df_raw)
                
                if df_processed is not None:
                    display_single_file_analysis(df_processed, up_file.name)
                    
                    account_name = os.path.splitext(up_file.name)[0]
                    df_export = df_processed.copy()
                    df_export.insert(0, "账号名", account_name)
                    
                    sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:31] or f"Sheet_{len(processed_dfs)+1}"
                    processed_dfs[sheet_name] = df_export
                    all_data_list.append(df_export)
                else:
                    st.error(f"文件 {up_file.name} 缺少必要列，跳过处理。")
            except Exception as e:
                st.error(f"处理文件 {up_file.name} 时发生错误: {e}")

        # 汇总分析部分
        if processed_dfs and all_data_list:
            st.markdown("---")
            st.header(" 账号/月份 核心指标趋势 & 环比分析", divider="orange")
            
            df_all = pd.concat(all_data_list, ignore_index=True)
            if '年月' not in df_all.columns:
                 df_all['年月'] = df_all['首次发布时间'].dt.to_period('M').astype(str)

            df_all['估算点击数'] = df_all['封面点击率'] * df_all['曝光']
            
            # 聚合计算
            df_trend = df_all.groupby(['账号名', '年月']).agg({
                '曝光': 'sum', '观看量': 'sum', '点赞': 'sum', '收藏': 'sum', '评论': 'sum', '涨粉': 'sum', '估算点击数': 'sum'
            }).reset_index()

            df_trend['互动率'] = (df_trend['点赞'] + df_trend['收藏'] + df_trend['评论']) / df_trend['观看量'].replace(0, np.nan)
            df_trend['封面点击率'] = df_trend['估算点击数'] / df_trend['曝光'].replace(0, np.nan)
            df_trend.sort_values(by=['账号名', '年月'], ascending=[True, True], inplace=True)
            
            # 环比计算
            df_trend['涨粉环比'] = df_trend.groupby('账号名')['涨粉'].pct_change()
            df_trend['互动率环比'] = df_trend.groupby('账号名')['互动率'].pct_change()
            df_trend['点击率环比'] = df_trend.groupby('账号名')['封面点击率'].pct_change()
            df_trend.replace([np.inf, -np.inf], np.nan, inplace=True)

            # 交互图表
            all_accounts = df_trend['账号名'].unique()
            selected_accounts = st.multiselect("👇 1. 请选择要对比趋势的账号：", all_accounts, default=all_accounts)

            if selected_accounts:
                df_chart = df_trend[df_trend['账号名'].isin(selected_accounts)].copy()
                df_chart.sort_values(by='年月', ascending=True, inplace=True)
                
                # 绘图函数 (内部函数无需缓存，因为数据量小且依赖交互)
                def plot_metric_chart(metric, title, is_pct=True):
                    fig, ax = plt.subplots(figsize=(14, 6))
                    for account in selected_accounts:
                        sub = df_chart[df_chart['账号名'] == account]
                        if not sub.empty:
                            ax.plot(sub['年月'], sub[metric], marker='o', linewidth=2, label=account)
                            if len(sub) < 24: # 数据点少时显示标签
                                for x, y in zip(sub['年月'], sub[metric]):
                                    if pd.notna(y):
                                        txt = f"{y:.1%}" if is_pct else f"{int(y)}"
                                        ax.text(x, y, txt, ha='center', va='bottom', fontsize=12)
                    ax.set_title(title)
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.5)
                    if is_pct: ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
                    return fig

                col_g1, col_g2 = st.columns(2)
                with col_g1: st.pyplot(plot_metric_chart('互动率', '互动率月度走势'))
                with col_g2: st.pyplot(plot_metric_chart('封面点击率', '封面点击率月度走势'))
                
                col_g3, col_g4 = st.columns(2)
                with col_g3: st.pyplot(plot_metric_chart('涨粉', '月度净涨粉走势', is_pct=False))

                # 数据详情表
                with st.expander("📋 点击展开：查看月度对比详细数据表", expanded=True):
                    st.dataframe(df_chart.style.format({
                        '涨粉': '{:,.0f}', '互动率': '{:.2%}', '封面点击率': '{:.2%}', 
                        '涨粉环比': '{:+.1%}', '互动率环比': '{:+.1%}', '点击率环比': '{:+.1%}'
                    }, na_rep="--"))
            
            # 透视表逻辑
            st.markdown("---")
            st.subheader("📅 核心指标详细透视表")
            metric_opt = st.selectbox("👇 请选择指标：", ["涨粉数", "互动率", "封面点击率"])
            metric_map = {
                "涨粉数": ("涨粉", "涨粉环比", "{:,.0f}"),
                "互动率": ("互动率", "互动率环比", "{:.2%}"),
                "封面点击率": ("封面点击率", "点击率环比", "{:.2%}")
            }
            val_col, mom_col, fmt = metric_map[metric_opt]
            
            if not df_trend.empty:
                pivot = df_trend.pivot(index='账号名', columns='年月', values=[val_col, mom_col])
                # 重排多层列
                months = sorted(df_trend['年月'].unique())
                new_cols = [(val_col, m) for m in months] + [(mom_col, m) for m in months]
                pivot = pivot.reindex(columns=new_cols)
                # 扁平化列名
                pivot.columns = [f"{m}" if c[0]==val_col else f"{m} 环比" for c in pivot.columns]
                st.dataframe(pivot.style.format(lambda x: fmt.format(x) if pd.notna(x) else "--" if "环比" not in fmt else "{:+.1%}".format(x), na_rep="--"))

            # Excel下载
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                for name, d in processed_dfs.items():
                    d.to_excel(writer, sheet_name=name, index=False)
                pd.concat(all_data_list, ignore_index=True).to_excel(writer, sheet_name="所有数据汇总", index=False)
                df_trend.to_excel(writer, sheet_name="月度统计", index=False)

            with placeholder_top.container():
                st.header("汇总Excel下载", divider="rainbow")
                st.download_button("⬇️ 下载汇总Excel报告", data=excel_buffer.getvalue(), file_name="小红书分析汇总.xlsx")

if __name__ == "__main__":
    main()
