import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from PIL import Image
import pytesseract
import io

# ---------- 配置 ----------
st.set_page_config(layout="wide", page_title="公务机飞行计划模拟")
st.title("✈️ 公务机飞行计划模拟 (拖拽模拟版)")

# 飞机列表（含N/A）
AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]
# 日期范围（基于截图：03-15 ~ 03-21）
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
        self.date = date  # MM-DD
        self.start = start  # HH:MM
        self.end = end      # HH:MM
        self.dep_apt = dep_apt
        self.arr_apt = arr_apt
        self.plan_type = plan_type  # 'passenger' or 'ferry'
        self.crew = crew
        self.is_ferry = is_ferry   # 调机计划红色F

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
    # 添加一些示例计划（基于截图）
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
                return True  # 冲突
    return False

def render_plan_block(plan):
    """返回计划显示的HTML块（简化）"""
    color = "#ffcccc" if plan.is_ferry else "#d4edda"
    f_tag = " <b style='color:red'>F</b>" if plan.is_ferry else ""
    return f"<div style='background:{color}; padding:5px; margin:2px; border-radius:4px; font-size:12px;'>{plan.start}-{plan.end}<br>{plan.dep_apt}→{plan.arr_apt}{f_tag}</div>"

def parse_ocr_text(text):
    """简单OCR文本解析，提取航班信息"""
    lines = text.split('\n')
    plans = []
    # 正则示例：B652Q07:00-09:00 韩国首尔金浦-北京首都
    pattern = r'([A-Z0-9]+)(\d{2}:\d{2})-(\d{2}:\d{2})\s+([^-]+)-(.+)'
    for line in lines:
        match = re.search(pattern, line)
        if match:
            aircraft = match.group(1)
            start = match.group(2)
            end = match.group(3)
            dep = match.group(4).strip()
            arr = match.group(5).strip()
            # 日期需要额外逻辑，这里默认今天，实际可让用户选择
            plans.append({
                'aircraft': aircraft,
                'start': start,
                'end': end,
                'dep': dep,
                'arr': arr
            })
    return plans

# ---------- 侧边栏：截图识别 & 手动添加 ----------
with st.sidebar:
    st.header("📸 截图识别")
    uploaded_file = st.file_uploader("上传航班计划截图", type=['png','jpg','jpeg'])
    use_mock = st.checkbox("使用模拟识别（不依赖OCR）", value=True)
    if st.button("识别并生成计划"):
        if uploaded_file is not None and not use_mock:
            # 真实OCR
            image = Image.open(uploaded_file)
            try:
                text = pytesseract.image_to_string(image, lang='eng')
                st.write("OCR识别结果：", text)
                parsed = parse_ocr_text(text)
                for item in parsed:
                    # 默认放在对应飞机下，日期取今天（示例）
                    new_plan = FlightPlan(
                        pid=get_next_id(),
                        aircraft=item['aircraft'],
                        date=DATES[0],  # 默认第一天
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
            # 模拟识别：生成几个示例计划
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
            ac = st.selectbox("飞机", AIRCRAFT, index=7)  # 默认N/A
            date_idx = st.selectbox("日期", range(7), format_func=lambda x: f"{DATE_LABELS[x]} {DATES[x]}")
            start = st.text_input("起飞时间 (HH:MM)", "08:00")
            dep = st.text_input("起飞机场", "北京首都")
        with col2:
            is_ferry = st.checkbox("调机计划 (红色F)")
            end = st.text_input("落地时间 (HH:MM)", "10:00")
            arr = st.text_input("落地机场", "上海虹桥")
        submitted = st.form_submit_button("添加计划")
        if submitted:
            # 简单格式校验
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
                # 冲突检测（若飞机不是N/A）
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

# ---------- 主界面：日历网格 ----------
st.header("📅 飞行计划日历")

# 构建表格头部
header_cols = st.columns([1] + [1 for _ in DATES])
with header_cols[0]:
    st.markdown("**飞机/日期**")
for i, label in enumerate(DATE_LABELS):
    with header_cols[i+1]:
        st.markdown(f"**{label} {DATES[i]}**")

# 为每架飞机生成一行
for ac in AIRCRAFT:
    row_cols = st.columns([1] + [1 for _ in DATES])
    with row_cols[0]:
        st.markdown(f"**{ac}**")
    for i, date in enumerate(DATES):
        with row_cols[i+1]:
            # 获取该飞机该日的所有计划，按开始时间排序
            day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
            day_plans.sort(key=lambda x: x.start)
            # 显示每个计划块
            for p in day_plans:
                # 每个计划下方放置一个更改飞机的下拉框
                cols = st.columns([3,1])
                with cols[0]:
                    st.markdown(render_plan_block(p), unsafe_allow_html=True)
                with cols[1]:
                    # 使用selectbox更改飞机
                    new_ac = st.selectbox(
                        "✈️", 
                        AIRCRAFT, 
                        index=AIRCRAFT.index(p.aircraft) if p.aircraft in AIRCRAFT else 7,
                        key=f"move_{p.id}",
                        label_visibility="collapsed"
                    )
                    if new_ac != p.aircraft:
                        # 检查冲突（目标飞机不是N/A时需要检测）
                        conflict = False
                        if new_ac != "N/A":
                            conflict = check_conflict(st.session_state.plans, new_ac, p.date, p.start, p.end, exclude_id=p.id)
                        if conflict:
                            st.error("时间冲突，不能移动")
                        else:
                            # 更新飞机
                            p.aircraft = new_ac
                            st.rerun()
            if not day_plans:
                st.markdown("—")

# ---------- 调机计划编辑区域 ----------
st.header("🔄 调机计划管理")
st.markdown("点击下方调机计划方框可编辑时间（暂用输入框代替）")

ferry_plans = [p for p in st.session_state.plans if p.is_ferry]
if ferry_plans:
    for fp in ferry_plans:
        with st.expander(f"调机 {fp.id} - {fp.aircraft} {fp.date} {fp.start}-{fp.end}"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_start = st.text_input("起飞时间", fp.start, key=f"start_{fp.id}")
            with col2:
                new_end = st.text_input("落地时间", fp.end, key=f"end_{fp.id}")
            with col3:
                new_dep = st.text_input("起飞机场", fp.dep_apt, key=f"dep_{fp.id}")
            with col4:
                new_arr = st.text_input("落地机场", fp.arr_apt, key=f"arr_{fp.id}")
            if st.button("更新", key=f"update_{fp.id}"):
                # 检查冲突（如果更改了时间）
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
    st.dataframe(df)

# 说明
st.markdown("---")
st.caption("操作说明：\n1. 每个计划旁的‘✈️’下拉框可更改所属飞机，系统自动检测时间冲突。\n2. 调机计划以红色背景标识，可展开编辑时间。\n3. 截图识别支持模拟模式（默认勾选）。")
