import re
import streamlit as st
import traceback
import time

# ===================== 原核心航路处理代码（完全未动） =====================
def parse_coord(coord_str):
    letter = coord_str[0]
    num_part = coord_str[1:]
    if letter == 'N':
        deg = int(num_part[0:2])
        minute = int(num_part[2:4])
        sec_part = num_part[4:]
        if '.' in sec_part:
            sec_float = float(sec_part)
            sec_int = int(round(sec_float))
        else:
            sec_int = int(sec_part)
        if sec_int >= 60:
            sec_int -= 60
            minute += 1
            if minute >= 60:
                minute -= 60
                deg += 1
        return f"{deg:02d}{minute:02d}{sec_int:02d}"
    elif letter == 'E':
        deg = int(num_part[0:3])
        minute = int(num_part[3:5])
        sec_part = num_part[5:]
        if '.' in sec_part:
            sec_float = float(sec_part)
            sec_int = int(round(sec_float))
        else:
            sec_int = int(sec_part)
        if sec_int >= 60:
            sec_int -= 60
            minute += 1
            if minute >= 60:
                minute -= 60
                deg += 1
        return f"{deg:03d}{minute:02d}{sec_int:02d}"
    else:
        raise ValueError(f"未知的坐标前缀: {letter}")

def base_name(s):
    return s.split('@')[0]

def is_open_point(s):
    base = base_name(s)
    if re.match(r'^[A-Z]{2,5}$', base):
        return True
    if re.match(r'^P[A-Z]+$', base):
        return True
    return False

def is_p_point(s):
    base = base_name(s)
    return re.match(r'^P\d+$', base) is not None

def clean_route(r):
    if r.startswith('#'):
        return r[1:]
    return r

def is_open_route(rt):
    return rt and rt[0] not in ('H', 'J', 'V')

def extract_table(text):
    tokens = text.strip().split()
    start_idx = 0
    for i, tok in enumerate(tokens):
        if tok.isdigit() and 1 <= int(tok) <= 40:
            start_idx = i
            break
    tokens = tokens[start_idx:]
    lines = []
    i = 0
    while i < len(tokens):
        if tokens[i].isdigit():
            line = [tokens[i]]
            i += 1
            while i < len(tokens) and not tokens[i].isdigit():
                line.append(tokens[i])
                i += 1
            lines.append(line)
    points = []
    routes = []
    for line in lines:
        lat_idx = None
        for idx, tok in enumerate(line):
            if tok.startswith('N') and tok[1:].replace('.', '', 1).isdigit():
                lat_idx = idx
                break
        if lat_idx is None:
            continue
        lon_idx = lat_idx + 1
        if lon_idx >= len(line) or not line[lon_idx].startswith('E'):
            continue
        lat_str = line[lat_idx]
        lon_str = line[lon_idx]
        route = None
        if lon_idx + 1 < len(line):
            next_tok = line[lon_idx + 1]
            if re.match(r'^[A-Z][A-Z0-9]*$', next_tok) and not next_tok[0].isdigit():
                route = next_tok
        point_name = None
        for j in range(lat_idx - 1, 0, -1):
            tok = line[j]
            if is_open_point(tok) or is_p_point(tok):
                point_name = tok
                break
        if point_name is None:
            continue
        if is_p_point(point_name):
            lat_int = parse_coord(lat_str)
            lon_int = parse_coord(lon_str)
            point_display = f"{point_name}@{lat_int}N{lon_int}E"
        else:
            point_display = point_name
        points.append(point_display)
        if route is not None:
            routes.append(route)
    seq = []
    for i in range(len(points)):
        seq.append(points[i])
        if i < len(routes):
            seq.append(routes[i])
    return seq

def extract_chinese(text):
    text = re.sub(r'[\u4e00-\u9fa5，、。；：""''（）【】]', ' ', text)
    words = text.split()
    seq = []
    for w in words:
        if '(' in w and ')' in w:
            m = re.search(r'\(([A-Z]+)\)', w)
            if m:
                point = m.group(1)
                prefix = w[:w.find('(')]
                m_route = re.search(r'([A-Z]\d+)$', prefix)
                if m_route:
                    seq.append(m_route.group(1))
                seq.append(point)
        elif re.match(r'^[A-Z]\d+[A-Z]{2,5}$', w) or re.match(r'^[A-Z]\d+P\d+$', w):
            m = re.match(r'^([A-Z]\d+)([A-Z]{2,5}|P\d+)$', w)
            if m:
                seq.append(m.group(1))
                seq.append(m.group(2))
        elif re.match(r'^[A-Z]\d+$', w):
            seq.append(w)
        elif is_open_point(w) or is_p_point(w):
            seq.append(w)
    return seq

def step1_extract(text):
    if re.search(r'N\d{5,6}(?:\.\d+)?\s+E\d{6,7}(?:\.\d+)?', text):
        return extract_table(text), 'table'
    else:
        return extract_chinese(text), 'chinese'

