import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from PIL import Image
import pytesseract
import io

st.set_page_config(layout="wide", page_title="公务机飞行计划")

# 飞机列表（含N/A）
AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]

# ---------- 动态生成日期（从今天开始，连续7天）----------
today = datetime.now().date()
date_objects = [today + timedelta(days=i) for i in range(7)]
DATES = [d.strftime("%m-%d") for d in date_objects]
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

# 初始化计划列表（示例计划）
if 'plans' not in st.session_state:
    st.session_state.plans = [
        FlightPlan(1, "B652Q", "03-15", "07:00", "09:00", "韩国首尔金浦", "北京首都"),
        FlightPlan(2, "B652Q", "03-15", "17:00", "20:50", "日本东京羽田", "天津滨海"),
        FlightPlan(3, "B652Q", "03-16", "05:00", "07:45", "天津滨海", "重庆江北"),
        FlightPlan(4, "B652Q", "03-17", "07:00", "08:45", "深圳宝安", "上海虹桥"),
        FlightPlan(5, "B652R", "03-15", "11:50", "14:00", "越南金兰", "马来西亚吉隆坡", is_ferry=True),
        FlightPlan(6, "B652R", "03-16", "07:30", "11:45", "香港", "孟加拉达卡"),
        FlightPlan(7, "B652S", "03-18", "17:00", "19:05", "泰国普吉", "老挝万象"),
        FlightPlan(8, "N440QS", "03-15", "09:00", "11:00", "郑州新郑", "上海虹桥"),
        FlightPlan(9, "N440QS", "03-16", "16:00", "18:05", "越南金兰", "台中清泉岗", is_ferry=True),
    ]

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

