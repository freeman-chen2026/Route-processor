import re

def parse_coord(coord_str):
    """将坐标字符串（如 N252723.88 或 E1080859.53）转换为四舍五入后的整数部分，
    纬度返回6位数字，经度返回7位数字，自动处理进位。"""
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
    """返回点的基础名称（去掉@后面的部分）"""
    return s.split('@')[0]

def is_open_point(s):
    """判断是否为开放点（纯字母2-5位，或P后跟全字母）"""
    base = base_name(s)
    if re.match(r'^[A-Z]{2,5}$', base):
        return True
    if re.match(r'^P[A-Z]+$', base):
        return True
    return False

def is_p_point(s):
    """判断是否为不开放P点（P后跟数字）"""
    base = base_name(s)
    return re.match(r'^P\d+$', base) is not None

def clean_route(r):
    """去掉航路可能的#前缀（用于比较）"""
    if r.startswith('#'):
        return r[1:]
    return r

def is_open_route(rt):
    """判断是否为开放航路（不以 H/J/V 开头）"""
    return rt and rt[0] not in ('H', 'J', 'V')

# ---------- 表格格式提取 ----------
def extract_table(text):
    """处理带坐标的表格数据"""
    tokens = text.strip().split()
    # 找到第一个数字序号
    start_idx = 0
    for i, tok in enumerate(tokens):
        if tok.isdigit() and 1 <= int(tok) <= 40:
            start_idx = i
            break
    tokens = tokens[start_idx:]
    # 按序号分组
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
        # 找到纬度坐标
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
        # 航路（经度之后的下一个token）
        route = None
        if lon_idx + 1 < len(line):
            next_tok = line[lon_idx + 1]
            if re.match(r'^[A-Z][A-Z0-9]*$', next_tok) and not next_tok[0].isdigit():
                route = next_tok
        # 从纬度之前向前找点名称
        point_name = None
        for j in range(lat_idx - 1, 0, -1):
            tok = line[j]
            if is_open_point(tok) or is_p_point(tok):
                point_name = tok
                break
        if point_name is None:
            continue
        # 处理P点坐标
        if is_p_point(point_name):
            lat_int = parse_coord(lat_str)
            lon_int = parse_coord(lon_str)
            point_display = f"{point_name}@{lat_int}N{lon_int}E"
        else:
            point_display = point_name
        points.append(point_display)
        if route is not None:
            routes.append(route)
    # 构建点-航路交替序列
    seq = []
    for i in range(len(points)):
        seq.append(points[i])
        if i < len(routes):
            seq.append(routes[i])
    return seq

# ---------- 中文描述提取 ----------
def extract_chinese(text):
    """处理纯中文描述的航路数据（无坐标）"""
    # 将中文和中文标点替换为空格
    text = re.sub(r'[\u4e00-\u9fa5，、。；：""''（）【】]', ' ', text)
    words = text.split()
    seq = []
    for w in words:
        # 处理带括号的（如 R339南康VOR(BHY) -> R339 BHY）
        if '(' in w and ')' in w:
            m = re.search(r'\(([A-Z]+)\)', w)
            if m:
                point = m.group(1)
                prefix = w[:w.find('(')]
                m_route = re.search(r'([A-Z]\d+)$', prefix)
                if m_route:
                    seq.append(m_route.group(1))
                seq.append(point)
        # 处理航路+点组合（如 W285DUMAX）
        elif re.match(r'^[A-Z]\d+[A-Z]{2,5}$', w) or re.match(r'^[A-Z]\d+P\d+$', w):
            m = re.match(r'^([A-Z]\d+)([A-Z]{2,5}|P\d+)$', w)
            if m:
                seq.append(m.group(1))
                seq.append(m.group(2))
        # 单独航路
        elif re.match(r'^[A-Z]\d+$', w):
            seq.append(w)
        # 单独点
        elif is_open_point(w) or is_p_point(w):
            seq.append(w)
        # 其他忽略（如中文残留、无关英文）
    return seq

# ---------- 步骤1：根据输入类型提取 ----------
def step1_extract(text):
    """判断输入类型并提取点和航路，返回 (seq, format_type)"""
    # 检测是否有坐标模式（如 N332344 E1085114）
    if re.search(r'N\d{5,6}(?:\.\d+)?\s+E\d{6,7}(?:\.\d+)?', text):
        return extract_table(text), 'table'
    else:
        return extract_chinese(text), 'chinese'

# ---------- 步骤2：精简相同开放航路 ----------
def step2_reduce(seq):
    """精简相同开放航路连续且首尾开放点的段落"""
    L = seq[:]
    changed = True
    while changed:
        changed = False
        n = len(L)
        candidates = []  # (i, j, length)  length为航路数量
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

# ---------- 步骤3：添加#前缀（核心修复处） ----------
def step3_add_hash(seq):
    """为不开放航路和与P点相邻的航路添加#前缀"""
    # 边界处理：如果序列长度为1，直接返回
    if len(seq) == 1:
        return seq
    
    pts = seq[0::2]
    rts = seq[1::2]
    
    def is_closed_route(rt):
        return rt.startswith(('H', 'J', 'V'))
    
    def is_p(pt):
        base = base_name(pt)
        return re.match(r'^P\d+$', base) is not None
    
    res = [pts[0]]
    # 遍历rts，确保i+1永远小于pts长度
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
# ---------- 主程序 ----------
def main():
    # 请在这里输入你的文本（支持多行字符串）
    input_text = """


在这里输入

    """
    seq, fmt = step1_extract(input_text)
    if fmt == 'table':
        seq = step2_reduce(seq)
        seq = step3_add_hash(seq)
    # 中文描述直接输出提取结果
    print(' '.join(seq))

if __name__ == "__main__":
    main()

