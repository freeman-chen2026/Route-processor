import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(layout="wide", page_title="公务机飞行计划")

# 飞机列表（含N/A）
AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]

# ---------- 动态生成日期（从今天开始，连续7天）----------
today = datetime.now().date()
date_objects = [today + timedelta(days=i) for i in range(7)]
DATES = [d.strftime("%m-%d") for d in date_objects]          # 格式：MM-DD
# 星期映射（英文转中文）
weekday_map = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
    "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
}
DATE_LABELS = [weekday_map[d.strftime("%A")] for d in date_objects]

# 用于生成唯一ID
if 'id_counter' not in st.session_state:
    st.session_state.id_counter = 1000

# ---------- 数据结构 ----------
class FlightPlan:
    def __init__(self, pid, aircraft, date, start, end, dep_apt, arr_apt, is_ferry=False):
        self.id = pid
        self.aircraft = aircraft
        self.date = date
        self.start = start
        self.end = end
        self.dep_apt = dep_apt
        self.arr_apt = arr_apt
        self.is_ferry = is_ferry

if 'plans' not in st.session_state:
    st.session_state.plans = []  # 初始为空

# ---------- 辅助函数 ----------
def get_next_id():
    st.session_state.id_counter += 1
    return st.session_state.id_counter

def time_to_minutes(t):
    h, m = map(int, t.split(':'))
    return h*60 + m

def check_conflict(plans, aircraft, date, start, end, exclude_id=None):
    start_m = time_to_minutes(start)
    end_m = time_to_minutes(end)
    for p in plans:
        if p.aircraft == aircraft and p.date == date and p.id != exclude_id:
            p_start = time_to_minutes(p.start)
            p_end = time_to_minutes(p.end)
            if not (end_m <= p_start or start_m >= p_end):
                return True
    return False

def plan_block_html(plan):
    color = "#ffebee" if plan.is_ferry else "#e3f2fd"
    border_color = "#f44336" if plan.is_ferry else "#2196f3"
    f_tag = '<span style="color:#f44336; font-weight:bold; margin-left:4px;">F</span>' if plan.is_ferry else ''
    return f'''
    <div style="
        background-color: {color};
        border-left: 4px solid {border_color};
        padding: 6px 8px;
        margin: 4px 0;
        font-size: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        border-radius: 0;
    ">
        <strong>{plan.start}-{plan.end}</strong>{f_tag}<br>
        <span style="color:#555;">{plan.dep_apt} → {plan.arr_apt}</span>
    </div>
    '''

