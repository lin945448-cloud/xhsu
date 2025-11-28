import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, MultipleLocator, FuncFormatter
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from adjustText import adjust_text
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
                ax.text(
                    x, y + offset, label,
                    ha="center", va="bottom",
                    fontsize=12, color='black',
                    path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
                )

    ax.margins(y=0.4)
    ax.set_xlabel("笔记序号")
    ax.set_ylabel("数值")
    ax.set_title(title)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.6)


# ==============================================================================
# 核心互动指标趋势函数
# ==============================================================================
def plot_core_interaction(df):
    fig, ax = plt.subplots(figsize=(12, 12))
    cols = ["点赞率", "收藏率", "互动率"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    texts = []
    line_data = {}

    # --- 先绘制三条线并收集数据 ---
    for col, color in zip(cols, colors):
        y_vals = df[col].values
        ax.plot(df["序号"], y_vals, marker="o", linestyle="-", color=color, label=col)
        line_data[col] = y_vals

    # --- 判断哪条是最下面的线（平均值最低） ---
    avg_values = {col: pd.Series(vals).mean(skipna=True) for col, vals in line_data.items()}
    bottom_line = min(avg_values, key=avg_values.get)  # 找出平均值最低的折线名

    # --- 绘制标注，最下面的在下方标注，其余在线上方 ---
    for col, color in zip(cols, colors):
        for x, y in zip(df["序号"], df[col]):
            if pd.notna(y):
                label = f"{y:.1%}"
                if col == bottom_line:
                    offset = -0.06  # 下方标注
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

    # 自动避让标注
    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", lw=0.4, color='gray'))

    # 设置纵坐标步长为 0.1
    ax.yaxis.set_major_locator(MultipleLocator(0.1))

    ax.margins(y=0.3)
    ax.set_xlabel("笔记序号")
    ax.set_ylabel("数值")
    ax.set_title("核心互动指标趋势")
    ax.legend(title=f"最下面的线：{bottom_line}", title_fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    return fig, ax


# ==============================================================================
# 分析与显示逻辑
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
    required = ["笔记标题","曝光","观看量","收藏","点赞","评论","涨粉","分享","封面点击率","首次发布时间","体裁"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"文件缺少必要列：{missing}")
        return None
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
    st.subheader("分析后的数据表")
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
    avg_follow_rate = (total_follows / total_views) if total_views else float("nan")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("平均封面点击率", f"{avg_ctr:.2%}")
    c2.metric("平均点赞率", f"{avg_like_rate:.2%}")
    c3.metric("平均收藏率", f"{avg_fav_rate:.2%}")
    c4.metric("平均互动率", f"{avg_eng_rate:.2%}")

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

    fig_pie, ax_pie = plt.subplots(figsize=(6,6))
    pie_data = df["体裁"].value_counts()
    ax_pie.pie(pie_data, autopct="%1.1f%%", startangle=90, colors=["#ff9999","#66b3ff"])
    ax_pie.set_title("图文 vs 视频比例")
    save_fig_to_html(fig_pie, "图文 vs 视频比例", html_parts)

    fig1, ax1 = plot_core_interaction(df)
    save_fig_to_html(fig1, "核心互动指标趋势", html_parts)

    for col in ["点赞率","收藏率","赞藏比","评论率","互动率","有效活跃度","转粉率"]:
        fig, ax = plt.subplots(figsize=(12,4))
        plot_lines(ax, f"{col} 趋势图", [col], df)
        save_fig_to_html(fig, f"{col} 趋势图", html_parts)

    html_parts.append("</body></html>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

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
st.title("📊 小红书数据分析平台")
st.markdown("上传一个或多个 Excel 文件，系统会分析并生成**独立可视化 HTML 报告**与汇总 Excel。")
st.info("💡 提示：如需进行【账号/月份横向对比】，请确保不同文件代表不同账号，或者文件内包含不同月份的数据。")

uploaded_files = st.file_uploader("请上传小红书后台导出的 Excel 文件",
    type=["xls","xlsx"], accept_multiple_files=True)

if uploaded_files:
    placeholder_top = st.empty()
    processed_dfs = {}
    all_data_list = []

    for up_file in uploaded_files:
        try:
            df_raw = pd.read_excel(up_file, header=1)
            # 分析并显示（返回的 df 尚未添加账号名，保持原逻辑不变）
            df_processed = analyze_and_display(df_raw, up_file.name)
            
            if df_processed is not None:
                # 获取账号名（去除后缀）
                account_name = os.path.splitext(up_file.name)[0]
                
                # 创建用于导出的副本，并在第一列插入“账号名”
                df_export = df_processed.copy()
                df_export.insert(0, "账号名", account_name)
                
                # 存储用于单独Sheet的数据
                sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:31]
                processed_dfs[sheet_name] = df_export
                
                # 存储用于汇总Sheet的数据
                all_data_list.append(df_export)

        except Exception as e:
            st.error(f"处理文件 {up_file.name} 时发生错误: {e}")

    if processed_dfs:
        # ==============================================================================
        # 🔥🔥 新增功能：账号/月份 横向对比分析模块 🔥🔥
        # ==============================================================================
        st.markdown("---")
        st.header("🏆 账号/月份 核心指标趋势对比", divider="orange")
        
        if all_data_list:
            # 1. 数据合并与清洗
            df_all = pd.concat(all_data_list, ignore_index=True)
            
            # 提取“年月”（格式：YYYY-MM），方便按月对比
            df_all['年月'] = df_all['首次发布时间'].dt.to_period('M').astype(str)
            
            # 估算点击数（用于加权计算）：因为点击率是百分比，这里反推点击次数
            # 逻辑：点击数 = 封面点击率 * 曝光
            df_all['估算点击数'] = df_all['封面点击率'] * df_all['曝光']

            # 2. 按“账号名”和“年月”进行分组聚合（加权计算）
            df_trend = df_all.groupby(['账号名', '年月']).agg({
                '曝光': 'sum',
                '观看量': 'sum',
                '点赞': 'sum',
                '收藏': 'sum',
                '评论': 'sum',
                '估算点击数': 'sum'
            }).reset_index()

            # 3. 重新计算核心比率（加权后的真实月度数据）
            # 互动率 = (赞+藏+评) / 观看
            df_trend['互动率'] = (df_trend['点赞'] + df_trend['收藏'] + df_trend['评论']) / df_trend['观看量'].replace(0, pd.NA)
            # 封面点击率 = 总点击 / 总曝光
            df_trend['封面点击率'] = df_trend['估算点击数'] / df_trend['曝光'].replace(0, pd.NA)

            # 4. 用户交互：选择要分析的账号
            all_accounts = df_trend['账号名'].unique()
            # 默认全选，如果账号太多可以改成 default=all_accounts[:3]
            selected_accounts = st.multiselect("👇 请选择要对比的账号（选择单个账号即可查看该账号的月度走势）：", 
                                               all_accounts, default=all_accounts)

            if selected_accounts:
                df_chart = df_trend[df_trend['账号名'].isin(selected_accounts)].copy()
                df_chart.sort_values(by='年月', inplace=True)

                # 绘图通用函数
                def plot_compare_metric(metric_name, title_text):
                    fig, ax = plt.subplots(figsize=(14, 6))
                    
                    # 为每个选中的账号画一条线
                    for account in selected_accounts:
                        sub_data = df_chart[df_chart['账号名'] == account]
                        if not sub_data.empty:
                            ax.plot(sub_data['年月'], sub_data[metric_name], marker='o', linewidth=2, label=account)
                            
                            # 只有当数据点少于20个时才显示具体数值，避免重叠太乱
                            if len(sub_data) < 20:
                                for x, y in zip(sub_data['年月'], sub_data[metric_name]):
                                    if pd.notna(y):
                                        ax.text(x, y, f"{y:.1%}", ha='center', va='bottom', fontsize=12, 
                                                color='black', path_effects=[path_effects.withStroke(linewidth=2, foreground="white")])

                    ax.set_title(title_text, fontsize=20)
                    ax.set_xlabel("月份", fontsize=16)
                    ax.set_ylabel("百分比", fontsize=16)
                    ax.legend(loc='best')
                    ax.grid(True, linestyle='--', alpha=0.5)
                    # Y轴显示百分比格式
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
                    return fig

                # 展示图表
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.subheader("互动率 - 月度趋势")
                    st.pyplot(plot_compare_metric('互动率', '账号互动率月度对比'))
                
                with col_g2:
                    st.subheader("封面点击率 - 月度趋势")
                    st.pyplot(plot_compare_metric('封面点击率', '账号封面点击率月度对比'))
                
                # 展示聚合后的数据表（方便老板复制）
                with st.expander("查看月度对比详细数据表"):
                    st.dataframe(df_trend[df_trend['账号名'].isin(selected_accounts)].style.format({
                        '互动率': '{:.2%}',
                        '封面点击率': '{:.2%}',
                        '曝光': '{:,.0f}',
                        '观看量': '{:,.0f}'
                    }))
            else:
                st.warning("请至少选择一个账号进行分析。")

        # ==============================================================================
        # Excel 导出逻辑（包含新增的月度统计表）
        # ==============================================================================
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            
            # 1. 写入各个独立的Sheet
            for name, d in processed_dfs.items():
                d.to_excel(writer, sheet_name=name, index=False)
            
            # 2. 写入汇总的大Sheet
            if all_data_list:
                df_summary = pd.concat(all_data_list, ignore_index=True)
                df_summary.to_excel(writer, sheet_name="所有数据明细汇总", index=False)
            
            # 3. 写入老板需要的月度统计表 (如果已计算)
            if 'df_trend' in locals():
                df_trend.to_excel(writer, sheet_name="月度核心指标统计", index=False)

        with placeholder_top.container():
            st.header("汇总Excel下载", divider="rainbow")
            st.download_button("⬇️ 下载汇总Excel报告（含月度分析表）",
                               data=excel_buffer.getvalue(),
                               file_name="小红书分析汇总报告.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.balloons()
else:
    st.info("👆 请上传Excel文件开始分析。")


