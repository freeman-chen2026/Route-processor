import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(layout="wide", page_title="公务机飞行计划")

# 飞机列表（按指定顺序）
AIRCRAFT = ["B652Q", "B652R", "B652S", "MLLIN", "N440QS", "N88AY", "T73338", "N/A"]

# ---------- 动态生成日期（从今天开始，连续7天）----------
today = datetime.now().date()
date_objects = [today + timedelta(days=i) for i in range(7)]
DATES = [d.strftime("%m-%d") for d in date_objects]
weekday_map = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
    "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
}
DATE_LABELS = [weekday_map[d.strftime("%A")] for d in date_objects]

# 机场四字码 -> 中文名称映射（可扩展）
AIRPORT_MAP = {
    "VDTI": "柬埔寨金边德崇",
    "WSSL": "新加坡实里达",
    "VVCR": "越南金兰",
    "WMSA": "马来西亚吉隆坡梳邦",
    "VHHH": "香港",
    "ZSHC": "杭州萧山",
    "ZSSS": "上海虹桥",
    "ZBAA": "北京首都",
    "RJTT": "日本东京羽田",
    "ZBTJ": "天津滨海",
    "VTSP": "泰国普吉",
    "VLVT": "老挝万象",
    "ZUCK": "重庆江北",
    "ZGSZ": "深圳宝安",
    "VMMC": "澳门",
    "VVTS": "越南胡志明市",
    "RCMQ": "台中清泉岗",
    "RPLL": "菲律宾马尼拉",
    "ZGGG": "广州白云",
    "ZSQZ": "泉州晋江",
    "ZSPD": "上海浦东",
    "PANC": "美国安克雷奇史蒂文斯",
    "KSFO": "美国旧金山",
    "NZQN": "新西兰皇后镇",
    "WAMM": "印尼万鸦老",
    "WAMP": "印尼莫罗瓦利工业园",
    "WAEH": "印尼韦达港",
    "VTCC": "泰国清迈",
    "ZHCC": "郑州新郑",
    "ZJSY": "三亚凤凰",
    "ZSNB": "宁波栎社",
    "ZBAD": "北京大兴",
    "ZGNN": "南宁吴圩",
    "ZPPP": "昆明长水",
    "ZUUU": "成都双流",
    "ZUCK": "重庆江北",
    "ZGSZ": "深圳宝安",
    "ZGGG": "广州白云",
    "ZSHC": "杭州萧山",
    "ZSNJ": "南京禄口",
    "ZSOF": "合肥新桥",
    "ZSQD": "青岛胶东",
    "ZSYT": "烟台蓬莱",
    "ZBTJ": "天津滨海",
    "ZBSJ": "石家庄正定",
    "ZBYN": "太原武宿",
    "ZBCF": "长春龙嘉",
    "ZYHB": "哈尔滨太平",
    "ZYTL": "大连周水子",
    "ZYJM": "佳木斯东郊",
    "ZYTX": "沈阳桃仙",
    "ZHHH": "武汉天河",
    "ZGHA": "长沙黄花",
    "ZSCN": "南昌昌北",
    "ZSFZ": "福州长乐",
    "ZSAM": "厦门高崎",
    "ZGSZ": "深圳宝安",
    "ZGKL": "桂林两江",
    "ZJHK": "海口美兰",
    "ZJQH": "琼海博鳌",
    "ZJSY": "三亚凤凰",
    "ZWWW": "乌鲁木齐地窝堡",
    "ZLLL": "兰州中川",
    "ZLXY": "西安咸阳",
    "ZLIC": "银川河东",
    "ZLHZ": "汉中城固",
    "ZLXN": "西宁曹家堡",
    "ZULS": "拉萨贡嘎",
    "ZPPP": "昆明长水",
    "ZUCK": "重庆江北",
    "ZUUU": "成都双流",
    "ZUMY": "绵阳南郊",
    "ZUWX": "无锡硕放",
    "ZSNB": "宁波栎社",
    "ZSNJ": "南京禄口",
    "ZSOF": "合肥新桥",
    "ZSQD": "青岛胶东",
    "ZSYN": "盐城南洋",
    "ZSYT": "烟台蓬莱",
    "ZSJG": "济宁曲阜",
    "ZSLG": "连云港白塔埠",
    "ZSPD": "上海浦东",
    "ZSSS": "上海虹桥",
    "ZSTX": "黄山屯溪",
    "ZSWZ": "温州龙湾",
    "ZSXZ": "徐州观音",
    "ZSYW": "义乌",
    "ZSYN": "盐城",
    "ZSYC": "宜春明月山",
    "ZSYY": "烟台",
    "ZSZJ": "湛江",
    "ZSZS": "舟山普陀山",
}

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
    """从DataFrame解析计划，返回候选计划列表（针对用户提供的Excel格式优化）"""
    # 去除列名中的首尾空格
    df.columns = df.columns.astype(str).str.strip()
    col_names = list(df.columns)
    st.write("检测到的列名（已去除空格）：", col_names)

    # 所需列的关键字匹配
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
        
        dep_code = str(row[matched_cols['出发地']]).strip()
        arr_code = str(row[matched_cols['到达地']]).strip()
        # 映射为中文名称
        dep = AIRPORT_MAP.get(dep_code, dep_code)
        arr = AIRPORT_MAP.get(arr_code, arr_code)
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
    st.header("📊 上传Excel自动解析")
    uploaded_excel = st.file_uploader("选择Excel文件（.xlsx）", type=['xlsx'])
    
    if uploaded_excel is not None:
        try:
            df = pd.read_excel(uploaded_excel, header=1)
            st.success(f"成功读取Excel，共 {len(df)} 行")
            
            if st.button("解析并导入", width='stretch'):
                candidates = parse_excel(df)
                if not candidates:
                    st.warning("未解析出任何计划，请检查文件格式")
                else:
                    added = 0
                    conflicts = []
                    for cand in candidates:
                        # 自动匹配日期：如果原始日期在当前7天内则使用，否则默认今天
                        if cand['date_original'] in DATES:
                            target_date = cand['date_original']
                        else:
                            target_date = DATES[0]
                        # 检查冲突
                        if check_conflict(st.session_state.plans, cand['aircraft'], target_date, cand['start'], cand['end']):
                            conflicts.append(f"{cand['aircraft']} {cand['start']}-{cand['end']} {cand['dep']}-{cand['arr']} ({cand['date_original']})")
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
                    st.success(f"成功添加 {added} 个计划")
                    st.rerun()
        except Exception as e:
            st.error(f"读取Excel失败：{e}")

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