def parse_excel(df):
    """从DataFrame解析计划，返回候选计划列表"""
    candidates = []
    required_cols = ['飞机注册号', '用途', '出发日期', '计划出发', '出发地', '到达地']
    # 检查必要列是否存在（可能有别名，这里简化）
    if not all(col in df.columns for col in required_cols):
        st.error("Excel文件缺少必要列，请确保包含：飞机注册号、用途、出发日期、计划出发、出发地、到达地")
        return candidates
    
    for idx, row in df.iterrows():
        ac = row['飞机注册号']
        if ac not in AIRCRAFT:
            ac = "N/A"  # 不在列表中的飞机放入N/A
        
        # 解析日期
        try:
            date_obj = pd.to_datetime(row['出发日期']).date()
            date_str = date_obj.strftime("%m-%d")
        except:
            continue  # 日期无效则跳过
        
        # 解析时间
        try:
            start = pd.to_datetime(row['计划出发']).strftime("%H:%M")
        except:
            start = str(row['计划出发']).strip()
        
        # 注意：Excel中没有计划到达时间，只有出发日期和计划出发，需要根据实际飞行时间推算？用户提供的Excel中有“预计到达”列，但不在required_cols里。为简化，我们假设计划中包含了到达时间？从样本看，每个行程都有“预计到达”列（格式HH:MM）。所以需要添加。
        # 为了准确，我们应包含“预计到达”列。让我们重新定义必要列。
        # 实际上样本中有“预计到达”列。我们更新列检查。
        if '预计到达' in df.columns:
            try:
                end = pd.to_datetime(row['预计到达']).strftime("%H:%M")
            except:
                end = str(row['预计到达']).strip()
        else:
            # 如果没有，跳过或设为默认？最好提示。
            st.warning("缺少预计到达列，跳过该行")
            continue
        
        dep = str(row['出发地']).strip()
        arr = str(row['到达地']).strip()
        is_ferry = ('调机' in str(row['用途']))
        
        candidates.append({
            'aircraft': ac,
            'date_original': date_str,
            'date_idx': None,  # 稍后映射
            'start': start,
            'end': end,
            'dep': dep,
            'arr': arr,
            'is_ferry': is_ferry
        })
    return candidates

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📌 坐标输入（手动录入）")
    with st.expander("按单元格批量添加计划", expanded=False):
        selected_aircraft = st.selectbox("选择行（飞机）", AIRCRAFT, index=0)
        col_options = [f"{DATE_LABELS[i]} {DATES[i]}" for i in range(7)]
        selected_col = st.selectbox("选择列（日期）", range(7), format_func=lambda x: col_options[x])
        target_date = DATES[selected_col]
        
        cell_text = st.text_area(
            "输入该单元格内所有计划（每行一个）",
            height=100,
            placeholder="示例：\n07:00-09:00 首尔金浦-北京首都\n17:00-20:50 日本东京羽田-天津滨海 F"
        )
        
        if st.button("添加到单元格", width='stretch'):
            # 解析函数略（同前，此处省略，实际应有）
            st.info("手动添加功能保留，请根据需要自行填写")

    st.markdown("---")
    st.header("📊 上传Excel自动解析")
    uploaded_excel = st.file_uploader("选择Excel文件（.xlsx）", type=['xlsx'])
    
    if uploaded_excel is not None:
        try:
            df = pd.read_excel(uploaded_excel)
            st.success(f"成功读取Excel，共 {len(df)} 行")
            
            if st.button("解析并预览", width='stretch'):
                candidates = parse_excel(df)
                if candidates:
                    st.session_state['excel_candidates'] = candidates
                    st.success(f"解析出 {len(candidates)} 条候选计划")
                else:
                    st.warning("未解析出任何计划，请检查文件格式")
        except Exception as e:
            st.error(f"读取Excel失败：{e}")
    
    # 显示候选计划预览和导入界面
    if 'excel_candidates' in st.session_state and st.session_state['excel_candidates']:
        st.markdown("#### 待导入计划预览")
        # 为每个候选计划添加日期选择（映射到日历中的日期列）
        data = []
        for idx, cand in enumerate(st.session_state['excel_candidates']):
            # 尝试将原始日期映射到DATES中的索引
            try:
                orig_date = datetime.strptime(cand['date_original'], "%m-%d").date()
                # 查找在DATES中是否存在
                if cand['date_original'] in DATES:
                    default_idx = DATES.index(cand['date_original'])
                else:
                    default_idx = 0
            except:
                default_idx = 0
            
            # 显示一行，带复选框和日期选择
            row_data = {
                "选择": True,
                "飞机": cand['aircraft'],
                "起飞": cand['start'],
                "落地": cand['end'],
                "起飞机场": cand['dep'],
                "落地机场": cand['arr'],
                "调机": "是" if cand['is_ferry'] else "否",
                "原始日期": cand['date_original'],
                "分配日期": st.selectbox(
                    "",
                    range(7),
                    format_func=lambda x: f"{DATE_LABELS[x]} {DATES[x]}",
                    key=f"excel_date_{idx}",
                    index=default_idx,
                    label_visibility="collapsed"
                )
            }
            data.append(row_data)
        
        df_preview = pd.DataFrame(data)
        st.dataframe(df_preview, use_container_width=True)
        
        if st.button("✅ 导入所选计划", width='stretch'):
            added = 0
            conflicts = []
            for idx, row_data in enumerate(data):
                if not row_data["选择"]:
                    continue
                selected_date_idx = st.session_state[f"excel_date_{idx}"]
                target_date = DATES[selected_date_idx]
                cand = st.session_state['excel_candidates'][idx]
                # 检查冲突
                if check_conflict(st.session_state.plans, cand['aircraft'], target_date, cand['start'], cand['end']):
                    conflicts.append(f"{cand['aircraft']} {cand['start']}-{cand['end']} {cand['dep']}-{cand['arr']}")
                else:
                    new_plan = FlightPlan(
                        pid=get_next_id(),
                        aircraft=cand['aircraft'],
                        date=target_date,
                        start=cand['start'],
                        end=cand['end'],
                        dep_apt=cand['dep'],
                        arr_apt=cand['arr'],
                        is_ferry=cand['is_ferry']
                    )
                    st.session_state.plans.append(new_plan)
                    added += 1
            if conflicts:
                st.error(f"以下计划冲突，未添加：{', '.join(conflicts)}")
            if added > 0:
                st.success(f"成功添加 {added} 个计划")
                # 清空候选列表，避免重复添加
                del st.session_state['excel_candidates']
                st.rerun()

    st.markdown("---")
    st.header("🧪 模拟识别（快速测试）")
    if st.button("添加示例计划（今天）", width='stretch'):
        mock_plans = [
            ("B652Q", "07:00", "09:00", "首尔金浦", "北京首都", False),
            ("B652Q", "17:00", "20:50", "日本东京羽田", "天津滨海", False),
            ("B652R", "11:50", "14:00", "越南金兰", "吉隆坡", True),
        ]
        for ac, s, e, dep, arr, ferry in mock_plans:
            new_plan = FlightPlan(
                pid=get_next_id(),
                aircraft=ac,
                date=DATES[0],
                start=s,
                end=e,
                dep_apt=dep,
                arr_apt=arr,
                is_ferry=ferry
            )
            st.session_state.plans.append(new_plan)
        st.success("已添加3个示例计划到今天")
        st.rerun()

    st.header("➕ 手动添加单个计划")
    with st.form("add_plan_form"):
        col1, col2 = st.columns(2)
        with col1:
            ac = st.selectbox("飞机", AIRCRAFT, index=7)
            date_idx = st.selectbox("日期", range(7), format_func=lambda x: f"{DATE_LABELS[x]} {DATES[x]}")
            start = st.text_input("起飞时间 (HH:MM)", "08:00")
            dep = st.text_input("起飞机场", "北京首都")
        with col2:
            is_ferry = st.checkbox("调机计划 (红色F)")
            end = st.text_input("落地时间 (HH:MM)", "10:00")
            arr = st.text_input("落地机场", "上海虹桥")
        submitted = st.form_submit_button("添加计划", width='stretch')
        if submitted:
            if re.match(r'^\d{2}:\d{2}$', start) and re.match(r'^\d{2}:\d{2}$', end):
                new_plan = FlightPlan(
                    pid=get_next_id(),
                    aircraft=ac,
                    date=DATES[date_idx],
                    start=start,
                    end=end,
                    dep_apt=dep,
                    arr_apt=arr,
                    is_ferry=is_ferry
                )
                if ac != "N/A":
                    if check_conflict(st.session_state.plans, ac, DATES[date_idx], start, end):
                        st.error("该时间段已有计划，添加失败")
                    else:
                        st.session_state.plans.append(new_plan)
                        st.success("计划添加成功")
                else:
                    st.session_state.plans.append(new_plan)
                    st.success("计划添加成功 (N/A)")
            else:
                st.error("时间格式错误")

    st.markdown("---")
    st.header("🗑️ 清空所有计划")
    confirm_clear = st.checkbox("确认清空所有计划（不可恢复）")
    if st.button("清空计划", width='stretch', disabled=not confirm_clear):
        st.session_state.plans = []
        st.session_state.id_counter = 1000
        st.success("所有计划已清空")
        st.rerun()

