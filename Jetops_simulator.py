import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="公务机飞行计划")

# 飞机列表（含N/A）
AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]
# 日期范围
DATES = ["03-15", "03-16", "03-17", "03-18", "03-19", "03-20", "03-21"]
DATE_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

# ---------- 计划数据（和之前一样）----------
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

# 辅助函数：生成计划块的 HTML（确保标签正确闭合）
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

# ---------- 构建日历网格 ----------
st.write("## 飞行计划日历")

# 第一行：日期标题
cols = st.columns([1] + [1]*len(DATES))  # 第一列宽一点放飞机名
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
                    st.markdown(plan_block_html(p), unsafe_allow_html=True)
            else:
                st.markdown("<div style='color:#adb5bd; text-align:center; padding:12px 0;'>—</div>", unsafe_allow_html=True)

st.write("如果看到彩色计划块且排列整齐，说明日历网格渲染成功。")
