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

def parse_cell_text(text):
    """解析单元格内多行计划文本，返回计划字典列表"""
    lines = text.strip().split('\n')
    plans = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        is_ferry = 'F' in line
        line_clean = line.replace('F', '').strip()
        pattern = r'(\d{2}:\d{2})-(\d{2}:\d{2})\s+([^-]+)-(.+)'
        match = re.search(pattern, line_clean)
        if match:
            start = match.group(1)
            end = match.group(2)
            dep = match.group(3).strip()
            arr = match.group(4).strip()
            plans.append({
                'start': start,
                'end': end,
                'dep': dep,
                'arr': arr,
                'is_ferry': is_ferry
            })
    return plans

def parse_excel(df):
    """从DataFrame解析计划，返回候选计划列表（针对用户提供的Excel格式优化）"""
    # 去除列名中的首尾空格
    df.columns = df.columns.astype(str).str.strip()
    col_names = list(df.columns)
    st.write("检测到的列名（已去除空格）：", col_names)

    # 直接根据您提供的Excel列顺序映射（列索引从0开始）
    # 根据实际内容，列名在第1行（索引1），数据从索引2开始
    # 但pandas读取后列名已变为字符串，我们需要通过实际内容判断
    # 通过观察，需要的列有：飞机注册号（列C）、用途（列D）、出发日期（列G）、计划出发（列H）、预计到达（列O）、出发地（列K）、到达地（列M）
    # 由于列名可能变化，我们通过关键字匹配更稳健
    required_keywords = {
        '飞机注册号': ['飞机注册号', '注册号'],
        '用途': ['用途'],
        '出发日期': ['出发日期'],
        '计划出发': ['计划出发'],
        '预计到达': ['预计到达'],
        '出发地': ['出发地'],
        '到达地': ['到达地']
    }
    
    matched_cols = {}
    for key, keywords in required_keywords.items():
        found = False
        for col in col_names:
            if any(kw in col for kw in keywords):
                matched_cols[key] = col
                found = True
                break
        if not found:
            st.error(f"未能找到匹配的列：{key}，请确保Excel包含相关列（当前列名：{col_names}）")
            return []
    
    candidates = []
    for idx, row in df.iterrows():
        ac = row[matched_cols['飞机注册号']]
        if ac not in AIRCRAFT:
            ac = "N/A"
        
        try:
            date_obj = pd.to_datetime(row[matched_cols['出发日期']]).date()
            date_str = date_obj.strftime("%m-%d")
        except:
            continue
        
        try:
            start = pd.to_datetime(row[matched_cols['计划出发']]).strftime("%H:%M")
        except:
            start = str(row[matched_cols['计划出发']]).strip()
        
        try:
            end = pd.to_datetime(row[matched_cols['预计到达']]).strftime("%H:%M")
        except:
            end = str(row[matched_cols['预计到达']]).strip()
        
        dep = str(row[matched_cols['出发地']]).strip()
        arr = str(row[matched_cols['到达地']]).strip()
        is_ferry = ('调机' in str(row[matched_cols['用途']]))
        
        candidates.append({
            'aircraft': ac,
            'date_original': date_str,
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
            plans_to_add = parse_cell_text(cell_text)
            if not plans_to_add:
                st.warning("未解析到任何计划，请检查格式")
            else:
                conflicts = []
                added = 0
                for item in plans_to_add:
                    if check_conflict(st.session_state.plans, selected_aircraft, target_date, item['start'], item['end']):
                        conflicts.append(f"{item['start']}-{item['end']}")
                    else:
                        new_plan = FlightPlan(
                            pid=get_next_id(),
                            aircraft=selected_aircraft,
                            date=target_date,
                            start=item['start'],
                            end=item['end'],
                            dep_apt=item['dep'],
                            arr_apt=item['arr'],
                            is_ferry=item['is_ferry']
                        )
                        st.session_state.plans.append(new_plan)
                        added += 1
                if conflicts:
                    st.error(f"以下计划时间冲突，未添加：{', '.join(conflicts)}")
                if added > 0:
                    st.success(f"成功添加 {added} 个计划到 {selected_aircraft} {DATE_LABELS[selected_col]} {target_date}")
                    st.rerun()

    st.markdown("---")
    st.header("📊 上传Excel自动解析")
    uploaded_excel = st.file_uploader("选择Excel文件（.xlsx）", type=['xlsx'])
    
    if uploaded_excel is not None:
        try:
            # 关键修改：指定第二行为列名（header=1），并跳过前两行无用数据
            df = pd.read_excel(uploaded_excel, header=1)
            # 删除可能的前几行空数据（实际数据从第3行开始，header=1后自动处理）
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
    
    if 'excel_candidates' in st.session_state and st.session_state['excel_candidates']:
        st.markdown("#### 待导入计划预览")
        data = []
        for idx, cand in enumerate(st.session_state['excel_candidates']):
            # 尝试将原始日期匹配到日历列
            try:
                if cand['date_original'] in DATES:
                    default_idx = DATES.index(cand['date_original'])
                else:
                    default_idx = 0
            except:
                default_idx = 0
            
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
