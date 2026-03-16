import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from PIL import Image
import pytesseract
import io

st.set_page_config(layout="wide", page_title="公务机飞行计划")

AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]
DATES = ["03-15", "03-16", "03-17", "03-18", "03-19", "03-20", "03-21"]
DATE_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

if 'id_counter' not in st.session_state:
    st.session_state.id_counter = 1000

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

# 辅助函数（简化版，只用于获取每日计划）
def time_to_minutes(t):
    h, m = map(int, t.split(':'))
    return h*60 + m

# ---------- 构建表格 ----------
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
        background-color: white;
    }
    .aircraft-header {
        background-color: #e9ecef;
        font-weight: 600;
        text-align: center;
        vertical-align: middle !important;
        color: #212529;
        width: 80px;
    }
    .plan-block {
        padding: 6px 8px;
        margin: 4px 0;
        font-size: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        border-left: 4px solid;
    }
    .ferry {
        background-color: #ffebee;
        border-left-color: #f44336;
    }
    .passenger {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
</style>
""", unsafe_allow_html=True)

html = '<table class="excel-table"><tr><th>飞机/日期</th>'
for i, label in enumerate(DATE_LABELS):
    html += f'<th>{label}<br><span style="font-weight:normal;">{DATES[i]}</span></th>'
html += '</tr>'

for ac in AIRCRAFT:
    html += f'<tr><td class="aircraft-header">{ac}</td>'
    for date in DATES:
        html += '<td><div style="display:flex; flex-direction:column; gap:4px;">'
        day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
        day_plans.sort(key=lambda x: x.start)
        if day_plans:
            for p in day_plans:
                cls = "ferry" if p.is_ferry else "passenger"
                f_tag = ' <span style="color:#f44336; font-weight:bold;">F</span>' if p.is_ferry else ''
                html += f'''
                <div class="plan-block {cls}">
                    <strong>{p.start}-{p.end}</strong>{f_tag}<br>
                    <span style="color:#555;">{p.dep_apt}→{p.arr_apt}</span>
                </div>
                '''
        else:
            html += '<div style="color:#adb5bd; text-align:center; padding:12px 0;">—</div>'
        html += '</div></td>'
    html += '</tr>'
html += '</table>'

st.markdown(html, unsafe_allow_html=True)
st.write("如果看到彩色计划块，说明计划渲染正常。")