# ---------- 日历网格（带隐藏调机计划功能和飞机切换）----------
# 使用两列布局：左侧放标题，右侧放统计信息（段数+时间）
title_col, stats_col = st.columns([2, 1])
with title_col:
    st.write("## 飞行计划日历")
with stats_col:
    # 计算7天内所有调机计划的飞行时间总和
    ferry_plans_7d = [p for p in st.session_state.plans if p.is_ferry and p.date in DATES]
    ferry_total_minutes = 0
    for p in ferry_plans_7d:
        ferry_total_minutes += (time_to_minutes(p.end) - time_to_minutes(p.start))
    ferry_hours = ferry_total_minutes // 60
    ferry_minutes = ferry_total_minutes % 60
    ferry_segments = len(ferry_plans_7d)
    
    # 计算7天内所有载客计划的飞行时间总和
    pax_plans_7d = [p for p in st.session_state.plans if not p.is_ferry and p.date in DATES]
    pax_total_minutes = 0
    for p in pax_plans_7d:
        pax_total_minutes += (time_to_minutes(p.end) - time_to_minutes(p.start))
    pax_hours = pax_total_minutes // 60
    pax_minutes = pax_total_minutes % 60
    pax_segments = len(pax_plans_7d)
    
    st.markdown(f"""
    <div style='background-color:#f0f0f0; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>
        <div>调机: {ferry_segments}段, {ferry_hours}小时{ferry_minutes}分钟</div>
        <div style='margin-top:5px;'>载客: {pax_segments}段, {pax_hours}小时{pax_minutes}分钟</div>
    </div>
    """, unsafe_allow_html=True)

# 隐藏调机计划复选框
hide_ferry = st.checkbox("隐藏调机计划", value=False)

# 增强表格边框的CSS
st.markdown("""
<style>
    .plan-grid {
        border-collapse: collapse;
        width: 100%;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    .plan-grid th {
        background-color: #f2f2f2;
        border: 2px solid #aaa;
        padding: 10px 8px;
        text-align: center;
        font-weight: 600;
    }
    .plan-grid td {
        border: 2px solid #aaa;
        padding: 8px;
        vertical-align: top;
        background-color: white;
    }
    .aircraft-header {
        background-color: #e6e6e6;
        font-weight: 600;
        text-align: center;
        vertical-align: middle !important;
        border: 2px solid #aaa;
    }
</style>
""", unsafe_allow_html=True)

# 构建表头
cols = st.columns([1] + [1]*len(DATES))
with cols[0]:
    st.markdown("**飞机/日期**")
for i, label in enumerate(DATE_LABELS):
    with cols[i+1]:
        st.markdown(f"**{label}**<br><span style='font-weight:normal'>{DATES[i]}</span>", unsafe_allow_html=True)

# 为每架飞机生成行（按新的顺序）
for ac in AIRCRAFT:
    row_cols = st.columns([1] + [1]*len(DATES))
    with row_cols[0]:
        st.markdown(f"**{ac}**")
    for i, date in enumerate(DATES):
        with row_cols[i+1]:
            # 获取该飞机该日的所有计划，并根据hide_ferry过滤调机计划
            day_plans = [p for p in st.session_state.plans if p.aircraft == ac and p.date == date]
            if hide_ferry:
                day_plans = [p for p in day_plans if not p.is_ferry]
            day_plans.sort(key=lambda x: x.start)
            if day_plans:
                for p in day_plans:
                    # 显示计划块
                    st.markdown(plan_block_html(p), unsafe_allow_html=True)
                    
                    # 飞机切换下拉框（启用）
                    options = [ac] + [a for a in AIRCRAFT if a != ac]
                    selected_ac = st.selectbox(
                        "✈️",
                        options,
                        index=0,
                        key=f"move_{p.id}",
                        label_visibility="collapsed"
                    )
                    # 如果用户选择了不同的飞机
                    if selected_ac != ac:
                        # 检查目标飞机是否有冲突（排除自身）
                        conflict = False
                        if selected_ac != "N/A":
                            conflict = check_conflict(st.session_state.plans, selected_ac, p.date, p.start, p.end, exclude_id=p.id)
                        if conflict:
                            st.error(f"时间冲突，不能移动到 {selected_ac}")
                        else:
                            # 更新计划所属飞机
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
st.caption("📌 使用说明：上传Excel后点击“解析并导入”，系统自动匹配日期（原始日期在7天内则自动对应，否则放入今天），并添加所有计划。支持手动添加单条计划。调机计划以红色背景显示，可勾选“隐藏调机计划”简化视图。点击计划下方的✈️下拉框可将计划移动到其他飞机（自动检测时间冲突）。右上角显示7天内调机和载客计划的段数及飞行时间总和。")
