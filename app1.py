# app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm # 导入字体管理器
import io  # 用于在内存中创建文件
import os # 用于处理文件路径

# ==============================================================================
# 关键修正：将 st.set_page_config() 移到最前面
# 这是 Streamlit 的规则，它必须是第一个被调用的 Streamlit 命令。
# ==============================================================================
st.set_page_config(page_title="小红书数据批量分析平台", layout="wide")

# ==============================================================================
# 核心修改：从项目文件中加载中文字体 (这部分逻辑保持不变)
# ==============================================================================
# 定义字体文件的路径 (假设它和 app.py 在同一个目录下)
font_path = 'SourceHanSansSC-Regular.otf'

# 检查字体文件是否存在
if os.path.exists(font_path):
    # 使用字体管理器加载字体
    # 这会告诉matplotlib，我们有一个新的字体可以使用
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'sans-serif' # 必须先设置字体家族
    # 'Source Han Sans SC' 是思源黑体的内部名称，通过addfont后就可以识别
    plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'SimHei'] 
    plt.rcParams['axes.unicode_minus'] = False # 解决负号显示问题
    st.sidebar.info("中文字体加载成功！")
else:
    # 如果在云端或本地找不到字体文件，给出明确的提示
    st.sidebar.warning(
        f"未找到字体文件 '{font_path}'。请确保已将字体文件上传到项目根目录。\n"
        "图表中的中文可能显示为方块。"
    )
    plt.rcParams['axes.unicode_minus'] = False # 即使字体失败，也尝试解决负号问题

# ==============================================================================
# 您原来的代码保持不变
# ==============================================================================

# ==============================================================================
# 将核心分析逻辑封装成一个函数，方便对每个文件重复调用
# ==============================================================================
def analyze_and_display(df, filename):
    """对单个DataFrame进行分析和可视化"""
    
    st.header(f"--- 分析报告：【{filename}】 ---", divider='rainbow')

    # ---------- 2️⃣ 列名规范与检查 ----------
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "曝光量": "曝光", "阅读量": "观看量", "播放量": "观看量", "观看数": "观看量",
        "点赞数": "点赞", "获赞": "点赞", "获赞数": "点赞", "点赞次数": "点赞",
        "收藏数": "收藏", "评论数": "评论", "涨粉数": "涨粉", "净涨粉": "涨粉",
        "发布形式": "体裁"
    }
    df.rename(columns=rename_map, inplace=True)

    required_cols = ["笔记标题", "曝光", "点赞", "观看量", "收藏", "评论", "涨粉", "分享", "封面点击率", "首次发布时间", "体裁"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"文件 '{filename}' 缺少必要列：{missing}，已跳过此文件。")
        return None  # 返回None表示处理失败

    # ---------- 3️⃣ 日期解析与排序 ----------
    df["首次发布时间"] = pd.to_datetime(df["首次发布时间"], format='%Y年%m月%d日%H时%M分%S秒', errors='coerce')
    df.dropna(subset=["首次发布时间"], inplace=True)
    df.sort_values(by="首次发布时间", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "序号", df.index + 1)
    
    min_date = df["首次发布时间"].min()
    max_date = df["首次发布时间"].max()
    st.markdown(f"**📅 数据时间范围：{min_date.date()} 至 {max_date.date()}**")

    # ---------- 4️⃣ 指标计算 ----------
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

    # ---------- 5️⃣ 数据表 ----------
    st.subheader("📄 计算结果完整数据表")
    display_cols = [
        "序号", "笔记标题", "首次发布时间", "体裁", "曝光", "观看量", "封面点击率", 
        "点赞", "评论", "收藏", "涨粉", "分享",
        "点赞率", "收藏率", "互动率", "转粉率", "赞藏比", "有效活跃度"
    ]
    st.dataframe(df[display_cols].style.format({
        "首次发布时间": "{:%Y-%m-%d %H:%M}", "封面点击率": "{:.2%}", "点赞率": "{:.2%}",
        "收藏率": "{:.2%}", "互动率": "{:.2%}", "转粉率": "{:.2%}", "赞藏比": "{:.2f}",
        "有效活跃度": "{:.2f}"
    }))

    # ---------- 6️⃣ 平均值 ----------
    st.subheader("📈 核心指标平均值")
    avg = df[["封面点击率", "点赞率", "收藏率", "互动率", "转粉率"]].mean()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均封面点击率", f"{avg['封面点击率']:.2%}")
    c2.metric("平均点赞率", f"{avg['点赞率']:.2%}")
    c3.metric("平均收藏率", f"{avg['收藏率']:.2%}")
    c4.metric("平均互动率", f"{avg['互动率']:.2%}")

    # ---------- 7️⃣ 可视化 ----------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎨 内容形式分布")
        fig_pie, ax_pie = plt.subplots()
        pie_data = df["体裁"].value_counts()
        ax_pie.pie(
            pie_data, autopct="%1.1f%%", startangle=90,
            colors=["#ff9999", "#66b3ff"], textprops={'color':"w"}
        )
        ax_pie.set_ylabel('')
        ax_pie.set_title("图文 vs 视频比例", color='w')
        fig_pie.set_facecolor('#0E1117')
        ax_pie.legend(labels=pie_data.index, loc="upper right")
        st.pyplot(fig_pie)
    
    # 辅助函数移动到 col2 外面，避免重复定义
    def plot_with_labels(ax, title, cols, df):
        for col in cols:
            ax.plot(df["序号"], df[col], marker="o", linestyle="-", label=col)
            for x, y in zip(df["序号"], df[col]):
                if pd.notna(y):
                    if '%' in col or '率' in col: label = f"{y:.1%}"
                    elif y < 1 and y > 0: label = f"{y:.2f}"
                    else: label = f"{int(y)}"
                    ax.text(x, y, label, ha="center", va="bottom", fontsize=7, color='grey')
        ax.set_xlabel("笔记序号")
        ax.set_ylabel("数值")
        ax.set_title(title)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)

    # 原始的组合图表
    st.subheader("📈 各篇笔记指标表现")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    plot_with_labels(ax1, "核心互动指标趋势", ["点赞率", "收藏率", "互动率"], df)
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots(figsize=(12, 5))
    plot_with_labels(ax2, "基础数据表现", ["曝光", "观看量", "点赞", "收藏", "分享"], df)
    st.pyplot(fig2)

    # ==============================================================================
    # 【新增部分】为每个指标单独生成图表
    # ==============================================================================
    st.markdown("---") # 添加分割线
    st.subheader("📊 单项指标详细趋势")
    st.markdown("下方为各篇笔记的单项指标表现，方便您进行深入分析。")

    # 定义需要单独可视化的指标列表
    individual_metrics = [
        "点赞率", "收藏率", "评论率", "互动率", 
        "转粉率", "赞藏比", "有效活跃度"
    ]

    # 创建两列布局来放置图表
    viz_col1, viz_col2 = st.columns(2)

    # 循环遍历每个指标，并将其绘制在对应的列中
    for i, metric in enumerate(individual_metrics):
        # 为每个图表创建一个新的Figure和Axes对象
        fig_ind, ax_ind = plt.subplots(figsize=(10, 4)) # 调整尺寸以适应列宽
        
        # 使用现有的辅助函数绘图，标题动态生成
        plot_with_labels(ax_ind, f"{metric} 趋势", [metric], df)
        
        # 交替在左右两列显示图表
        if i % 2 == 0:
            with viz_col1:
                st.pyplot(fig_ind)
        else:
            with viz_col2:
                st.pyplot(fig_ind)
    
    return df # 返回处理好的df，用于后续汇总

