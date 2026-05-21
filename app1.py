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
# 初始化页面
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

# ==============================================================================
# 中文字体加载（一次性资源，开销很小，可以保持原样）
# ==============================================================================
font_path = 'SourceHanSansSC-Regular.otf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    st.sidebar.info("中文字体加载成功！")
else:
    st.sidebar.warning(f"未找到字体文件 '{font_path}'，中文可能显示异常。")
    plt.rcParams['axes.unicode_minus'] = False


# ==============================================================================
# 基础绘图函数：带标注的线图（保持原有行为）
# ==============================================================================
def plot_lines(ax, title, cols, df):
    if df.empty:
        return

    for col in cols:
        y_data = pd.to_numeric(df[col], errors='coerce')
        ax.plot(df["序号"], y_data, marker="o", linestyle="-", label=col)
        for x, y in zip(df["序号"], y_data):
            if pd.notna(y):
                if col in ["赞藏比", "有效活跃度"]:
                    label = f"{y:.2f}"
                elif '率' in col:
                    label = f"{y:.1%}"
                elif y < 1 and y > 0:
                    label = f"{y:.2f}"
                else:
                    label = f"{int(y)}"
                offset = abs(y) * 0.1 if y != 0 else 0.05
                ax.text(
                    x, y + offset, label,
                    ha="center", va="bottom",
                    fontsize=12, color='black',
                    path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
                )

    ax.margins(y=0.4)
    ax.set_xlabel("本月发布顺序 (序号)", fontsize=12)
    ax.set_ylabel("数值")
    ax.set_title(title)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)


