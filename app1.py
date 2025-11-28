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

    for col, color in zip(cols, colors):
        y_vals = df[col].values
        ax.plot(df["序号"], y_vals, marker="o", linestyle="-", color=color, label=col)
        line_data[col] = y_vals

    avg_values = {col: pd.Series(vals).mean(skipna=True) for col, vals in line_data.items()}
    bottom_line = min(avg_values, key=avg_values.get)

    for col, color in zip(cols, colors):
        for x, y in zip(df["序号"], df[col]):
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

    for c in ["曝光","封面点击率","点赞","观看量","收藏","评论","涨粉","分享"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["点赞率"] = df["点赞"] / df["观看量"].replace(0, pd.NA)
    df["收藏率"] = df["收藏"] / df["观看量"].replace(0, pd.NA)
    df["赞藏比"] = df["点赞"] / df["收藏"].replace(0, pd.NA)
    df["评论率"] = df["评论"] / df["观看量"].replace(0, pd.NA)
    df["互动率"] = (df["点赞"] + df["评论"] + df["收藏"]) / df["观看量"].replace(0, pd.NA)
    df["有效活跃度"] = df["评论"] / (df["点赞"] + df["收藏"]).replace(0, pd.NA)
    df["转粉率"] = df["涨粉"] / df["观看量"].replace(0, pd.NA)

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
st.info("💡 提示：如需进行【账号/月份横向对比】或【环比分析】，请确保不同文件代表不同账号，或者文件内包含不同月份的数据。")

uploaded_files = st.file_uploader("请上传小红书后台导出的 Excel 文件",
    type=["xls","xlsx"], accept_multiple_files=True)

if uploaded_files:
    placeholder_top = st.empty()
    processed_dfs = {}
    all_data_list = []

    for up_file in uploaded_files:
        try:
            df_raw = pd.read_excel(up_file, header=1)
            df_processed = analyze_and_display(df_raw, up_file.name)
            
            if df_processed is not None:
                account_name = os.path.splitext(up_file.name)[0]
                df_export = df_processed.copy()
                df_export.insert(0, "账号名", account_name)
                sheet_name = ''.join(e for e in up_file.name if e.isalnum())[:31]
                processed_dfs[sheet_name] = df_export
                all_data_list.append(df_export)

        except Exception as e:
            st.error(f"处理文件 {up_file.name} 时发生错误: {e}")

    if processed_dfs:
        # ==============================================================================
        # 🔥🔥 进阶功能：全景对比 & 环比分析 🔥🔥
        # ==============================================================================
        st.markdown("---")
        st.header("🏆 账号/月份 核心指标趋势 & 环比分析", divider="orange")
        
        if all_data_list:
            # 1. 数据准备
            df_all = pd.concat(all_data_list, ignore_index=True)
            
            # 生成 YYYY-MM 格式的年月字符串
            df_all['年月'] = df_all['首次发布时间'].dt.to_period('M').astype(str)
            df_all['估算点击数'] = df_all['封面点击率'] * df_all['曝光']

            # 2. 分组聚合
            df_trend = df_all.groupby(['账号名', '年月']).agg({
                '曝光': 'sum',
                '观看量': 'sum',
                '点赞': 'sum',
                '收藏': 'sum',
                '评论': 'sum',
                '涨粉': 'sum',
                '估算点击数': 'sum'
            }).reset_index()

            # 3. 计算加权指标
            df_trend['互动率'] = (df_trend['点赞'] + df_trend['收藏'] + df_trend['评论']) / df_trend['观看量'].replace(0, pd.NA)
            df_trend['封面点击率'] = df_trend['估算点击数'] / df_trend['曝光'].replace(0, pd.NA)
            
            # 4. 排序与计算环比
            # 确保按【账号、年月】升序排列，保证环比计算正确，且小月份在前
            df_trend.sort_values(by=['账号名', '年月'], ascending=[True, True], inplace=True)
            
            # 计算环比 (MoM)
            df_trend['涨粉环比'] = df_trend.groupby('账号名')['涨粉'].pct_change()
            df_trend['互动率环比'] = df_trend.groupby('账号名')['互动率'].pct_change()
            df_trend['点击率环比'] = df_trend.groupby('账号名')['封面点击率'].pct_change()
            
            # 5. 账号选择器
            all_accounts = df_trend['账号名'].unique()
            selected_accounts = st.multiselect("👇 1. 请选择要对比趋势的账号：", all_accounts, default=all_accounts)

            # ------------------------------------------------------------------
            # A. 趋势图表区域
            # ------------------------------------------------------------------
            if selected_accounts:
                df_chart = df_trend[df_trend['账号名'].isin(selected_accounts)].copy()
                
                # 再次强制按【年月升序】排序，确保图表X轴是从左到右
                df_chart.sort_values(by='年月', ascending=True, inplace=True)

                def plot_compare_metric(metric_name, title_text, is_percent=True):
                    fig, ax = plt.subplots(figsize=(14, 6))
                    for account in selected_accounts:
                        sub_data = df_chart[df_chart['账号名'] == account]
                        if not sub_data.empty:
                            ax.plot(sub_data['年月'], sub_data[metric_name], marker='o', linewidth=2, label=account)
                            
                            if len(sub_data) < 24:
                                for x, y in zip(sub_data['年月'], sub_data[metric_name]):
                                    if pd.notna(y):
                                        txt = f"{y:.1%}" if is_percent else f"{int(y)}"
                                        ax.text(x, y, txt, ha='center', va='bottom', fontsize=10, 
                                                color='black', path_effects=[path_effects.withStroke(linewidth=2, foreground="white")])

                    ax.set_title(title_text, fontsize=16)
                    ax.set_xlabel("月份", fontsize=12)
                    ax.set_ylabel("数值", fontsize=12)
                    ax.tick_params(axis='both', labelsize=10)
                    ax.legend(loc='best', fontsize=10)
                    ax.grid(True, linestyle='--', alpha=0.5)
                    if is_percent:
                        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
                    return fig

                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.subheader("🔥 互动率 - 月度趋势")
                    st.pyplot(plot_compare_metric('互动率', '账号互动率月度走势', is_percent=True))
                
                with col_g2:
                    st.subheader("👀 封面点击率 - 月度趋势")
                    st.pyplot(plot_compare_metric('封面点击率', '账号封面点击率月度走势', is_percent=True))
                
                st.subheader("📈 涨粉数 - 月度趋势")
                st.pyplot(plot_compare_metric('涨粉', '账号月度净涨粉走势', is_percent=False))
                
                # ------------------------------------------------------------------
                # B. 月度对比详细数据表
                # ------------------------------------------------------------------
                st.markdown("---")
                with st.expander("📋 点击展开：查看月度对比详细数据表（含环比增长率）", expanded=True):
                    st.info("💡 **环比说明**：展示相比**上一个月**的增长百分比。")
                    
                    display_cols = [
                        '账号名', '年月', 
                        '涨粉', '涨粉环比',
                        '互动率', '互动率环比',
                        '封面点击率', '点击率环比',
                        '曝光', '观看量'
                    ]
                    
                    df_display = df_chart[display_cols].copy()
                    
                    st.dataframe(df_display.style.format({
                        '涨粉': '{:,.0f}',
                        '互动率': '{:.2%}',
                        '封面点击率': '{:.2%}',
                        '曝光': '{:,.0f}',
                        '观看量': '{:,.0f}',
                        '涨粉环比': '{:+.1%}',
                        '互动率环比': '{:+.1%}',
                        '点击率环比': '{:+.1%}'
                    }).bar(subset=['涨粉'], color='#d65f5f', vmin=0) 
                      .background_gradient(subset=['互动率'], cmap='Greens')
                    )

            else:
                st.warning("请至少选择一个账号查看趋势图。")

            # ------------------------------------------------------------------
            # C. 🔥🔥 核心指标详细透视 (数值在前 + 环比在后) 🔥🔥
            # ------------------------------------------------------------------
            st.markdown("---")
            st.subheader("📅 核心指标详细透视表 (数值在前，环比在后)")
            st.info("📊 排序方式：[10月数值] | [11月数值] ... [10月环比] | [11月环比] ...")

            # 配置映射：指标名称 -> (数值列名, 环比列名, 数值格式化字符串)
            metric_configs = {
                "涨粉数": {"val_col": "涨粉", "mom_col": "涨粉环比", "fmt": "{:,.0f}"},
                "互动率": {"val_col": "互动率", "mom_col": "互动率环比", "fmt": "{:.2%}"},
                "封面点击率": {"val_col": "封面点击率", "mom_col": "点击率环比", "fmt": "{:.2%}"}
            }
            
            target_key = st.selectbox("👇 请选择要查看的指标：", list(metric_configs.keys()))
            cfg = metric_configs[target_key]

            if not df_trend.empty:
                # 1. 生成透视表，包含“数值”和“环比”两类值
                # 结果是 MultiIndex Columns: Level 0 = [数值列, 环比列], Level 1 = [月份]
                pivot_df = df_trend.pivot(index='账号名', columns='年月', values=[cfg['val_col'], cfg['mom_col']])
                
                # 2. 获取所有月份并排序
                sorted_months = sorted(df_trend['年月'].unique())
                
                # 3. 🔥🔥 关键修改：先放所有数值列，再放所有环比列 🔥🔥
                val_cols_ordered = [(cfg['val_col'], m) for m in sorted_months]
                mom_cols_ordered = [(cfg['mom_col'], m) for m in sorted_months]
                
                # 拼接：所有月份数值 + 所有月份环比
                new_columns_order = val_cols_ordered + mom_cols_ordered
                
                # 4. 根据新顺序重排 DataFrame 列
                try:
                    df_final = pivot_df.reindex(columns=new_columns_order)
                    
                    # 5. 设置样式 (Styler)
                    idx = pd.IndexSlice
                    styler = df_final.style
                    
                    # 格式化数值列 (数值为空填充None)
                    styler = styler.format(cfg['fmt'], na_rep="None", subset=idx[:, (cfg['val_col'], slice(None))])
                    
                    # 格式化环比列 (带正负号百分比，空值填充None)
                    styler = styler.format("{:+.1%}", na_rep="None", subset=idx[:, (cfg['mom_col'], slice(None))])
                    
                    # 给环比列加背景色 (红绿涨跌)
                    styler = styler.background_gradient(cmap='RdYlGn', vmin=-0.5, vmax=0.5, 
                                                      subset=idx[:, (cfg['mom_col'], slice(None))])
                    
                    st.write(f"**📊 各账号 {target_key} 月度详细数据表：**")
                    st.dataframe(styler)
                    
                except KeyError as e:
                    st.error(f"数据重排时出错。详细错误: {e}")
            else:
                st.warning("暂无数据可用于生成透视表。")

    # ==============================================================================
    # Excel 导出逻辑
    # ==============================================================================
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        for name, d in processed_dfs.items():
            d.to_excel(writer, sheet_name=name, index=False)
        if all_data_list:
            pd.concat(all_data_list, ignore_index=True).to_excel(writer, sheet_name="所有数据明细汇总", index=False)
        if 'df_trend' in locals():
            df_trend.to_excel(writer, sheet_name="月度统计(含环比)", index=False)

    with placeholder_top.container():
        st.header("汇总Excel下载", divider="rainbow")
        st.download_button("⬇️ 下载汇总Excel报告（含月度分析表）",
                           data=excel_buffer.getvalue(),
                           file_name="小红书分析汇总报告.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.balloons()

else:
    st.info("👆 请上传Excel文件开始分析。")