# ==============================================================================
# 主应用逻辑 (这部分逻辑在 st.set_page_config() 之后)
# ==============================================================================
st.title("📊 小红书数据批量分析与报告生成")
st.markdown("您可以上传**一个或多个**Excel文件，系统将逐一分析并在下方展示结果，最后提供一个汇总的Excel报告供您下载。")

# --- 核心修改1：允许多文件上传 ---
uploaded_files = st.file_uploader(
    "请上传小红书后台导出的 Excel 文件", 
    type=["xls", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    processed_dfs = {} # 用于存储所有处理好的DataFrame

    # --- 核心修改2：循环处理每个文件 ---
    for uploaded_file in uploaded_files:
        try:
            # 读取文件
            df_raw = pd.read_excel(uploaded_file, header=1)
            # 调用分析函数
            df_processed = analyze_and_display(df_raw, uploaded_file.name)
            
            # 如果分析成功，则存入字典，用于最后汇总下载
            if df_processed is not None:
                # 清理文件名作为Sheet名，避免特殊字符和过长
                sheet_name = ''.join(e for e in uploaded_file.name if e.isalnum())[:31]
                processed_dfs[sheet_name] = df_processed

        except Exception as e:
            st.error(f"处理文件 {uploaded_file.name} 时发生严重错误: {e}")

    # --- 核心修改3：提供汇总下载按钮 ---
    if processed_dfs:
        st.header("--- 报告下载 ---", divider='rainbow')
        st.success("所有文件分析完成！您可以下载包含所有详细数据的汇总Excel报告。")
        
        # 创建一个内存中的Excel文件
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            for sheet_name, df_to_write in processed_dfs.items():
                df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 提供下载按钮
        st.download_button(
            label="📥 下载汇总Excel报告",
            data=output_buffer.getvalue(),
            file_name="小红书分析汇总报告.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.balloons()
else:
    st.info("👆 请上传一个或多个Excel文件开始分析。")