# ==============================================================================
# 核心互动指标趋势函数（保持原有行为）
# ==============================================================================
def plot_core_interaction(df):
    fig, ax = plt.subplots(figsize=(12, 8))

    if df.empty:
        ax.text(0.5, 0.5, "无有效数据", ha='center', va='center')
        return fig, ax

    cols = ["点赞率", "收藏率", "互动率"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    texts = []
    line_data = {}

    for col, color in zip(cols, colors):
        y_vals = pd.to_numeric(df[col], errors='coerce').values
        ax.plot(df["序号"], y_vals, marker="o", linestyle="-", color=color, label=col)
        line_data[col] = y_vals

    # 均值 & 找到最下面的线
    avg_values = {col: pd.Series(vals).mean(skipna=True) for col, vals in line_data.items()}
    bottom_line = min(avg_values, key=avg_values.get) if avg_values else cols[0]

    for col, color in zip(cols, colors):
        y_vals = pd.to_numeric(df[col], errors='coerce')
        for x, y in zip(df["序号"], y_vals):
            if pd.notna(y):
                label = f"{y:.1%}"
                if col == bottom_line:
                    offset = -0.06
                    va = "top"
                else:
                    offset = 0.04
                    va = "bottom"
                text = ax.text(
                    x, y + offset, label,
                    ha="center", va=va,
                    fontsize=12, color=color,
                    path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
                )
                texts.append(text)

    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", lw=0.4, color='gray'))
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.margins(y=0.3)
    ax.set_xlabel("本月发布顺序 (序号)", fontsize=12)
    ax.set_ylabel("数值")
    ax.set_title("核心互动指标趋势")
    ax.legend(title=f"最下面的线：{bottom_line}", title_fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    return fig, ax


# ==============================================================================
# 纯计算：根据 DataFrame 生成 HTML 报告（不使用 Streamlit，方便缓存）
# ==============================================================================
def build_html_report(df: pd.DataFrame, filename: str) -> str:
    """生成单个文件的 HTML 可视化报告（纯计算，无 Streamlit 调用）"""

    def fig_to_img_block(fig, caption: str) -> str:
        buf = io.BytesIO()
        # dpi 可以略微调低一点，减小体积和生成时间；不影响功能，只影响图片清晰度
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=180)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        return f"<h3>{caption}</h3><img src='data:image/png;base64,{b64}' style='max-width:100%;'><hr>"

    html_parts = [
        f"<html><head><meta charset='utf-8'><title>{filename} 可视化报告</title>",
        "<style>body{font-family:sans-serif; max-width:1000px; margin:auto; padding:20px;}",
        "h2{color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:10px; margin-top:50px;}",
        "h3{color:#555; margin-top:30px;}</style></head><body>",
        f"<h1>📊 {filename} 可视化分析报告</h1>"
    ]

    # --- 全局图表：体裁分布 ---
    fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
    pie_data = df["体裁"].value_counts()
    ax_pie.pie(pie_data, autopct="%1.1f%%", startangle=90, colors=["#ff9999", "#66b3ff"])
    ax_pie.set_title("总体 图文 vs 视频比例")
    html_parts.append(fig_to_img_block(fig_pie, "总体体裁分布"))

    # --- 分月图表 ---
    sorted_months = sorted(df['年月'].unique())
    for month in sorted_months:
        df_month = df[df['年月'] == month].copy()
        df_month.sort_values(by="首次发布时间", ascending=True, inplace=True)
        note_count = len(df_month)

        html_parts.append(f"<h2>📅 {month} 月度分析 (共 {note_count} 篇笔记)</h2>")

        if note_count > 0:
            # 核心互动指标
            fig1, ax1 = plot_core_interaction(df_month)
            html_parts.append(fig_to_img_block(fig1, f"{month} - 核心互动指标趋势"))

            # 各单项指标
            for col in ["点赞率", "收藏率", "赞藏比", "评论率", "互动率", "有效活跃度", "转粉率"]:
                fig, ax = plt.subplots(figsize=(12, 4))
                plot_lines(ax, f"{month} - {col} 趋势图", [col], df_month)
                html_parts.append(fig_to_img_block(fig, f"{month} - {col} 趋势图"))
        else:
            html_parts.append("<p>该月无有效数据。</p>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


# ==============================================================================
# 纯计算 + 缓存：读 Excel + 清洗 + 指标计算 + HTML 报告生成
#   - 不做任何 st.xxx 调用（方便 @st.cache_data）
#   - 首次对每个文件执行一次；之后同一文件重复操作时直接复用结果
# ==============================================================================
@st.cache_data(show_spinner=False)
def analyze_file_cached(file_bytes: bytes, filename: str):
    """对单个上传文件进行完整分析，并返回：
       - 清洗/计算好的 DataFrame
       - 该文件的 HTML 报告字符串
    """
    # 0. 读 Excel 原始数据
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=1)

    # 1. 列名清洗与重命名
    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量": "曝光", "阅读量": "观看量", "播放量": "观看量", "观看数": "观看量",
        "点赞数": "点赞", "获赞": "点赞", "获赞数": "点赞", "点赞次数": "点赞",
        "收藏数": "收藏", "评论数": "评论", "涨粉数": "涨粉", "净涨粉": "涨粉",
        "发布形式": "体裁"
    }
    df.rename(columns=rename_map, inplace=True)
    required = ["笔记标题", "曝光", "观看量", "收藏", "点赞", "评论",
                "涨粉", "分享", "封面点击率", "首次发布时间", "体裁"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        # 抛出异常，外层用 st.error 展示，交互行为不变
        raise ValueError(f"文件缺少必要列：{missing}")

    # 2. 时间处理与排序
    df["首次发布时间"] = pd.to_datetime(
        df["首次发布时间"],
        format='%Y年%m月%d日%H时%M分%S秒',
        errors='coerce'
    )
    df = df.dropna(subset=["首次发布时间"]).copy()
    if df.empty:
        raise ValueError("无有效的“首次发布时间”数据。")

    df.sort_values(by="首次发布时间", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 3. 生成“年月”和“序号”（每月从 1 开始）
    df['年月'] = df['首次发布时间'].dt.to_period('M').astype(str)
    df.insert(df.columns.get_loc("年月") + 1, "月份", df['首次发布时间'].dt.month)
    df.insert(0, "序号", df.groupby("年月").cumcount() + 1)

    # 4. 数值转换
    for c in ["曝光", "封面点击率", "点赞", "观看量",
              "收藏", "评论", "涨粉", "分享"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)

    # 5. 衍生指标计算
    views = df["观看量"].replace(0, np.nan)
    expo = df["曝光"].replace(0, np.nan)

    df["点赞率"] = df["点赞"] / views
    df["收藏率"] = df["收藏"] / views
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, np.nan)
    df["评论率"] = df["评论"] / views
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / views
    df["有效活跃度"] = df["评论"] / (df["点赞"] + df["收藏"]).replace(0, np.nan)
    df["转粉率"] = df["涨粉"] / views

    # 6. 生成 HTML 报告（仅首次计算，之后从缓存取）
    html_str = build_html_report(df, filename)

    return df, html_str


# ==============================================================================
# 展示逻辑：用已经计算好的 df 和 HTML 字符串，在页面上绘制所有交互组件
#   这个函数每次 rerun 都会执行（保证交互不变），但用的是缓存好的数据
# ==============================================================================
def render_single_file(df: pd.DataFrame, filename: str, html_str: str):
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')

    st.markdown(
        f"**📅 数据时间范围：{df['首次发布时间'].min().date()} "
        f"至 {df['首次发布时间'].max().date()}**"
    )
    # =========================================================
    # 新增板块：数据总览
    # =========================================================
    st.subheader("📊 数据总览（曝光与观看）")
    
    # 总体指标计算
    total_expo = df["曝光"].sum()
    total_views = df["观看量"].sum()
    total_notes = len(df)
    avg_expo = total_expo / total_notes if total_notes > 0 else 0
    avg_views = total_views / total_notes if total_notes > 0 else 0

    # 总体呈现
    with st.expander("【总体指标】所有月份汇总", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总曝光", f"{total_expo:,.0f}")
        c2.metric("总观看量", f"{total_views:,.0f}")
        c3.metric("平均每篇曝光", f"{avg_expo:,.0f}")
        c4.metric("平均每篇观看", f"{avg_views:,.0f}")

    # 分月呈现
    with st.expander("📋 点击收起/展开：【分月指标】详细数据", expanded=False):
        for month in sorted(df['年月'].unique()):
            df_month = df[df['年月'] == month]
            m_count = len(df_month)
            m_total_expo = df_month["曝光"].sum()
            m_total_views = df_month["观看量"].sum()
            m_avg_expo = m_total_expo / m_count if m_count > 0 else 0
            m_avg_views = m_total_views / m_count if m_count > 0 else 0
            
            st.markdown(f"**🗓️ {month} 月表现 (共 {m_count} 篇)**")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric(f"总曝光", f"{m_total_expo:,.0f}")
            mc2.metric(f"总观看量", f"{m_total_views:,.0f}")
            mc3.metric(f"平均每篇曝光", f"{m_avg_expo:,.0f}")
            mc4.metric(f"平均每篇观看", f"{m_avg_views:,.0f}")
            st.markdown("---")
    # =========================================================
    # 1. 显示分析后的数据表
    st.subheader("分析后的数据表")
    show_cols = [
        "序号", "年月","月份", "笔记标题", "首次发布时间", "体裁",
        "曝光", "观看量", "封面点击率",
        "点赞", "评论", "收藏", "涨粉", "分享",
        "点赞率", "收藏率", "互动率", "转粉率", "赞藏比", "有效活跃度"
    ]
    st.dataframe(
        df[show_cols].style.format({
            "首次发布时间": "{:%Y-%m-%d %H:%M}",
            "封面点击率": "{:.2%}", "点赞率": "{:.2%}", "收藏率": "{:.2%}",
            "互动率": "{:.2%}", "转粉率": "{:.2%}", "赞藏比": "{:.2f}", "有效活跃度": "{:.2f}",
            "曝光": "{:.0f}", "观看量": "{:.0f}", "点赞": "{:.0f}",
            "评论": "{:.0f}", "收藏": "{:.0f}", "涨粉": "{:.0f}", "分享": "{:.0f}"
        }, na_rep="--")
    )

    # 2. 核心指标平均值（按月 + 全局）
    st.subheader("📈 核心指标平均值")

    with st.expander("📋 点击收起/展开：各月份详细平均指标数据", expanded=False):
        sorted_months = sorted(df['年月'].unique())
        for month in sorted_months:
            df_month = df[df['年月'] == month]

            m_total_views = df_month["观看量"].sum()
            m_total_expo = df_month["曝光"].sum()
            m_total_likes = df_month["点赞"].sum()
            m_total_favs = df_month["收藏"].sum()
            m_total_comments = df_month["评论"].sum()

            m_avg_ctr = (
                (df_month["封面点击率"] * df_month["曝光"]).sum() / m_total_expo
                if m_total_expo else 0
            )
            m_avg_like_rate = (m_total_likes / m_total_views) if m_total_views else 0
            m_avg_fav_rate = (m_total_favs / m_total_views) if m_total_views else 0
            m_avg_eng_rate = (
                (m_total_likes + m_total_comments + m_total_favs) / m_total_views
                if m_total_views else 0
            )
            
            # --- 新增：平均阅读率计算 ---
            m_avg_read_rate = m_total_views / m_total_expo if m_total_expo else 0

            st.markdown(f"**🗓️ {month} 月度表现 (共 {len(df_month)} 篇)**")
            # --- 修改：将4列改为5列，并添加阅读率展示 ---
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(f"{month} 平均阅读率", f"{m_avg_read_rate:.2%}")
            c2.metric(f"{month} 平均封面点击率", f"{m_avg_ctr:.2%}")
            c3.metric(f"{month} 平均点赞率", f"{m_avg_like_rate:.2%}")
            c4.metric(f"{month} 平均收藏率", f"{m_avg_fav_rate:.2%}")
            c5.metric(f"{month} 平均互动率", f"{m_avg_eng_rate:.2%}")
            st.markdown("---")

    with st.expander("【全局累计】平均指标（所有月份汇总）"):
        total_views = df["观看量"].sum()
        total_expo = df["曝光"].sum()
        total_likes = df["点赞"].sum()
        total_favs = df["收藏"].sum()
        total_comments = df["评论"].sum()

        g_avg_ctr = (
            (df["封面点击率"] * df["曝光"]).sum() / total_expo
            if total_expo else 0
        )
        g_avg_like_rate = (total_likes / total_views) if total_views else 0
        g_avg_fav_rate = (total_favs / total_views) if total_views else 0
        g_avg_eng_rate = (
            (total_likes + total_comments + total_favs) / total_views
            if total_views else 0
        )
        
        # --- 新增：全局平均阅读率计算 ---
        g_avg_read_rate = total_views / total_expo if total_expo else 0

        # --- 修改：将4列改为5列，并添加全局阅读率展示 ---
        gc1, gc2, gc3, gc4, gc5 = st.columns(5)
        gc1.metric("全局平均阅读率", f"{g_avg_read_rate:.2%}")
        gc2.metric("全局平均点击率", f"{g_avg_ctr:.2%}")
        gc3.metric("全局平均点赞率", f"{g_avg_like_rate:.2%}")
        gc4.metric("全局平均收藏率", f"{g_avg_fav_rate:.2%}")
        gc5.metric("全局平均互动率", f"{g_avg_eng_rate:.2%}")

    # 3. HTML 报告下载（不再写临时文件到硬盘，直接使用内存中的字符串）
    download_file_name = f"{os.path.splitext(filename)[0]}_可视化报告.html"
    st.success(f"✅ 已生成可视化报告文件：{download_file_name}")
    st.download_button(
        "下载该文件的可视化HTML报告",
        data=html_str.encode("utf-8"),
        file_name=download_file_name,
        mime="text/html"
    )


# ==============================================================================
# 主逻辑：文件上传、汇总下载、账号对比 & 环比分析
# ==============================================================================
st.title("📊 小红书数据分析平台")
st.markdown("上传一个或多个 Excel 文件，系统会分析并生成**独立可视化 HTML 报告**与汇总 Excel。")
st.info("💡 提示：如需进行【账号/月份横向对比】或【环比分析】，请确保不同文件代表不同账号，或者文件内包含不同月份的数据。")

uploaded_files = st.file_uploader(
    "请上传小红书后台导出的 Excel 文件",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    placeholder_top = st.empty()
    processed_dfs = {}
    all_data_list = []

    # === 每个文件只在首次上传时做一次重计算，之后都从缓存里取 ===
    for up_file in uploaded_files:
        try:
            file_bytes = up_file.getvalue()
            df_processed, html_str = analyze_file_cached(file_bytes, up_file.name)

            # 页面展示（数据表、指标卡、HTML 下载按钮等）
            render_single_file(df_processed, up_file.name, html_str)

            # 用于后续汇总导出
            account_name = os.path.splitext(up_file.name)[0]
            df_export = df_processed.copy()
            df_export.insert(0, "账号名", account_name)

            sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:31]
            if not sheet_name:
                sheet_name = f"Sheet_{len(processed_dfs) + 1}"

            processed_dfs[sheet_name] = df_export
            all_data_list.append(df_export)

        except Exception as e:
            st.error(f"处理文件 {up_file.name} 时发生错误: {e}")

    if processed_dfs:
        # ==============================================================================
        # 进阶功能：全景对比 & 环比分析
        # ==============================================================================
        st.markdown("---")
        st.header(" 账号/月份 核心指标趋势 & 环比分析", divider="orange")

        if all_data_list:
            df_all = pd.concat(all_data_list, ignore_index=True)

            # 确保汇总分析时也有年月
            if '年月' not in df_all.columns:
                df_all['年月'] = df_all['首次发布时间'].dt.to_period('M').astype(str)

            df_all['估算点击数'] = df_all['封面点击率'] * df_all['曝光']

            df_trend = df_all.groupby(['账号名', '年月']).agg({
                '曝光': 'sum', '观看量': 'sum', '点赞': 'sum',
                '收藏': 'sum', '评论': 'sum', '涨粉': 'sum',
                '估算点击数': 'sum'
            }).reset_index()

            df_trend['互动率'] = (
                (df_trend['点赞'] + df_trend['收藏'] + df_trend['评论'])
                / df_trend['观看量'].replace(0, np.nan)
            )
            df_trend['封面点击率'] = (
                df_trend['估算点击数'] / df_trend['曝光'].replace(0, np.nan)
            )
            
            # === 新增：计算阅读率、点赞率、收藏率 ===
            df_trend['阅读率'] = df_trend['观看量'] / df_trend['曝光'].replace(0, np.nan)
            df_trend['点赞率'] = df_trend['点赞'] / df_trend['观看量'].replace(0, np.nan)
            df_trend['收藏率'] = df_trend['收藏'] / df_trend['观看量'].replace(0, np.nan)

            df_trend.sort_values(by=['账号名', '年月'],
                                 ascending=[True, True], inplace=True)

            df_trend['涨粉环比'] = df_trend.groupby('账号名')['涨粉'].pct_change()
            df_trend['互动率环比'] = df_trend.groupby('账号名')['互动率'].pct_change()
            df_trend['点击率环比'] = df_trend.groupby('账号名')['封面点击率'].pct_change()
            df_trend.replace([np.inf, -np.inf], np.nan, inplace=True)

            all_accounts = df_trend['账号名'].unique()
            selected_accounts = st.multiselect(
                "👇 1. 请选择要对比趋势的账号：",
                all_accounts,
                default=all_accounts
            )

            if selected_accounts:
                df_chart = df_trend[df_trend['账号名'].isin(selected_accounts)].copy()
                df_chart.sort_values(by='年月', ascending=True, inplace=True)

                def plot_compare_metric(metric_name, title_text, is_percent=True):
                    fig, ax = plt.subplots(figsize=(14, 6))
                    for account in selected_accounts:
                        sub_data = df_chart[df_chart['账号名'] == account]
                        if not sub_data.empty:
                            x_vals = sub_data['年月']
                            y_vals = sub_data[metric_name]
                            ax.plot(x_vals, y_vals, marker='o', linewidth=2, label=account)
                            if len(sub_data) < 24:
                                for x, y in zip(x_vals, y_vals):
                                    if pd.notna(y):
                                        txt = f"{y:.1%}" if is_percent else f"{int(y)}"
                                        ax.text(
                                            x, y, txt,
                                            ha='center', va='bottom', fontsize=12,
                                            color='black',
                                            path_effects=[path_effects.withStroke(
                                                linewidth=2, foreground="white"
                                            )]
                                        )
                    ax.margins(y=0.5)
                    ax.set_title(title_text, fontsize=16)
                    ax.set_xlabel("月份", fontsize=14)
                    ax.set_ylabel("数值", fontsize=14)
                    ax.tick_params(axis='both', labelsize=12)
                    ax.legend(loc='best', fontsize=14)
                    ax.grid(True, linestyle='--', alpha=0.5)
                    if is_percent:
                        ax.yaxis.set_major_formatter(
                            FuncFormatter(lambda y, _: '{:.0%}'.format(y))
                        )
                    return fig

                # =========================================================
                # 绘制 6 个趋势对比图
                # =========================================================
                # 第一排：阅读率、封面点击率
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.subheader("阅读率 - 月度趋势")
                    st.pyplot(plot_compare_metric('阅读率', '账号阅读率月度走势', is_percent=True))

                with col_g2:
                    st.subheader("封面点击率 - 月度趋势")
                    st.pyplot(plot_compare_metric('封面点击率', '账号封面点击率月度走势', is_percent=True))

                # 第二排：点赞率、收藏率
                col_g3, col_g4 = st.columns(2)
                with col_g3:
                    st.subheader("点赞率 - 月度趋势")
                    st.pyplot(plot_compare_metric('点赞率', '账号点赞率月度走势', is_percent=True))

                with col_g4:
                    st.subheader("收藏率 - 月度趋势")
                    st.pyplot(plot_compare_metric('收藏率', '账号收藏率月度走势', is_percent=True))

                # 第三排：互动率、涨粉数
                col_g5, col_g6 = st.columns(2)
                with col_g5:
                    st.subheader("互动率 - 月度趋势")
                    st.pyplot(plot_compare_metric('互动率', '账号互动率月度走势', is_percent=True))

                with col_g6:
                    st.subheader("涨粉数 - 月度趋势")
                    st.pyplot(plot_compare_metric('涨粉', '账号月度净涨粉走势', is_percent=False))
                # =========================================================

                st.markdown("---")
                with st.expander(
                    "📋 点击展开：查看月度对比详细数据表（含环比增长率）",
                    expanded=True
                ):
                    display_cols = [
                        '账号名', '年月', '涨粉', '涨粉环比', '互动率', '互动率环比',
                        '封面点击率', '点击率环比', '曝光', '观看量'
                    ]
                    df_display = df_chart[display_cols].copy()
                    st.dataframe(
                        df_display.style.format({
                            '涨粉': '{:,.0f}',
                            '互动率': '{:.2%}',
                            '封面点击率': '{:.2%}',
                            '曝光': '{:,.0f}',
                            '观看量': '{:,.0f}',
                            '涨粉环比': '{:+.1%}',
                            '互动率环比': '{:+.1%}',
                            '点击率环比': '{:+.1%}'
                        }, na_rep="--").bar(
                            subset=['涨粉'], color='#d65f5f', vmin=0
                        ).background_gradient(
                            subset=['互动率'], cmap='Greens'
                        )
                    )
            else:
                st.warning("请至少选择一个账号查看趋势图。")

            st.markdown("---")
            st.subheader("📅 核心指标详细透视表 ")
            metric_configs = {
                "涨粉数": {"val_col": "涨粉", "mom_col": "涨粉环比", "fmt": "{:,.0f}"},
                "互动率": {"val_col": "互动率", "mom_col": "互动率环比", "fmt": "{:.2%}"},
                "封面点击率": {"val_col": "封面点击率", "mom_col": "点击率环比", "fmt": "{:.2%}"}
            }
            target_key = st.selectbox("👇 请选择要查看的指标：", list(metric_configs.keys()))
            cfg = metric_configs[target_key]

            if not df_trend.empty:
                pivot_df = df_trend.pivot(
                    index='账号名',
                    columns='年月',
                    values=[cfg['val_col'], cfg['mom_col']]
                )
                sorted_months = sorted(df_trend['年月'].unique())
                new_columns_order = (
                    [(cfg['val_col'], m) for m in sorted_months] +
                    [(cfg['mom_col'], m) for m in sorted_months]
                )
                try:
                    df_final = pivot_df.reindex(columns=new_columns_order)
                    new_col_names = []
                    format_dict = {}
                    for metric_type, month in df_final.columns:
                        if metric_type == cfg['val_col']:
                            new_name = f"{month}"
                            format_dict[new_name] = cfg['fmt']
                        else:
                            new_name = f"{month} 环比"
                            format_dict[new_name] = "{:+.1%}"
                        new_col_names.append(new_name)
                    df_final.columns = new_col_names
                    styler = df_final.style.format(format_dict, na_rep="--")
                    st.write(f"**📊 各账号 {target_key} 月度详细数据表：**")
                    st.dataframe(styler)
                except KeyError as e:
                    st.error(f"数据重排时出错。详细错误: {e}")
            else:
                st.warning("暂无数据可用于生成透视表。")



        # ==============================================================================
        # 汇总 Excel 下载（原生 OpenPyXL 格式化，确保 Excel 识别为真实数字而非文本）
        # ==============================================================================
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            
            # 定义需要加千位分隔符的整数列
            integer_cols_with_comma = ["曝光", "观看量", "点赞", "评论", "收藏", "涨粉", "分享", "人均观看时长", "弹幕"]

            def write_and_format_sheet(df_data, sheet_name):
                df_export = df_data.copy()
                
                # 确保月份列存在
                if '年月' in df_export.columns and '月份' not in df_export.columns:
                    df_export.insert(df_export.columns.get_loc('年月') + 1, '月份', df_export['年月'].str.split('-').str[-1].astype(int))
                
                # 将空值替换为 '--'，其余的保留为原生的数字类型
                df_export.fillna('--', inplace=True)
                
                # 写入原生数据（不转字符串），让 Excel 能识别为真实的数字
                df_export.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 获取该 sheet 对象，直接修改 Excel 底层单元格的数字格式（Number Format）
                worksheet = writer.sheets[sheet_name]
                
                for idx, col_name in enumerate(df_export.columns):
                    col_idx = idx + 1  # openpyxl 的列索引从 1 开始
                    
                    excel_fmt = None
                    # 判断当前列应当适用哪种 Excel 格式代码
                    if col_name in integer_cols_with_comma:
                        excel_fmt = '#,##0'                 # 千位分隔符，无小数
                    elif '环比' in str(col_name):
                        excel_fmt = '+0.0%;-0.0%;0.0%'      # 带正负号的百分比，一位小数
                    elif '率' in str(col_name):
                        excel_fmt = '0.00%'                 # 百分比，两位小数
                    elif pd.api.types.is_float_dtype(df_data[col_name]) and col_name not in ['序号', '月份']:
                        excel_fmt = '0.0'                   # 其他浮点数，一位小数

                    if excel_fmt:
                        # 从第二行开始遍历单元格（跳过第一行的表头）
                        for row in range(2, len(df_export) + 2):
                            cell = worksheet.cell(row=row, column=col_idx)
                            # 只有当单元格是原生数字类型时，才赋予格式（防止把 '--' 报错）
                            if isinstance(cell.value, (int, float)):
                                cell.number_format = excel_fmt

            # 1. 写入每个独立文件的sheet
            for name, d in processed_dfs.items():
                write_and_format_sheet(d, name)

            # 2. 写入“所有数据明细汇总”sheet
            if all_data_list:
                df_all_summary = pd.concat(all_data_list, ignore_index=True)
                write_and_format_sheet(df_all_summary, "所有数据明细汇总")

            # 3. 写入“月度统计(含环比)”sheet
            if 'df_trend' in locals() and not df_trend.empty:
                write_and_format_sheet(df_trend, "月度统计(含环比)")

        with placeholder_top.container():
            st.header("汇总Excel下载", divider="rainbow")
            st.download_button(
                "⬇️ 下载汇总Excel报告（含月度分析表）",
                data=excel_buffer.getvalue(),
                file_name="小红书分析汇总报告.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.balloons()
    else:
        st.error("没有文件被成功处理，无法生成汇总报告。请检查上方报错信息。")
else:
    st.info("👆 请上传Excel文件开始分析。")
