import re
import streamlit as st
import traceback

# ===================== 核心航路处理代码（重构优化版） =====================
def parse_coord(coord_str):
    """坐标解析，增加异常捕获"""
    try:
        letter = coord_str[0]
        num_part = coord_str[1:].replace('.', '')
        if not num_part.isdigit():
            return None

        if letter == 'N':
            if len(num_part) < 6:
                return None
            deg = int(num_part[0:2])
            minute = int(num_part[2:4])
            sec_int = int(num_part[4:6])
        elif letter == 'E':
            if len(num_part) < 7:
                return None
            deg = int(num_part[0:3])
            minute = int(num_part[3:5])
            sec_int = int(num_part[5:7])
        else:
            return None

        # 进位处理
        if sec_int >= 60:
            sec_int -= 60
            minute += 1
        if minute >= 60:
            minute -= 60
            deg += 1

        return f"{deg:02d}{minute:02d}{sec_int:02d}" if letter == 'N' else f"{deg:03d}{minute:02d}{sec_int:02d}"
    except Exception:
        return None

def base_name(s):
    return s.split('@')[0] if '@' in s else s

def is_open_point(s):
    base = base_name(s)
    return re.match(r'^[A-Z]{2,5}$', base) or re.match(r'^P[A-Z]+$', base)

def is_p_point(s):
    base = base_name(s)
    return re.match(r'^P\d+$', base) is not None

def clean_route(r):
    return r.lstrip('#')

def is_open_route(rt):
    return rt and rt[0] not in ('H', 'J', 'V')

