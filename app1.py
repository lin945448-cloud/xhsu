import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm
import io
import os

# ==============================================================================
# 必须在最前面调用 set_page_config
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

# ==============================================================================
# 加载中文字体
# ==============================================================================
font_path = 'SourceHanSansSC-Regular.otf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    st.sidebar.info("中文字体加载成功！")
else:
    st.sidebar.warning(
        f"未找到字体文件 '{font_path}'。请确保已上传到项目根目录。\n"
        "图表中的中文可能显示为方块。"
    )
    plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# 分析函数
# ==============================================================================
def analyze_and_display(df, filename):
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')

    # ---------- 列名规范 ----------
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量": "曝光", "阅读量": "观看量", "播放量": "观看量", "观看数": "观看量",
        "点赞数": "点赞", "获赞": "点赞", "获赞数": "点赞", "点赞次数": "点赞",
        "收藏数": "收藏", "评论数": "评论", "涨粉数": "涨粉", "净涨粉": "涨粉",
        "发布形式": "体裁"
    }
    df.rename(columns=rename_map, inplace=True)

    required_cols = ["笔记标题", "曝光", "点赞", "观看量", "收藏", "评论",
                     "涨粉", "分享", "封面点击率", "首次发布时间", "体裁"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"文件 '{filename}' 缺少必要列：{missing}，已跳过此文件。")
        return None

    # ---------- 日期解析 ----------
    df["首次发布时间"] = pd.to_datetime(
        df["首次发布时间"], format='%Y年%m月%d日%H时%M分%S秒', errors='coerce'
    )
    df.dropna(subset=["首次发布时间"], inplace=True)
    df.sort_values(by="首次发布时间", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "序号", df.index + 1)
    min_date = df["首次发布时间"].min()
    max_date = df["首次发布时间"].max()
    st.markdown(f"**📅 数据时间范围：{min_date.date()} 至 {max_date.date()}**")

    # ---------- 指标计算 ----------
    numeric_cols = ["曝光", "封面点击率", "点赞", "观看量", "收藏", "评论", "涨粉", "分享"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["点赞率"] = df["点赞"] / df["观看量"].replace(0, pd.NA)
    df["收藏率"] = df["收藏"] / df["观看量"].replace(0, pd.NA)
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, pd.NA)
    df["评论率"] = df["评论"] / df["观看量"].replace(0, pd.NA)
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / df["观看量"].replace(0, pd.NA)
    df["有效活跃度"] = df["评论"] / (df["点赞"] + df["收藏"]).replace(0, pd.NA)
    df["转粉率"] = df["涨粉"] / df["观看量"].replace(0, pd.NA)

    # ---------- 数据表 ----------
    st.subheader("📄 计算结果完整数据表")
    display_cols = [
        "序号", "笔记标题", "首次发布时间", "体裁", "曝光", "观看量",
        "封面点击率", "点赞", "评论", "收藏", "涨粉", "分享",
        "点赞率", "收藏率", "互动率", "转粉率", "赞藏比", "有效活跃度"
    ]
    st.dataframe(df[display_cols].style.format({
        "首次发布时间": "{:%Y-%m-%d %H:%M}", "封面点击率": "{:.2%}",
        "点赞率": "{:.2%}", "收藏率": "{:.2%}", "互动率": "{:.2%}", "转粉率": "{:.2%}",
        "赞藏比": "{:.2f}", "有效活跃度": "{:.2f}"
    }))

    # ---------- 平均值 ----------
    st.subheader("📈 核心指标平均值")
    avg = df[["封面点击率", "点赞率", "收藏率", "互动率", "转粉率"]].mean()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均封面点击率", f"{avg['封面点击率']:.2%}")
    c2.metric("平均点赞率", f"{avg['点赞率']:.2%}")
    c3.metric("平均收藏率", f"{avg['收藏率']:.2%}")
    c4.metric("平均互动率", f"{avg['互动率']:.2%}")

    # ---------- 可视化 ----------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎨 内容形式分布")
        fig_pie, ax_pie = plt.subplots()
        pie_data = df["体裁"].value_counts()
        ax_pie.pie(pie_data, autopct="%1.1f%%", startangle=90,
                   colors=["#ff9999", "#66b3ff"], textprops={'color': "w"})
        ax_pie.set_ylabel('')
        ax_pie.set_title("图文 vs 视频比例", color='w')
        fig_pie.set_facecolor('#0E1117')
        ax_pie.legend(labels=pie_data.index, loc="upper right")
        st.pyplot(fig_pie)

    # 折线图辅助函数
    def plot_with_labels(ax, title, cols, df):
        for col in cols:
            ax.plot(df["序号"], df[col], marker="o", linestyle="-", label=col)
            for x, y in zip(df["序号"], df[col]):
                if pd.notna(y):
                    if '%' in col or '率' in col:
                        label = f"{y:.1%}"
                    elif y < 1 and y > 0:
                        label = f"{y:.2f}"
                    else:
                        label = f"{int(y)}"
                    ax.text(x, y + y*0.05 if y != 0 else 0.05, label,
                            ha="center", va="bottom", fontsize=7, color='grey')
        ax.margins(y=0.4)
        ax.set_xlabel("笔记序号")
        ax.set_ylabel("数值")
        ax.set_title(title)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)

    st.subheader("📈 各篇笔记指标表现")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    plot_with_labels(ax1, "核心互动指标趋势",
                     ["点赞率", "收藏率", "互动率"], df)
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots(figsize=(12, 5))
    plot_with_labels(ax2, "基础数据表现",
                     ["曝光", "观看量", "点赞", "收藏", "分享"], df)
    st.pyplot(fig2)

    # ====================================================
    # 🌟 每个指标单独图，留白空间+特定格式
    # ====================================================
    st.subheader("📊 各单项指标趋势图")
    indicator_cols = ["点赞率", "收藏率", "赞藏比", "评论率", "互动率", "有效活跃度", "转粉率"]
    for col in indicator_cols:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["序号"], df[col], color="#66b3ff", marker="o", linestyle="-")

        for x, y in zip(df["序号"], df[col]):
            if pd.notna(y):
                # 针对特定指标使用不同格式
                if col in ["赞藏比", "有效活跃度"]:
                    label = f"{y:.2f}"
                elif '率' in col:
                    label = f"{y:.1%}"
                elif y < 1 and y > 0:
                    label = f"{y:.2f}"
                else:
                    label = f"{int(y)}"
                # 垂直偏移 + 大号字体
                offset = (abs(y) * 0.1 if y != 0 else 0.05)
                ax.text(x, y + offset, label,
                        ha="center", va="bottom", fontsize=9, color='grey')

        # 增加边距避免标题遮挡
        ax.margins(y=0.4)
        ax.set_title(f"{col} 趋势图")
        ax.set_xlabel("笔记序号")
        ax.set_ylabel(col)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(True, linestyle="--", alpha=0.6)
        st.pyplot(fig)

    return df

