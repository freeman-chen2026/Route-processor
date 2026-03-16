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
DATES = [d.strftime("%m-%d") for d in date_objects]  # 格式：MM-DD
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

# 初始化计划列表（示例计划使用固定日期，可能不在当前动态日期范围内，但你可以手动添加新计划）
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
    """HH:MM 转换为分钟数"""
    h, m = map(int, t.split(':'))
    return h*60 + m

def check_conflict(plans, aircraft, date, start, end, exclude_id=None):
    """检查指定飞机在指定日期时间段是否有冲突（排除自己）"""
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
    """生成计划块的HTML（确保标签正确闭合）"""
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

# ---------- 侧边栏（截图识别和手动添加）----------
with st.sidebar:
    st.header("📸 截图识别")
    uploaded_file = st.file_uploader("上传航班计划截图", type=['png','jpg','jpeg'])
    use_mock = st.checkbox("使用模拟识别（不依赖OCR）", value=True)
    
    if st.button("识别并生成计划", width='stretch'):
        if uploaded_file is not None and not use_mock:
            image = Image.open(uploaded_file)
            try:
                text = pytesseract.image_to_string(image, lang='eng')
                st.write("OCR识别结果：", text)
                # 简单解析（可后续完善）
                st.warning("OCR解析功能待完善，请使用模拟模式")
            except Exception as e:
                st.error(f"OCR失败：{e}")
        else:
            # 模拟识别：生成两个测试计划放在N/A上，日期使用今天
            mock_plans = [
                ("B652Q", "07:00", "09:00", "首尔金浦", "北京首都"),
                ("B652R", "11:50", "14:00", "越南金兰", "吉隆坡"),
            ]
            for ac, s, e, dep, arr in mock_plans:
                new_plan = FlightPlan(
                    pid=get_next_id(),
                    aircraft="N/A",  # 先放在N/A
                    date=DATES[0],   # 使用今天日期
                    start=s,
                    end=e,
                    dep_apt=dep,
                    arr_apt=arr,
                    is_ferry=False
                )
                st.session_state.plans.append(new_plan)
            st.success("模拟识别：已添加2个测试计划到N/A（今天日期）")

    st.header("➕ 手动添加计划")
    with st.form("add_plan_form"):
        col1, col2 = st.columns(2)
        with col1:
            ac = st.selectbox("飞机", AIRCRAFT, index=7)  # 默认N/A
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

# ---------- 日历网格 ----------
st.write("## 飞行计划日历")

# 第一行：日期标题
cols = st.columns([1] + [1]*len(DATES))
with cols[0]:
    st.markdown("**飞机/日期**")
for i, label in enumerate(DATE_LABELS):
    with cols[i+1]:
        st.markdown(f"**{label}**<br><span style='font-weight:normal'>{DATES[i]}</span>", unsafe_allow_html=True)

# 为每架飞机生成一行
for ac in AIRCRAFT:
    row_cols = st.columns([1] + [1]*len(DATES))
    with row_cols[0]:
        st.markdown(f"**{ac}**")
    
    for i, date in enumerate(DATES):
        with row_cols[i+1]:
            # 获取该飞机该日的所有计划
            day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
            day_plans.sort(key=lambda x: x.start)
            if day_plans:
                for p in day_plans:
                    # 显示计划块
                    st.markdown(plan_block_html(p), unsafe_allow_html=True)
                    
                    # 飞机切换下拉框（每个计划一个）
                    options = [ac] + [a for a in AIRCRAFT if a != ac]
                    selected_ac = st.selectbox(
                        "✈️",
                        options,
                        index=0,
                        key=f"move_{p.id}",
                        label_visibility="collapsed"
                    )
                    if selected_ac != ac:
                        # 检查冲突（如果目标不是N/A）
                        conflict = False
                        if selected_ac != "N/A":
                            conflict = check_conflict(st.session_state.plans, selected_ac, p.date, p.start, p.end, exclude_id=p.id)
                        if conflict:
                            st.error(f"时间冲突，不能移动到 {selected_ac}")
                        else:
                            # 更新飞机
                            p.aircraft = selected_ac
                            st.rerun()
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
st.caption("📌 日期从今天开始动态更新。示例计划使用固定日期，可能不在当前显示范围内，请手动添加新计划体验。")
