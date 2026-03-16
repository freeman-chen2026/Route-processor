import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from PIL import Image
import pytesseract
import io

# ---------- 配置 ----------
st.set_page_config(layout="wide", page_title="公务机飞行计划")

# 飞机列表（含N/A）
AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]
# 日期范围
DATES = ["03-15", "03-16", "03-17", "03-18", "03-19", "03-20", "03-21"]
DATE_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

# 用于生成唯一ID
if 'id_counter' not in st.session_state:
    st.session_state.id_counter = 1000

# ---------- 数据结构 ----------
class FlightPlan:
    def __init__(self, pid, aircraft, date, start, end, dep_apt, arr_apt, plan_type='passenger', crew='', is_ferry=False):
        self.id = pid
        self.aircraft = aircraft
        self.date = date
        self.start = start
        self.end = end
        self.dep_apt = dep_apt
        self.arr_apt = arr_apt
        self.plan_type = plan_type
        self.crew = crew
        self.is_ferry = is_ferry

    def to_dict(self):
        return {
            'id': self.id,
            'aircraft': self.aircraft,
            'date': self.date,
            'start': self.start,
            'end': self.end,
            'dep_apt': self.dep_apt,
            'arr_apt': self.arr_apt,
            'type': self.plan_type,
            'crew': self.crew,
            'is_ferry': self.is_ferry
        }