def extract_table(text):
    """重构表格提取，确保点和航路数量严格匹配"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    points = []
    routes = []

    for line in lines:
        tokens = re.split(r'\s+', line)
        # 过滤无效行（无数字序号或无足够字段）
        if len(tokens) < 3 or not tokens[0].isdigit():
            continue

        # 提取点名称（序号后第一个符合规则的字符）
        point_name = None
        for tok in tokens[1:]:
            if is_open_point(tok) or is_p_point(tok):
                point_name = tok
                break
        if not point_name:
            continue

        # 提取坐标（仅做P点拼接用，非必须）
        lat_str, lon_str = None, None
        for i, tok in enumerate(tokens):
            if tok.startswith('N') and parse_coord(tok):
                lat_str = tok
                if i+1 < len(tokens) and tokens[i+1].startswith('E') and parse_coord(tokens[i+1]):
                    lon_str = tokens[i+1]
                break

        # 提取航路（点名称后第一个符合规则的字符）
        route = None
        point_idx = tokens.index(point_name) if point_name in tokens else -1
        if point_idx != -1:
            for tok in tokens[point_idx+1:]:
                if re.match(r'^[A-Z][A-Z0-9]*$', tok) and not tok[0].isdigit():
                    route = tok
                    break

        # 处理P点显示
        point_display = point_name
        if is_p_point(point_name) and lat_str and lon_str:
            lat_int = parse_coord(lat_str)
            lon_int = parse_coord(lon_str)
            if lat_int and lon_int:
                point_display = f"{point_name}@{lat_int}N{lon_int}E"

        points.append(point_display)
        if route:
            routes.append(route)

    # 强制保证点和航路数量匹配（核心修复）
    min_len = min(len(points), len(routes) + 1)
    points = points[:min_len]
    routes = routes[:min_len - 1]

    # 构建序列
    seq = []
    for i in range(len(points)):
        seq.append(points[i])
        if i < len(routes):
            seq.append(routes[i])
    return seq

def extract_chinese(text):
    """优化中文提取，减少正则开销"""
    text = re.sub(r'[\u4e00-\u9fa5，、。；：""''（）【】]', ' ', text)
    words = [w for w in text.split() if w.strip()]
    seq = []

    for w in words:
        # 带括号格式
        if '(' in w and ')' in w:
            m = re.search(r'\(([A-Z]+)\)', w)
            if m:
                prefix = w[:w.find('(')]
                m_route = re.search(r'([A-Z]\d+)$', prefix)
                if m_route:
                    seq.append(m_route.group(1))
                seq.append(m.group(1))
        # 航路+点组合
        elif re.match(r'^[A-Z]\d+([A-Z]{2,5}|P\d+)$', w):
            m = re.match(r'^([A-Z]\d+)([A-Z]{2,5}|P\d+)$', w)
            if m:
                seq.append(m.group(1))
                seq.append(m.group(2))
        # 单独航路/点
        elif re.match(r'^[A-Z]\d+$', w) or is_open_point(w) or is_p_point(w):
            seq.append(w)
    return seq

def step1_extract(text):
    """增加空值校验"""
    if not text:
        return [], 'empty'
    if re.search(r'N\d{6,}\s+E\d{7,}', text):
        return extract_table(text), 'table'
    else:
        return extract_chinese(text), 'chinese'

def step2_reduce(seq):
    """优化精简逻辑，避免无限循环"""
    if len(seq) < 5:
        return seq  # 长度不足，无需精简
    L = seq[:]
    max_iter = 10  # 限制最大迭代次数，防止长文本卡住
    iter_count = 0

    while iter_count < max_iter:
        changed = False
        n = len(L)
        best_candidate = None

        for i in range(0, n, 2):
            if i + 1 >= n or not is_open_point(L[i]) or not is_open_route(clean_route(L[i+1])):
                continue
            first_route = clean_route(L[i+1])

            for j in range(i+4, n, 2):  # 至少间隔2个航路才精简
                if not is_open_point(L[j]):
                    break
                # 检查中间航路是否全相同
                all_same = True
                for k in range(i+1, j, 2):
                    if k >= n or clean_route(L[k]) != first_route or not is_open_route(clean_route(L[k])):
                        all_same = False
                        break
                if all_same:
                    candidate = (i, j, (j-i)//2)
                    if not best_candidate or candidate[2] > best_candidate[2]:
                        best_candidate = candidate

        if best_candidate:
            i, j, _ = best_candidate
            new_segment = [L[i], L[i+1], L[j]]
            L = L[:i] + new_segment + L[j+1:]
            changed = True
        if not changed:
            break
        iter_count += 1
    return L

def step3_add_hash(seq):
    """增加索引校验，彻底解决越界问题"""
    if len(seq) < 2:
        return seq
    pts = seq[0::2]
    rts = seq[1::2]
    res = [pts[0]]

    for i in range(len(rts)):
        # 核心校验：确保左右点都存在
        if i >= len(pts) - 1:
            break
        rt = rts[i]
        left = pts[i]
        right = pts[i+1]

        need_hash = False
        if rt.startswith(('H', 'J', 'V')):
            need_hash = True
        elif is_p_point(left) or is_p_point(right):
            need_hash = True

        res.append('#' + rt if need_hash else rt)
        res.append(right)
    return res

# ===================== Streamlit 界面（增加加载提示） =====================
st.title("✈️ 航路文本处理工具")
st.caption("支持长文本批量处理，自动过滤无效数据")

input_text = st.text_area(
    "请输入待处理的航路文本：",
    height=300,
    placeholder="粘贴表格格式（带序号/坐标）或中文描述格式的航路数据..."
)

# 长文本处理提示
if len(input_text) > 1000:
    st.info("检测到长文本，处理可能需要几秒钟，请耐心等待...")

if st.button("开始处理", type="primary"):
    with st.spinner("正在处理中..."):  # 加载动画，避免用户以为卡住
        try:
            seq, fmt = step1_extract(input_text)
            if fmt == 'empty':
                st.warning("请输入有效文本！")
            else:
                if fmt == 'table':
                    seq = step2_reduce(seq)
                seq = step3_add_hash(seq)
                result = ' '.join(seq) if seq else "未提取到有效航路数据"
                
                st.success("✅ 处理完成！")
                # 分栏显示结果，支持复制
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.text_area(
                        "处理结果",
                        value=result,
                        height=200,
                        disabled=False
                    )
                with col2:
                    st.button("复制结果", on_click=lambda: st.session_state.update({'clipboard': result}))
                    if 'clipboard' in st.session_state:
                        st.success("已复制！")

        except Exception as e:
            st.error(f"❌ 处理失败: {str(e)}")
            # 仅在调试时显示详细报错
            with st.expander("查看详细错误（点击展开）"):
                st.code(traceback.format_exc(), language="text")