# ---------- OCR解析函数（针对截图优化）----------
def parse_ocr_text(text):
    lines = text.split('\n')
    plans = []
    # 匹配常见格式：飞机号 时间 机场1—机场2
    pattern = r'([A-Z0-9]+)(\d{2}:\d{2})-(\d{2}:\d{2})\s+([^—\s]+)[—\-](.+)'
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.search(pattern, line)
        if match:
            aircraft = match.group(1)
            start = match.group(2)
            end = match.group(3)
            dep = match.group(4).strip()
            arr = match.group(5).strip()
            arr = re.sub(r'\s+[PC][0-9]{3,}.*$', '', arr)  # 去除机组信息
            is_ferry = 'F' in line
            if aircraft not in AIRCRAFT:
                aircraft = "N/A"
            plans.append({
                'aircraft': aircraft,
                'start': start,
                'end': end,
                'dep': dep,
                'arr': arr,
                'is_ferry': is_ferry
            })
    return plans

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📸 截图识别")
    uploaded_file = st.file_uploader("上传航班计划截图", type=['png','jpg','jpeg'])
    
    # 简易识别（直接添加，日期默认今天）
    use_mock = st.checkbox("使用模拟识别（不依赖OCR）", value=True)
    if st.button("快速识别（放入今天）", width='stretch'):
        if uploaded_file is not None and not use_mock:
            image = Image.open(uploaded_file)
            try:
                text = pytesseract.image_to_string(image, lang='eng+chi_sim')
                st.write("OCR结果预览：", text[:300])
                parsed = parse_ocr_text(text)
                if parsed:
                    for item in parsed:
                        new_plan = FlightPlan(
                            pid=get_next_id(),
                            aircraft=item['aircraft'],
                            date=DATES[0],
                            start=item['start'],
                            end=item['end'],
                            dep_apt=item['dep'],
                            arr_apt=item['arr'],
                            is_ferry=item['is_ferry']
                        )
                        st.session_state.plans.append(new_plan)
                    st.success(f"已添加 {len(parsed)} 个计划到今天")
                else:
                    st.warning("未识别到任何计划")
            except Exception as e:
                st.error(f"OCR失败：{e}")
        else:
            # 模拟识别
            mock_plans = [
                ("B652Q", "07:00", "09:00", "首尔金浦", "北京首都", False),
                ("B652Q", "17:00", "20:50", "日本东京羽田", "天津滨海", False),
                ("B652R", "11:50", "14:00", "越南金兰", "吉隆坡", True),
                ("B652R", "07:30", "11:45", "香港", "孟加拉达卡", False),
                ("N440QS", "09:00", "11:00", "郑州新郑", "上海虹桥", False),
                ("N440QS", "16:00", "18:05", "台中清泉岗", "香港", True),
                ("MLLIN", "08:45", "10:30", "柬埔寨金边", "新加坡", True),
                ("MLLIN", "12:30", "15:55", "新加坡", "香港", False),
            ]
            for ac, s, e, dep, arr, ferry in mock_plans:
                target_ac = ac if ac in AIRCRAFT else "N/A"
                new_plan = FlightPlan(
                    pid=get_next_id(),
                    aircraft=target_ac,
                    date=DATES[0],
                    start=s,
                    end=e,
                    dep_apt=dep,
                    arr_apt=arr,
                    is_ferry=ferry
                )
                st.session_state.plans.append(new_plan)
            st.success(f"模拟识别：已添加 {len(mock_plans)} 个测试计划到今天")

    # ---------- 新增：批量识别与日期修正 ----------
    with st.expander("🛠️ 批量识别（可调整日期）"):
        if uploaded_file is not None:
            if st.button("开始批量识别", width='stretch'):
                image = Image.open(uploaded_file)
                try:
                    text = pytesseract.image_to_string(image, lang='eng+chi_sim')
                    parsed = parse_ocr_text(text)
                    if parsed:
                        # 将识别结果存入session_state，每项增加一个日期索引（默认今天）
                        for item in parsed:
                            item['date_idx'] = 0  # 默认今天
                        st.session_state['batch_plans'] = parsed
                        st.success(f"已识别 {len(parsed)} 条计划，请在下方调整日期")
                    else:
                        st.warning("未识别到任何计划")
                except Exception as e:
                    st.error(f"OCR失败：{e}")
            
            # 如果存在批量识别结果，显示可编辑表格
            if 'batch_plans' in st.session_state and st.session_state['batch_plans']:
                st.markdown("#### 待添加计划")
                # 准备数据框
                data = []
                for idx, item in enumerate(st.session_state['batch_plans']):
                    data.append({
                        "选择": True,
                        "飞机": item['aircraft'],
                        "起飞": item['start'],
                        "落地": item['end'],
                        "起飞机场": item['dep'],
                        "落地机场": item['arr'],
                        "调机": item['is_ferry'],
                        "日期": st.selectbox(
                            "",
                            range(7),
                            format_func=lambda x: f"{DATE_LABELS[x]} {DATES[x]}",
                            key=f"date_{idx}",
                            index=item.get('date_idx', 0),
                            label_visibility="collapsed"
                        )
                    })
                df_batch = pd.DataFrame(data)
                # 显示可编辑表格（由于selectbox已嵌入，这里直接显示会重复，我们用另一种方式：每行一个选择框）
                # 更简单的方法：直接用st.data_editor，但日期列用下拉框需要特殊处理。为简化，我们使用st.data_editor配合column_config
                # 但streamlit的data_editor对日期选择有限制，我们改用每行单独显示的方式，但为了界面简洁，这里采用循环显示
                for idx, item in enumerate(st.session_state['batch_plans']):
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([1,1,1,1.5,1.5,1,1.5])
                    with col1:
                        use = st.checkbox("", key=f"use_{idx}", value=True)
                    with col2:
                        st.write(item['aircraft'])
                    with col3:
                        st.write(f"{item['start']}-{item['end']}")
                    with col4:
                        st.write(item['dep'])
                    with col5:
                        st.write(item['arr'])
                    with col6:
                        st.write("F" if item['is_ferry'] else "")
                    with col7:
                        date_idx = st.selectbox(
                            "",
                            range(7),
                            format_func=lambda x: f"{DATE_LABELS[x]} {DATES[x]}",
                            key=f"batch_date_{idx}",
                            index=item.get('date_idx', 0),
                            label_visibility="collapsed"
                        )
                        item['date_idx'] = date_idx
                    # 存储选择状态
                    if 'use_flags' not in st.session_state:
                        st.session_state['use_flags'] = {}
                    st.session_state['use_flags'][idx] = use
                
                if st.button("✅ 确认添加所选计划", width='stretch'):
                    added = 0
                    for idx, item in enumerate(st.session_state['batch_plans']):
                        if st.session_state['use_flags'].get(idx, False):
                            new_plan = FlightPlan(
                                pid=get_next_id(),
                                aircraft=item['aircraft'],
                                date=DATES[item['date_idx']],
                                start=item['start'],
                                end=item['end'],
                                dep_apt=item['dep'],
                                arr_apt=item['arr'],
                                is_ferry=item['is_ferry']
                            )
                            # 可选冲突检查（略）
                            st.session_state.plans.append(new_plan)
                            added += 1
                    st.success(f"已添加 {added} 个计划")
                    # 清空批量识别结果
                    del st.session_state['batch_plans']
                    st.rerun()
        else:
            st.info("请先上传截图")

    st.header("➕ 手动添加计划")
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

# ---------- 日历网格（与之前完全相同）----------
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
                    selected_ac = st.selectbox(
                        "✈️",
                        options,
                        index=0,
                        key=f"move_{p.id}",
                        label_visibility="collapsed"
                    )
                    if selected_ac != ac:
                        conflict = False
                        if selected_ac != "N/A":
                            conflict = check_conflict(st.session_state.plans, selected_ac, p.date, p.start, p.end, exclude_id=p.id)
                        if conflict:
                            st.error(f"时间冲突，不能移动到 {selected_ac}")
                        else:
                            p.aircraft = selected_ac
                            st.rerun()
            else:
                st.markdown("<div style='color:#adb5bd; text-align:center; padding:12px 0;'>—</div>", unsafe_allow_html=True)

# ---------- 调机计划编辑区域（保持不变）----------
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
    df = pd.DataFrame([{
        "飞机": p.aircraft,
        "日期": p.date,
        "起飞": p.start,
        "落地": p.end,
        "起飞机场": p.dep_apt,
        "落地机场": p.arr_apt,
        "调机": p.is_ferry
    } for p in st.session_state.plans])
    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("📌 使用说明：上传截图后，点击「批量识别」可逐条调整日期，确认后一次性添加。快速识别会将所有计划默认放入今天。")