# ==============================================================================
# 主逻辑
# ==============================================================================
st.title("📊 小红书数据批量分析与报告生成")
st.markdown("您可以上传**一个或多个**Excel文件，系统将逐一分析并展示结果，并提供汇总报告。")

uploaded_files = st.file_uploader(
    "请上传小红书后台导出的 Excel 文件",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    processed_dfs = {}

    for uploaded_file in uploaded_files:
        try:
            df_raw = pd.read_excel(uploaded_file, header=1)
            df_processed = analyze_and_display(df_raw, uploaded_file.name)
            if df_processed is not None:
                sheet_name = ''.join(e for e in uploaded_file.name if e.isalnum())[:31]
                processed_dfs[sheet_name] = df_processed
        except Exception as e:
            st.error(f"处理文件 {uploaded_file.name} 时发生严重错误: {e}")

    if processed_dfs:
        st.header("--- 报告下载 ---", divider='rainbow')
        st.success("所有文件分析完成！可下载汇总Excel报告。")
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            for sheet_name, df_to_write in processed_dfs.items():
                df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
        st.download_button(
            label="📥 下载汇总Excel报告",
            data=output_buffer.getvalue(),
            file_name="小红书分析汇总报告.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.balloons()
else:
    st.info("👆 请上传一个或多个Excel文件开始分析。")