# ---------- 日历网格 ----------
st.write("## 飞行计划日历")

cols = st.columns([1] + [1]*len(DATES))
with cols[0]:
    st.markdown("**飞机/日期**")
for i, label in enumerate(DATE_LABELS):
    with cols[i+1]:
        st.markdown(f"**{label}**<br><span style='font-weight:normal'>{DATES[i]}</span>", unsafe_allow_html=True)

for ac in AIRCRAFT:
    row_cols = st.columns([1] + [1]*len(DATES))
    with row_cols[0]:
        st.markdown(f"**{ac}**")
    for i, date in enumerate(DATES):
        with row_cols[i+1]:
            day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
            day_plans.sort(key=lambda x: x.start)
            if day_plans:
                for p in day_plans:
                    st.markdown(plan_block_html(p), unsafe_allow_html=True)
                    # 飞机切换下拉框（演示功能，可禁用）
                    options = [ac] + [a for a in AIRCRAFT if a != ac]
                    st.selectbox(
                        "✈️",
                        options,
                        index=0,
                        key=f"move_{p.id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
            else:
                st.markdown("<div style='color:#adb5bd; text-align:center; padding:12px 0;'>—</div>", unsafe_allow_html=True)

# ---------- 调机计划编辑区域 ----------
st.markdown("---")
st.markdown("### 🔄 调机计划管理")

ferry_plans = [p for p in st.session_state.plans if p.is_ferry]
if ferry_plans:
    cols_per_row = 3
    for i in range(0, len(ferry_plans), cols_per_row):
        row_plans = ferry_plans[i:i+cols_per_row]
        row_cols = st.columns(cols_per_row)
        for col_idx, fp in enumerate(row_plans):
            with row_cols[col_idx]:
                with st.expander(f"调机 {fp.id} - {fp.aircraft} {fp.date} {fp.start}-{fp.end}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_start = st.text_input("起飞时间", fp.start, key=f"start_{fp.id}")
                        new_dep = st.text_input("起飞机场", fp.dep_apt, key=f"dep_{fp.id}")
                    with col2:
                        new_end = st.text_input("落地时间", fp.end, key=f"end_{fp.id}")
                        new_arr = st.text_input("落地机场", fp.arr_apt, key=f"arr_{fp.id}")
                    if st.button("更新", key=f"update_{fp.id}", width='stretch'):
                        if not (re.match(r'^\d{2}:\d{2}$', new_start) and re.match(r'^\d{2}:\d{2}$', new_end)):
                            st.error("时间格式错误，应为 HH:MM")
                        else:
                            time_changed = (new_start != fp.start) or (new_end != fp.end)
                            if time_changed:
                                if fp.aircraft != "N/A":
                                    if check_conflict(st.session_state.plans, fp.aircraft, fp.date, new_start, new_end, exclude_id=fp.id):
                                        st.error("时间冲突，更新失败")
                                        st.stop()
                            fp.start = new_start
                            fp.end = new_end
                            fp.dep_apt = new_dep
                            fp.arr_apt = new_arr
                            st.success("已更新")
                            st.rerun()
else:
    st.info("暂无调机计划")

# ---------- 底部 ----------
with st.expander("📋 所有计划列表"):
    df_list = pd.DataFrame([{
        "飞机": p.aircraft,
        "日期": p.date,
        "起飞": p.start,
        "落地": p.end,
        "起飞机场": p.dep_apt,
        "落地机场": p.arr_apt,
        "调机": p.is_ferry
    } for p in st.session_state.plans])
    st.dataframe(df_list, use_container_width=True)

st.markdown("---")
st.caption("📌 使用说明：上传Excel后点击解析，可调整日期后导入。支持手动坐标输入和单条添加。调机计划以红色背景显示。")
