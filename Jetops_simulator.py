import streamlit as st

st.set_page_config(layout="wide", page_title="公务机飞行计划")

AIRCRAFT = ["B652Q", "B652R", "B652S", "N440QS", "T73338", "N88AY", "MLLIN", "N/A"]
DATES = ["03-15", "03-16", "03-17", "03-18", "03-19", "03-20", "03-21"]
DATE_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

# 构建一个空表格（所有单元格都是 "—"）
html = '<table style="border-collapse:collapse; width:100%; border:1px solid #ddd;">'
html += '<tr><th style="border:1px solid #ddd; padding:8px;">飞机/日期</th>'
for label, date in zip(DATE_LABELS, DATES):
    html += f'<th style="border:1px solid #ddd; padding:8px;">{label}<br>{date}</th>'
html += '</tr>'

for ac in AIRCRAFT:
    html += '<tr>'
    html += f'<td style="border:1px solid #ddd; padding:8px; background:#e9ecef;"><strong>{ac}</strong></td>'
    for _ in DATES:
        html += '<td style="border:1px solid #ddd; padding:8px; text-align:center;">—</td>'
    html += '</tr>'
html += '</table>'

st.markdown(html, unsafe_allow_html=True)
st.write("如果看到表格，说明 HTML 渲染正常。")