# 初始化计划列表
if 'plans' not in st.session_state:
    st.session_state.plans = [
        FlightPlan(1, "B652Q", "03-15", "07:00", "09:00", "韩国首尔金浦", "北京首都", is_ferry=False),
        FlightPlan(2, "B652Q", "03-15", "17:00", "20:50", "日本东京羽田", "天津滨海", is_ferry=False),
        FlightPlan(3, "B652Q", "03-16", "05:00", "07:45", "天津滨海", "重庆江北", is_ferry=False),
        FlightPlan(4, "B652Q", "03-17", "07:00", "08:45", "深圳宝安", "上海虹桥", is_ferry=False),
        FlightPlan(5, "B652R", "03-15", "11:50", "14:00", "越南金兰", "马来西亚吉隆坡", is_ferry=True),
        FlightPlan(6, "B652R", "03-16", "07:30", "11:45", "香港", "孟加拉达卡", is_ferry=False),
        FlightPlan(7, "B652S", "03-18", "17:00", "19:05", "泰国普吉", "老挝万象", is_ferry=False),
        FlightPlan(8, "N440QS", "03-15", "09:00", "11:00", "郑州新郑", "上海虹桥", is_ferry=False),
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

def render_plan_block(plan):
    if plan.is_ferry:
        color = "#ffebee"
        border = "#f44336"
        tag = " <span style='color:#f44336; font-weight:bold;'>F</span>"
    else:
        color = "#e3f2fd"
        border = "#2196f3"
        tag = ""
    
    return f"""
    <div style="
        background:{color};
        border-left: 4px solid {border};
        border-radius: 0px;
        padding: 6px 8px;
        margin: 4px 0;
        font-size: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        font-family: monospace;
    ">
        <strong>{plan.start}-{plan.end}</strong>{tag}<br>
        <span style="color:#555;">{plan.dep_apt}→{plan.arr_apt}</span>
    </div>
    """

def parse_ocr_text(text):
    lines = text.split('\n')
    plans = []
    pattern = r'([A-Z0-9]+)(\d{2}:\d{2})-(\d{2}:\d{2})\s+([^-]+)-(.+)'
    for line in lines:
        match = re.search(pattern, line)
        if match:
            aircraft = match.group(1)
            start = match.group(2)
            end = match.group(3)
            dep = match.group(4).strip()
            arr = match.group(5).strip()
            plans.append({
                'aircraft': aircraft,
                'start': start,
                'end': end,
                'dep': dep,
                'arr': arr
            })
    return plans

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📸 截图识别")
    uploaded_file = st.file_uploader("上传航班计划截图", type=['png','jpg','jpeg'])
    use_mock = st.checkbox("使用模拟识别（不依赖OCR）", value=True)
    
    if st.button("识别并生成计划", use_container_width=True):
        if uploaded_file is not None and not use_mock:
            image = Image.open(uploaded_file)
            try:
                text = pytesseract.image_to_string(image, lang='eng')
                st.write("OCR识别结果：", text)
                parsed = parse_ocr_text(text)
                for item in parsed:
                    new_plan = FlightPlan(
                        pid=get_next_id(),
                        aircraft=item['aircraft'],
                        date=DATES[0],
                        start=item['start'],
                        end=item['end'],
                        dep_apt=item['dep'],
                        arr_apt=item['arr'],
                        is_ferry=False
                    )
                    st.session_state.plans.append(new_plan)
                st.success(f"已生成 {len(parsed)} 个计划")
            except Exception as e:
                st.error(f"OCR失败：{e}")
        else:
            mock_plans = [
                ("B652Q", "07:00", "09:00", "首尔金浦", "北京首都"),
                ("B652R", "11:50", "14:00", "越南金兰", "吉隆坡"),
            ]
            for ac, s, e, dep, arr in mock_plans:
                new_plan = FlightPlan(
                    pid=get_next_id(),
                    aircraft=ac,
                    date=DATES[0],
                    start=s,
                    end=e,
                    dep_apt=dep,
                    arr_apt=arr,
                    is_ferry=False
                )
                st.session_state.plans.append(new_plan)
            st.success("模拟识别：已添加2个测试计划")

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
        
        submitted = st.form_submit_button("添加计划", use_container_width=True)
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

# ---------- 主界面：Excel风格日历表格 ----------
st.markdown("""
<style>
    .excel-table {
        border-collapse: collapse;
        width: 100%;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    .excel-table th {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 10px 8px;
        text-align: center;
        font-weight: 600;
        color: #495057;
    }
    .excel-table td {
        border: 1px solid #dee2e6;
        padding: 8px;
        vertical-align: top;
        min-height: 100px;
        background-color: white;
    }
    .excel-table tr:first-child th {
        border-top: 2px solid #adb5bd;
    }
    .excel-table tr th:first-child, .excel-table tr td:first-child {
        border-left: 2px solid #adb5bd;
    }
    .excel-table tr th:last-child, .excel-table tr td:last-child {
        border-right: 2px solid #adb5bd;
    }
    .excel-table tr:last-child td {
        border-bottom: 2px solid #adb5bd;
    }
    .aircraft-header {
        background-color: #e9ecef;
        font-weight: 600;
        text-align: center;
        vertical-align: middle !important;
        color: #212529;
        width: 80px;
    }
    .plan-container {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .stButton > button {
        background-color: #f8f9fa;
        border: 1px solid #ced4da;
        color: #495057;
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .stButton > button:hover {
        background-color: #e9ecef;
        border-color: #adb5bd;
    }
</style>
""", unsafe_allow_html=True)

# 构建表格
html = '<table class="excel-table"><tr><th>飞机/日期</th>'
for i, label in enumerate(DATE_LABELS):
    html += f'<th>{label}<br><span style="font-weight:normal;">{DATES[i]}</span></th>'
html += '</tr>'

# 为每架飞机生成行
for ac in AIRCRAFT:
    html += f'<tr><td class="aircraft-header">{ac}</td>'
    
    for i, date in enumerate(DATES):
        html += '<td><div class="plan-container">'
        
        day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
        day_plans.sort(key=lambda x: x.start)
        
        if day_plans:
            for p in day_plans:
                # 计划块
                if p.is_ferry:
                    bg = "#ffebee"
                    border = "#f44336"
                else:
                    bg = "#e3f2fd"
                    border = "#2196f3"
                
                html += f'''
                <div style="
                    background:{bg};
                    border-left:4px solid {border};
                    padding:6px 8px;
                    margin:4px 0;
                    font-size:12px;
                    box-shadow:0 1px 2px rgba(0,0,0,0.1);
                ">
                    <strong>{p.start}-{p.end}</strong>
                    { '<span style="color:#f44336; font-weight:bold; margin-left:4px;">F</span>' if p.is_ferry else '' }
                    <br>
                    <span style="color:#555;">{p.dep_apt}→{p.arr_apt}</span>
                '''
                
                # 飞机切换下拉框（每个计划一个）
                html += f'''
                    <div style="margin-top:6px;">
                        <select onchange="alert('飞机切换功能需与后端配合，当前为演示')" style="
                            width:100%;
                            padding:2px 4px;
                            font-size:11px;
                            border:1px solid #ced4da;
                            border-radius:3px;
                        ">
                            <option value="{p.aircraft}" selected>{p.aircraft} ✓</option>
                '''
                for other_ac in AIRCRAFT:
                    if other_ac != p.aircraft:
                        html += f'<option value="{other_ac}">{other_ac}</option>'
                html += f'</select></div></div>'
        else:
            html += '<div style="color:#adb5bd; text-align:center; padding:12px 0;">—</div>'
        
        html += '</div></td>'
    
    html += '</tr>'

html += '</table>'

st.markdown(html, unsafe_allow_html=True)

# ---------- 调机计划编辑区域 ----------
st.markdown("---")
st.markdown("### 🔄 调机计划管理")

ferry_plans = [p for p in st.session_state.plans if p.is_ferry]
if ferry_plans:
    cols = st.columns(3)
    for i, fp in enumerate(ferry_plans):
        with cols[i % 3]:
            with st.expander(f"调机 {fp.id} - {fp.aircraft} {fp.date} {fp.start}-{fp.end}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_start = st.text_input("起飞时间", fp.start, key=f"start_{fp.id}")
                    new_dep = st.text_input("起飞机场", fp.dep_apt, key=f"dep_{fp.id}")
                with col2:
                    new_end = st.text_input("落地时间", fp.end, key=f"end_{fp.id}")
                    new_arr = st.text_input("落地机场", fp.arr_apt, key=f"arr_{fp.id}")
                
                if st.button("更新", key=f"update_{fp.id}", use_container_width=True):
                    if new_start != fp.start or new_end != fp.end:
                        if check_conflict(st.session_state.plans, fp.aircraft, fp.date, new_start, new_end, exclude_id=fp.id):
                            st.error("时间冲突，更新失败")
                        else:
                            fp.start = new_start
                            fp.end = new_end
                            fp.dep_apt = new_dep
                            fp.arr_apt = new_arr
                            st.success("已更新")
                            st.rerun()
                    else:
                        fp.dep_apt = new_dep
                        fp.arr_apt = new_arr
                        st.success("机场已更新")
                        st.rerun()
else:
    st.info("暂无调机计划")

# ---------- 底部：数据统计与导出 ----------
with st.expander("📋 所有计划列表"):
    df = pd.DataFrame([p.to_dict() for p in st.session_state.plans])
    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("📌 蓝色：载客计划 · 红色：调机计划（带F）· 每个计划下方可选飞机（演示功能）")
