# streamlit_app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ---------- 页面配置 ----------
st.set_page_config(page_title="飞行计划自动填报代码生成器", layout="wide")
st.title("✈️ 飞行计划自动填报代码生成器")
st.markdown("上传 Excel 文件，自动生成可直接在浏览器控制台运行的 JavaScript 代码")

# ---------- 城市映射表（与脚本保持一致） ----------
CITY_DETAIL_MAP = {
    # 境外城市 -> 国家名（直接用于第二个下拉框）
    "菲律宾马尼拉": "菲律宾",
    "马来西亚吉隆坡": "马来西亚",
    "日本东京": "日本",
    "新西兰皇后镇": "新西兰",
    "新西兰奥克兰": "新西兰",
    "香港": "香港",
    # 境内城市 -> (省份, 区县) 用于第三级下拉框
    "北京首都": ("北京", "顺义区"),
    "北京大兴": ("北京", "大兴区"),
    "天津滨海": ("天津", "滨海新区"),
    "上海虹桥": ("上海", "闵行区"),
    "上海浦东": ("上海", "浦东新区"),
    "重庆江北": ("重庆", "江北区"),
    "三亚凤凰": ("海南", "三亚"),
}

# 国内城市关键词（用于判断境内/境外）
DOMESTIC_KEYWORDS = [
    '北京', '上海', '广州', '深圳', '成都', '西安', '三亚', '重庆', '天津',
    '杭州', '南京', '武汉', '长沙', '郑州', '青岛', '大连', '厦门', '福州',
    '昆明', '贵阳', '南宁', '海口', '兰州', '西宁', '银川', '乌鲁木齐',
    '拉萨', '呼和浩特', '哈尔滨', '长春', '沈阳', '石家庄', '太原', '济南',
    '合肥', '南昌'
]

# ---------- 辅助函数 ----------
def parse_flight_time(time_str):
    """将 "HH:MM" 格式的时间字符串拆分为小时和分钟整数"""
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours, minutes
    except:
        return 0, 0

def map_city(city_name):
    """
    根据城市名返回境内/境外标识和具体值。
    返回格式: (zone, region, need_third, province, district)
    """
    # 1. 先检查是否在详细映射表中
    if city_name in CITY_DETAIL_MAP:
        value = CITY_DETAIL_MAP[city_name]
        if isinstance(value, tuple):
            # 境内城市，需要第三级
            province, district = value
            return "境内", province, True, province, district
        else:
            # 境外城市
            return "境外", value, False, None, None

    # 2. 根据关键词判断境内/境外
    is_domestic = any(kw in city_name for kw in DOMESTIC_KEYWORDS)
    if is_domestic:
        # 尝试提取城市名（取第一个词）
        region = city_name.split()[0]
        return "境内", region, True, region, None
    else:
        # 境外：取第一个词作为国家名
        country = city_name.split()[0]
        return "境外", country, False, None, None

