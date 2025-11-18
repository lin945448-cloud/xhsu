import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm
import io, os, base64

# ==============================================================================
# 初始化页面
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

# ==============================================================================
# 中文字体加载
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
# 基础绘图函数：带标注的线图
# ==============================================================================
def plot_lines(ax, title, cols, df):
    """通用绘线函数，用于保存为HTML时复用"""
    for col in cols:
        ax.plot(df["序号"], df[col], marker="o", linestyle="-", label=col)
        for x, y in zip(df["序号"], df[col]):
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
                ax.text(x, y + offset, label, ha="center", va="bottom", fontsize=8, color='grey')
    ax.margins(y=0.4)
    ax.set_xlabel("笔记序号")
    ax.set_ylabel("数值")
    ax.set_title(title)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)

# ==============================================================================
# 分析函数
# ==============================================================================
def analyze_and_display(df, filename):
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')

    # ---- 列名规范化 ----
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量":"曝光","阅读量":"观看量","播放量":"观看量","观看数":"观看量",
        "点赞数":"点赞","获赞":"点赞","获赞数":"点赞","点赞次数":"点赞",
        "收藏数":"收藏","评论数":"评论","涨粉数":"涨粉","净涨粉":"涨粉",
        "发布形式":"体裁"
    }
    df.rename(columns=rename_map, inplace=True)
    required = ["笔记标题","曝光","点赞","观看量","收藏","评论","涨粉","分享","封面点击率","首次发布时间","体裁"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"文件缺少必要列：{missing}")
        return None

    # ---- 日期处理 ----
    df["首次发布时间"] = pd.to_datetime(df["首次发布时间"], format='%Y年%m月%d日%H时%M分%S秒', errors='coerce')
    df.dropna(subset=["首次发布时间"], inplace=True)
    df.sort_values(by="首次发布时间", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "序号", df.index + 1)
    st.markdown(f"**📅 数据时间范围：{df['首次发布时间'].min().date()} 至 {df['首次发布时间'].max().date()}**")

    # ---- 指标计算 ----
    for c in ["曝光","封面点击率","点赞","观看量","收藏","评论","涨粉","分享"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["点赞率"] = df["点赞"] / df["观看量"].replace(0, pd.NA)
    df["收藏率"] = df["收藏"] / df["观看量"].replace(0, pd.NA)
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, pd.NA)
    df["评论率"] = df["评论"] / df["观看量"].replace(0, pd.NA)
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / df["观看量"].replace(0, pd.NA)
    df["有效活跃度"] = df["评论"] / (df["点赞"] + df["收藏"]).replace(0, pd.NA)
    df["转粉率"] = df["涨粉"] / df["观看量"].replace(0, pd.NA)

    # ---- 表格展示 ----
    st.subheader("📄 完整数据表")
    show_cols = [
        "序号","笔记标题","首次发布时间","体裁","曝光","观看量","封面点击率",
        "点赞","评论","收藏","涨粉","分享",
        "点赞率","收藏率","互动率","转粉率","赞藏比","有效活跃度"
    ]
    st.dataframe(df[show_cols].style.format({
        "首次发布时间":"{:%Y-%m-%d %H:%M}",
        "封面点击率":"{:.2%}","点赞率":"{:.2%}","收藏率":"{:.2%}",
        "互动率":"{:.2%}","转粉率":"{:.2%}","赞藏比":"{:.2f}","有效活跃度":"{:.2f}"
    }))

    # ---- 平均指标 ----
    st.subheader("📈 核心指标平均值")
    # 加权/总量法：用总量求转化率
    total_views = df["观看量"].sum()
    total_expo = df["曝光"].sum()
    total_likes = df["点赞"].sum()
    total_favs = df["收藏"].sum()
    total_comments = df["评论"].sum()
    total_follows = df["涨粉"].sum()

    avg_ctr = ((df["封面点击率"] * df["曝光"]).sum() / total_expo) if total_expo else float("nan")
    avg_like_rate = (total_likes / total_views) if total_views else float("nan")
    avg_fav_rate = (total_favs / total_views) if total_views else float("nan")
    avg_eng_rate = ((total_likes + total_comments + total_favs) / total_views) if total_views else float("nan")
    avg_follow_rate = (total_follows / total_views) if total_views else float("nan")  # 未展示，但保持一致性计算

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("平均封面点击率", f"{avg_ctr:.2%}")
    c2.metric("平均点赞率", f"{avg_like_rate:.2%}")
    c3.metric("平均收藏率", f"{avg_fav_rate:.2%}")
    c4.metric("平均互动率", f"{avg_eng_rate:.2%}")

    # ==============================================================================
    # 🎨 生成所有可视化并输出为独立HTML报告
    # ==============================================================================
    html_dir = "html_reports"
    os.makedirs(html_dir, exist_ok=True)
    html_path = os.path.join(html_dir, f"{os.path.splitext(filename)[0]}_可视化报告.html")

    def save_fig_to_html(fig, caption, parts):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        parts.append(f"<h3>{caption}</h3><img src='data:image/png;base64,{b64}' style='max-width:100%;'><hr>")

    html_parts = [
        f"<html><head><meta charset='utf-8'><title>{filename} 可视化报告</title></head><body>",
        f"<h2>{filename} 可视化报告</h2>"
    ]

    # -- 饼图 --
    fig_pie, ax_pie = plt.subplots(figsize=(6,6))
    pie_data = df["体裁"].value_counts()
    ax_pie.pie(pie_data, autopct="%1.1f%%", startangle=90, colors=["#ff9999","#66b3ff"])
    ax_pie.set_title("图文 vs 视频比例")
    save_fig_to_html(fig_pie, "图文 vs 视频比例", html_parts)

    # -- 核心互动 & 基础表现 --
    fig1, ax1 = plt.subplots(figsize=(12,5))
    plot_lines(ax1, "核心互动指标趋势", ["点赞率","收藏率","互动率"], df)
    save_fig_to_html(fig1, "核心互动指标趋势", html_parts)

    fig2, ax2 = plt.subplots(figsize=(12,5))
    plot_lines(ax2, "基础数据表现", ["曝光","观看量","点赞","收藏","分享"], df)
    save_fig_to_html(fig2, "基础数据表现", html_parts)

    # -- 各单项指标 --
    for col in ["点赞率","收藏率","赞藏比","评论率","互动率","有效活跃度","转粉率"]:
        fig, ax = plt.subplots(figsize=(12,4))
        plot_lines(ax, f"{col} 趋势图", [col], df)
        save_fig_to_html(fig, f"{col} 趋势图", html_parts)

    html_parts.append("</body></html>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    # ---- 下载HTML报告按钮 ----
    st.success(f"✅ 已生成可视化报告文件：{os.path.basename(html_path)}")
    with open(html_path, "rb") as f:
        st.download_button("下载该文件的可视化HTML报告",
                           data=f.read(),
                           file_name=os.path.basename(html_path),
                           mime="text/html")
    return df

# ==============================================================================
# 主逻辑：文件上传、汇总下载
# ==============================================================================
st.title("📊 小红书数据批量分析平台")
st.markdown("上传一个或多个 Excel 文件，系统会分析并生成**独立可视化 HTML 报告**与汇总 Excel。")

uploaded_files = st.file_uploader("请上传小红书后台导出的 Excel 文件",
    type=["xls","xlsx"], accept_multiple_files=True)

if uploaded_files:
    placeholder_top = st.empty()  # 顶部留位放下载汇总按钮
    processed_dfs = {}

    for up_file in uploaded_files:
        try:
            df_raw = pd.read_excel(up_file, header=1)
            df_processed = analyze_and_display(df_raw, up_file.name)
            if df_processed is not None:
                sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:31]
                processed_dfs[sheet_name] = df_processed
        except Exception as e:
            st.error(f"处理文件 {up_file.name} 时发生错误: {e}")

    # 汇总Excel按钮在顶部
    if processed_dfs:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            for name, d in processed_dfs.items():
                d.to_excel(writer, sheet_name=name, index=False)
        with placeholder_top.container():
            st.header("汇总Excel下载", divider="rainbow")
            st.download_button("⬇️ 下载汇总Excel报告",
                               data=excel_buffer.getvalue(),
                               file_name="小红书分析汇总报告.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.balloons()
else:
    st.info("👆 请上传Excel文件以开始分析。")