def step2_reduce(seq):
    L = seq[:]
    changed = True
    while changed:
        changed = False
        n = len(L)
        candidates = []
        for i in range(0, n, 2):
            if not is_open_point(L[i]):
                continue
            if i + 1 >= n:
                continue
            first_route = clean_route(L[i+1])
            if not is_open_route(first_route):
                continue
            for j in range(i+2, n, 2):
                all_same = True
                for k in range(i+1, j, 2):
                    rt = clean_route(L[k])
                    if rt != first_route or not is_open_route(rt):
                        all_same = False
                        break
                if not all_same:
                    break
                if is_open_point(L[j]):
                    length = (j - i) // 2
                    if length >= 2:
                        candidates.append((i, j, length))
        if not candidates:
            break
        candidates.sort(key=lambda x: -x[2])
        best_i, best_j, _ = candidates[0]
        new_segment = [L[best_i], L[best_i+1], L[best_j]]
        L = L[:best_i] + new_segment + L[best_j+1:]
        changed = True
    return L

def step3_add_hash(seq):
    pts = seq[0::2]
    rts = seq[1::2]
    m = len(rts)
    def is_closed_route(rt):
        return rt.startswith(('H', 'J', 'V'))
    def is_p(pt):
        base = base_name(pt)
        return re.match(r'^P\d+$', base) is not None
    res = [pts[0]]
    for i, rt in enumerate(rts):
        left = pts[i]
        right = pts[i+1]
        need_hash = False
        if is_closed_route(rt):
            need_hash = True
        elif is_p(left) or is_p(right):
            need_hash = True
        res.append('#' + rt if need_hash else rt)
        res.append(right)
    return res

# ===================== 最终修复版界面代码 =====================
st.set_page_config(
    page_title="航路文本处理工具",
    page_icon="✈️",
    layout="wide"
)

# 仅保留必要的CSS，避免冲突
st.markdown("""
    <style>
    .stButton>button {margin-right: 0.5rem; margin-bottom: 0.5rem; border-radius: 6px;}
    .stTextArea {margin-bottom: 0.8rem;}
    </style>
""", unsafe_allow_html=True)

st.title("✈️ 民航航路文本处理工具")
st.caption("支持表格格式（带N/E坐标）/中文描述格式，自动精简航路+添加#前缀")

# 初始化session_state（核心修复：提前初始化，避免渲染冲突）
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "result_text" not in st.session_state:
    st.session_state.result_text = ""

# 输入区域（核心修复：用key绑定，确保状态同步）
input_text = st.text_area(
    "📋 请输入待处理的航路文本",
    value=st.session_state.input_text,
    height=250,
    key="input_area",
    placeholder="粘贴民航航线数据，支持多行表格格式/纯中文描述格式..."
)

# 按钮区域（核心修复：调整列比例，避免按钮挤压）
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 3])
with btn_col1:
    process_btn = st.button("⚙️ 开始处理", type="primary", use_container_width=True)
with btn_col2:
    clear_btn = st.button("🗑️ 清空输入", use_container_width=True)
with btn_col3:
    # 核心修复：复制按钮仅在结果非空时激活，逻辑更严谨
    copy_btn = st.button(
        "📌 复制结果",
        use_container_width=True,
        disabled=not bool(st.session_state.result_text.strip())
    )

# 清空按钮逻辑（核心修复：先更新input_text，再rerun，确保输入框同步）
if clear_btn:
    st.session_state.input_text = ""
    st.session_state.result_text = ""
    st.rerun()

# 复制按钮逻辑（核心修复：用Streamlit原生code块+提示，无JS，百分百兼容）
if copy_btn:
    st.success("✅ 已为你选中结果，直接复制即可！")
    st.code(st.session_state.result_text, language="text")

# 处理逻辑
if process_btn and input_text.strip():
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_steps = 4
    current_step = 0

    try:
        current_step +=1
        progress_bar.progress(current_step/total_steps)
        status_text.text(f"处理中：第{current_step}步（识别输入类型）")
        time.sleep(0.2)
        seq, fmt = step1_extract(input_text)

        current_step +=1
        progress_bar.progress(current_step/total_steps)
        status_text.text(f"处理中：第{current_step}步（精简相同开放航路）")
        time.sleep(0.2)
        if fmt == 'table':
            seq = step2_reduce(seq)

        current_step +=1
        progress_bar.progress(current_step/total_steps)
        status_text.text(f"处理中：第{current_step}步（添加航路#前缀）")
        time.sleep(0.2)
        if fmt == 'table':
            seq = step3_add_hash(seq)

        current_step +=1
        progress_bar.progress(current_step/total_steps)
        status_text.text(f"处理中：第{current_step}步（生成最终结果）")
        time.sleep(0.2)
        st.session_state.result_text = ' '.join(seq) if seq else "⚠️ 未提取到有效航路数据"
        st.session_state.input_text = input_text  # 保存当前输入

        progress_bar.empty()
        status_text.empty()
        st.success("✅ 处理完成！结果如下：")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 处理失败：{str(e)}")
        with st.expander("🔍 查看详细错误", expanded=False):
            st.code(traceback.format_exc(), language="text")

# 结果输出区域
if st.session_state.result_text:
    st.subheader("📊 处理结果", divider="blue")
    st.text_area(
        "结果展示",
        value=st.session_state.result_text,
        height=150,
        disabled=True,
        key="result_area"
    )

# 空输入提示
if not input_text.strip() and not process_btn:
    st.info("💡 提示：粘贴航路数据后，点击「开始处理」即可")