def generate_js_script(df):
    """根据DataFrame生成JavaScript代码"""
    records = []
    for _, row in df.iterrows():
        # 处理用途：除“调机”外统一为“自用飞行”
        purpose_raw = row.get("用途", "")
        purpose = "调机" if "调机" in purpose_raw else "自用飞行"

        # 出发和到达日期（格式 YYYY-MM-DD）
        start_date = pd.to_datetime(row["出发日期"]).strftime("%Y-%m-%d")
        end_date = pd.to_datetime(row["到达日期"]).strftime("%Y-%m-%d")

        # 飞行时间
        flight_time = row.get("预计飞行时间", "")
        hours, minutes = parse_flight_time(flight_time)

        # 城市信息
        dep_city_raw = row["出发城市"]
        arr_city_raw = row["到达城市"]

        # 注册号处理（去除可能的横线）
        reg_raw = row["飞机注册号"]
        reg = reg_raw if '-' in reg_raw else reg_raw.replace('B', 'B-', 1) if reg_raw.startswith('B') else reg_raw

        record = {
            "reg": reg,
            "start_date": start_date,
            "end_date": end_date,
            "purpose": purpose,
            "dep_city": dep_city_raw,
            "arr_city": arr_city_raw,
            "flight_hours": hours,
            "flight_minutes": minutes
        }
        records.append(record)

    # 生成 JSON 字符串（格式化）
    records_json = json.dumps(records, ensure_ascii=False, indent=4)

    # 完整的 JavaScript 脚本模板（基于您最后调试成功的版本）
    script_template = f"""// ==================== 自动生成的飞行计划填报脚本 ====================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 总计 {len(records)} 条计划

// ==================== 获取最新 iframe 文档 ====================
async function getCurrentDoc() {{
    const iframe = document.querySelector('#main');
    if (!iframe) throw new Error('未找到 iframe');
    let doc = iframe.contentDocument;
    while (!doc || !doc.querySelector('body')) {{
        await sleep(200);
        doc = iframe.contentDocument;
    }}
    return doc;
}}

// ==================== 等待元素出现 ====================
async function waitForElement(selector, timeout = 15000, isXPath = false) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const doc = await getCurrentDoc();
        let el;
        if (isXPath) {{
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }} else {{
            el = doc.querySelector(selector);
        }}
        if (el) return el;
        await sleep(500);
    }}
    return null;
}}

// ==================== 弹窗确定按钮搜索 ====================
async function waitForDialogConfirmButton(timeout = 15000) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        let btn = document.evaluate('//a[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!btn) btn = document.evaluate('//button[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (btn) return btn;
        try {{
            const doc = await getCurrentDoc();
            btn = doc.evaluate('//a[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (!btn) btn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (btn) return btn;
        }} catch(e) {{}}
        await sleep(300);
    }}
    return null;
}}

// ==================== 确保在列表页 ====================
async function ensureListPage() {{
    const btn = await waitForElement('input.query.yuanjiao', 15000);
    if (btn) return true;
    console.log('当前不在列表页，尝试关闭可能遗留的对话框...');
    const doc = await getCurrentDoc();
    let closeBtn = doc.evaluate('//button[contains(text(), "取消")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "返回")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (closeBtn) {{
        closeBtn.click();
        console.log('已点击关闭按钮，等待返回列表页');
        await sleep(1000);
        const backBtn = await waitForElement('input.query.yuanjiao', 10000);
        return backBtn !== null;
    }} else {{
        console.warn('未找到返回按钮，请手动关闭对话框后继续（脚本将等待5秒）');
        await sleep(5000);
        const backBtn = await waitForElement('input.query.yuanjiao', 5000);
        return backBtn !== null;
    }}
}}

// ==================== 辅助函数 ====================
function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

async function setSelectValue(selectElement, valueText) {{
    for (let i = 0; i < selectElement.options.length; i++) {{
        const opt = selectElement.options[i];
        if (opt.text === valueText || opt.text.includes(valueText)) {{
            selectElement.selectedIndex = i;
            selectElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await sleep(300);
            return true;
        }}
    }}
    console.warn(`未找到选项: ${{valueText}}，可用选项：`, Array.from(selectElement.options).map(o => o.text));
    return false;
}}

function setDateInput(inputEl, dateStr) {{
    if (!inputEl) return false;
    inputEl.value = dateStr;
    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
    inputEl.blur();
    sleep(200);
    return true;
}}

// 境内城市详细映射表（自动生成，可根据需要补充）
const CITY_DETAIL_MAP = {json.dumps({k: list(v) if isinstance(v, tuple) else v for k, v in CITY_DETAIL_MAP.items()}, ensure_ascii=False, indent=4)};

async function fillSegmentSelects(container, city) {{
    const selects = container.querySelectorAll('select');
    if (selects.length < 2) {{
        console.warn('航段容器内 select 数量不足');
        return false;
    }}
    
    // 判断境内/境外
    let info = CITY_DETAIL_MAP[city];
    let isDomestic = false;
    let province = null, district = null;
    if (info && Array.isArray(info)) {{
        isDomestic = true;
        province = info[0];
        district = info[1];
    }} else if (info && typeof info === 'string') {{
        isDomestic = false;
    }} else {{
        // 降级处理
        const domesticKeywords = {json.dumps(DOMESTIC_KEYWORDS)};
        const isDom = domesticKeywords.some(kw => city.includes(kw));
        if (isDom) {{
            isDomestic = true;
            province = city.split()[0];
            district = null;
        }} else {{
            isDomestic = false;
            province = city.split()[0];
        }}
    }}
    
    if (!isDomestic) {{
        // 境外
        const country = (typeof info === 'string') ? info : province;
        await setSelectValue(selects[0], "境外");
        await setSelectValue(selects[1], country);
        return true;
    }}
    
    // 境内
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], province);
    
    if (selects.length >= 3 && district) {{
        // 等待1.5秒让第三个下拉框加载
        await sleep(1500);
        const newSelects = container.querySelectorAll('select');
        const thirdSelect = newSelects[2];
        // 查找匹配的区县
        let targetIndex = -1;
        for (let i = 0; i < thirdSelect.options.length; i++) {{
            if (thirdSelect.options[i].text.includes(district)) {{
                targetIndex = i;
                break;
            }}
        }}
        if (targetIndex !== -1) {{
            thirdSelect.selectedIndex = targetIndex;
            thirdSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            console.log(`已选择第三个下拉框: ${{thirdSelect.options[targetIndex].text}}`);
        }} else if (thirdSelect.options.length > 1) {{
            thirdSelect.selectedIndex = 1;
            thirdSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            console.log(`已选择第三个下拉框的第二个选项: ${{thirdSelect.options[1].text}}`);
        }}
    }}
    return true;
}}

// ==================== 航段填充封装 ====================
async function fillFirstSegmentSelects(city) {{
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div', 5000, true);
    if (!container) {{
        console.warn('未找到第一个航段容器');
        return false;
    }}
    return fillSegmentSelects(container, city);
}}

async function fillFirstSegmentTime(record) {{
    const hourInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[1]', 5000, true);
    const minuteInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[2]', 5000, true);
    const flightsInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[3]/div/input', 5000, true);
    if (hourInput && minuteInput && flightsInput) {{
        hourInput.value = record.flight_hours.toString().padStart(2, '0');
        minuteInput.value = record.flight_minutes.toString().padStart(2, '0');
        flightsInput.value = 1;
        hourInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        minuteInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        flightsInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log(`已填入第一个航段时间: ${{record.flight_hours}}:${{record.flight_minutes}}, 架次: 1`);
        return true;
    }}
    console.warn('无法填入第一个航段时间和架次');
    return false;
}}

async function fillSecondSegmentSelects(city) {{
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[1]/div/div', 5000, true);
    if (!container) {{
        console.warn('未找到第二个航段容器');
        return false;
    }}
    return fillSegmentSelects(container, city);
}}

async function fillSecondSegmentTime() {{
    const hourInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[1]', 5000, true);
    const minuteInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[2]', 5000, true);
    const flightsInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[3]/div/input', 5000, true);
    if (hourInput && minuteInput && flightsInput) {{
        hourInput.value = '00';
        minuteInput.value = '00';
        flightsInput.value = 0;
        hourInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        minuteInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        flightsInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log('已填入第二个航段时间: 00:00, 架次: 0');
        return true;
    }}
    console.warn('无法填入第二个航段时间和架次');
    return false;
}}

// ==================== 飞机选择 ====================
function formatRegNumber(reg) {{
    if (reg.includes('-')) return reg;
    const match = reg.match(/^([A-Z]+)(\\d+[A-Z]*)$/);
    if (match) return `${{match[1]}}-${{match[2]}}`;
    return reg;
}}

async function selectAircraft(reg) {{
    const regForSelect = formatRegNumber(reg);
    console.log(`尝试选择飞机: ${{regForSelect}}`);
    
    const airbox = await waitForElement('//*[@id="airbox"]', 10000, true);
    if (!airbox) {{
        console.warn('未找到飞机选择对话框');
        return false;
    }}
    const doc = await getCurrentDoc();
    
    let span = doc.evaluate(`//span[text()='${{regForSelect}}']`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!span) {{
        span = doc.evaluate(`//span[contains(text(), '${{regForSelect}}')]`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }}
    if (!span) {{
        console.warn(`未找到包含注册号 ${{regForSelect}} 的 span 元素`);
        return false;
    }}
    const li = span.closest('li');
    if (!li) {{
        console.warn(`未找到注册号 ${{regForSelect}} 对应的 li`);
        return false;
    }}
    const checkbox = li.querySelector('input[type="checkbox"]');
    if (!checkbox) {{
        console.warn(`未找到注册号 ${{regForSelect}} 的复选框`);
        return false;
    }}
    checkbox.click();
    console.log('已勾选飞机复选框');
    await sleep(300);
    
    let closeBtn = doc.evaluate('//*[@id="close7"]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) {{
        closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }}
    if (!closeBtn) {{
        closeBtn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }}
    if (closeBtn) {{
        closeBtn.click();
        console.log('已关闭选择对话框');
        await sleep(500);
        return true;
    }} else {{
        console.warn('未找到关闭按钮，尝试按 ESC 关闭');
        document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape' }}));
        await sleep(500);
        return false;
    }}
}}

// ==================== 主流程 ====================
async function processRecord(record) {{
    console.log(`\\n开始处理：${{record.reg}} - ${{record.dep_city}} -> ${{record.arr_city}}`);
    
    if (!(await ensureListPage())) {{
        console.error('无法返回列表页，终止流程');
        return false;
    }}
    
    const addBtn = await waitForElement('input.query.yuanjiao');
    if (!addBtn) {{
        console.error('未找到添加按钮，终止流程');
        return false;
    }}
    addBtn.click();
    console.log('已点击添加按钮，等待表单加载...');
    
    const aircraftSelectBtn = await waitForElement('//*[@id="ele7"]', 15000, true);
    if (!aircraftSelectBtn) {{
        console.error('未找到飞机机号选择按钮，终止流程');
        return false;
    }}
    console.log('表单加载完成，找到飞机机号选择按钮');
    
    aircraftSelectBtn.click();
    if (!(await selectAircraft(record.reg))) {{
        console.error('选择飞机失败，终止流程');
        return false;
    }}
    
    const doc = await getCurrentDoc();
    const specialSelect = doc.querySelector('#specialf');
    if (specialSelect) await setSelectValue(specialSelect, "否");
    const certSelect = doc.querySelector('#operationCertificate');
    if (certSelect) await setSelectValue(certSelect, "是");
    const operateSelect = doc.querySelector('#businessOperation');
    if (operateSelect) await setSelectValue(operateSelect, "否");
    
    const purposeSelect = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[19]/div/select[1]', 10000, true);
    if (purposeSelect) await setSelectValue(purposeSelect, record.purpose);
    
    const startDateInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[9]/div/input', 5000, true);
    const endDateInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[10]/div/input', 5000, true);
    if (startDateInput) setDateInput(startDateInput, record.start_date);
    if (endDateInput) setDateInput(endDateInput, record.end_date);
    
    await fillFirstSegmentSelects(record.dep_city);
    await fillFirstSegmentTime(record);
    
    const addSegmentBtn = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div/button', 5000, true);
    if (addSegmentBtn) {{
        addSegmentBtn.click();
        console.log('已点击添加航段按钮，等待新航段加载...');
        await sleep(1000);
        await fillSecondSegmentSelects(record.arr_city);
        await fillSecondSegmentTime();
    }}
    
    // 固定字段
    const detailAreaInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[25]/div/input', 5000, true);
    if (detailAreaInput) {{
        detailAreaInput.value = `${{record.dep_city}}-${{record.arr_city}}`;
        detailAreaInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
    const customerInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[27]/div/input', 5000, true);
    if (customerInput) {{
        customerInput.value = "天成商务航空有限公司";
        customerInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
    const baseInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[28]/div/input', 5000, true);
    if (baseInput) {{
        baseInput.value = `${{record.dep_city}}机场-${{record.arr_city}}机场`;
        baseInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
    const operatorInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[29]/div/input', 5000, true);
    if (operatorInput) {{
        operatorInput.value = "张永一";
        operatorInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
    const phoneInput = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[30]/div/input', 5000, true);
    if (phoneInput) {{
        phoneInput.value = "18566725728";
        phoneInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
    const contractSelect = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[36]/div/select', 5000, true);
    if (contractSelect) await setSelectValue(contractSelect, "已签订");
    const insuranceSelect = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[37]/div/select', 5000, true);
    if (insuranceSelect) await setSelectValue(insuranceSelect, "已参保");
    
    const submitBtn = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[40]/ul/li[2]/input', 5000, true);
    if (submitBtn) {{
        submitBtn.click();
        console.log('已提交，等待弹窗...');
        let confirmBtn = null;
        for (let attempt = 0; attempt < 8; attempt++) {{
            confirmBtn = await waitForDialogConfirmButton(2000);
            if (confirmBtn) break;
            console.log(`等待确定按钮... 第${{attempt+1}}次尝试`);
        }}
        if (confirmBtn) {{
            confirmBtn.click();
            console.log('已点击确定按钮');
        }}
        console.log('等待返回列表页...');
        await waitForElement('input.query.yuanjiao', 15000);
        console.log(`处理完成：${{record.reg}}`);
    }}
    await sleep(2000);
    return true;
}}

// ==================== 执行 ====================
(async () => {{
    const flightRecords = {records_json};
    for (let i = 0; i < flightRecords.length; i++) {{
        const success = await processRecord(flightRecords[i]);
        if (!success) {{
            console.error(`第 ${{i+1}} 条处理失败，终止后续执行。`);
            break;
        }}
    }}
    console.log("所有计划处理完毕");
}})();
"""

    return script_template

# ---------- Streamlit UI ----------
uploaded_file = st.file_uploader("📂 上传 Excel 文件（航段数据）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("文件上传成功！")
        
        # 显示数据预览
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())
        
        # 检查必要列
        required_cols = ["飞机注册号", "出发日期", "到达日期", "用途", "出发城市", "到达城市", "预计飞行时间"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
        else:
            st.info(f"✅ 共读取 {len(df)} 条飞行计划")
            
            # 生成脚本
            if st.button("🚀 生成 JavaScript 脚本"):
                with st.spinner("正在生成脚本..."):
                    script = generate_js_script(df)
                    st.success("脚本生成成功！")
                    st.subheader("📋 复制以下代码到浏览器控制台（F12）运行")
                    st.code(script, language="javascript")
                    st.info("💡 提示：请确保已登录系统并停留在「经营活动信息管理」列表页")
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传 Excel 文件开始")

# 底部说明
st.markdown("---")
st.caption("本工具根据上传的 Excel 自动生成 JavaScript 脚本，用于在民航智慧监管平台通用航空管理系统中自动填报飞行计划。")
