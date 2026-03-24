# streamlit_app.py
import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# ---------- 基础映射（您可在此补充境内机场的区县映射） ----------
BASE_CITY_DETAIL_MAP = {
    # 境外城市示例（自动扩展，这里仅作参考）
    "菲律宾马尼拉": "菲律宾",
    "马来西亚吉隆坡": "马来西亚",
    "日本东京": "日本",
    "香港": "香港",
    # 境内城市（必须包含省份和区县）
    "北京首都": ["北京", "顺义区"],
    "北京大兴": ["北京", "大兴区"],
    "天津滨海": ["天津", "滨海新区"],
    "上海虹桥": ["上海", "闵行区"],
    "上海浦东": ["上海", "浦东新区"],
    "重庆江北": ["重庆", "江北区"],
    "三亚凤凰": ["海南", "三亚"],
    # 如需添加更多，请在此处补充
}

# 国内城市关键词（用于判断境内/境外，仅供未映射城市降级使用）
DOMESTIC_KEYWORDS = [
    '北京', '上海', '广州', '深圳', '成都', '西安', '三亚', '重庆', '天津',
    '杭州', '南京', '武汉', '长沙', '郑州', '青岛', '大连', '厦门', '福州',
    '昆明', '贵阳', '南宁', '海口', '兰州', '西宁', '银川', '乌鲁木齐',
    '拉萨', '呼和浩特', '哈尔滨', '长春', '沈阳', '石家庄', '太原', '济南',
    '合肥', '南昌'
]

def parse_flight_time(time_str):
    """将 "HH:MM" 格式的时间字符串拆分为小时和分钟整数"""
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours, minutes
    except:
        return 0, 0

def build_full_city_map(df):
    """从 DataFrame 中提取所有城市，生成完整的 CITY_DETAIL_MAP"""
    cities = set()
    for _, row in df.iterrows():
        dep = str(row["出发城市"]).strip()
        arr = str(row["到达城市"]).strip()
        cities.add(dep)
        cities.add(arr)

    full_map = BASE_CITY_DETAIL_MAP.copy()
    for city in cities:
        if city in full_map:
            continue
        # 判断是否为境内城市
        is_domestic = any(kw in city for kw in DOMESTIC_KEYWORDS)
        if is_domestic:
            # 境内城市：尝试提取省份（第一个词），区县留空（脚本会降级选择第二个选项）
            province = city.split()[0] if city.split() else city
            full_map[city] = [province, ""]  # 使用数组格式
        else:
            # 境外城市：提取第一个词作为国家名
            match = re.match(r'^([A-Za-z\u4e00-\u9fa5]+)', city)
            if match:
                country = match.group(1)
                full_map[city] = country
            else:
                full_map[city] = city  # 保底
    return full_map

def generate_flight_records(df):
    """从 DataFrame 生成 flightRecords 的 JSON 字符串"""
    records = []
    for _, row in df.iterrows():
        purpose_raw = row.get("用途", "")
        purpose = "调机" if "调机" in purpose_raw else "自用飞行"
        start_date = str(row["出发日期"])
        end_date = str(row["到达日期"])
        flight_time = row.get("预计飞行时间", "")
        hours, minutes = parse_flight_time(flight_time)
        dep_city = str(row["出发城市"]).strip()
        arr_city = str(row["到达城市"]).strip()
        reg_raw = str(row["飞机注册号"]).strip()
        record = {
            "reg": reg_raw,
            "start_date": start_date,
            "end_date": end_date,
            "purpose": purpose,
            "dep_city": dep_city,
            "arr_city": arr_city,
            "flight_hours": hours,
            "flight_minutes": minutes
        }
        records.append(record)
    return json.dumps(records, ensure_ascii=False, indent=4)

def generate_js_script(flight_records_json, city_map_json):
    """生成最终 JavaScript 脚本（嵌入动态映射和数据）"""
    # 用户提供的原始脚本（已移除固定映射和固定数据，使用占位符）
    template = """
// ==================== 自动生成的飞行计划填报脚本 ====================
// 生成时间: __DATETIME__
// 总计 __COUNT__ 条计划

// ==================== 获取最新 iframe 文档 ====================
async function getCurrentDoc() {
    const iframe = document.querySelector('#main');
    if (!iframe) throw new Error('未找到 iframe');
    let doc = iframe.contentDocument;
    while (!doc || !doc.querySelector('body')) {
        await sleep(200);
        doc = iframe.contentDocument;
    }
    return doc;
}

// ==================== 等待元素出现 ====================
async function waitForElement(selector, timeout = 15000, isXPath = false) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const doc = await getCurrentDoc();
        let el;
        if (isXPath) {
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        } else {
            el = doc.querySelector(selector);
        }
        if (el) return el;
        await sleep(500);
    }
    return null;
}

// ==================== 弹窗确定按钮搜索 ====================
async function waitForDialogConfirmButton(timeout = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        let btn = document.evaluate('//a[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!btn) btn = document.evaluate('//button[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (btn) return btn;
        try {
            const doc = await getCurrentDoc();
            btn = doc.evaluate('//a[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (!btn) btn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (btn) return btn;
        } catch(e) {}
        await sleep(300);
    }
    return null;
}

// ==================== 确保当前在列表页 ====================
async function ensureListPage() {
    const btn = await waitForElement('input.query.yuanjiao', 15000);
    if (btn) return true;
    console.log('当前不在列表页，尝试关闭可能遗留的对话框...');
    const doc = await getCurrentDoc();
    let closeBtn = doc.evaluate('//button[contains(text(), "取消")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "返回")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (closeBtn) {
        closeBtn.click();
        console.log('已点击关闭按钮，等待返回列表页');
        await sleep(1000);
        const backBtn = await waitForElement('input.query.yuanjiao', 10000);
        return backBtn !== null;
    } else {
        console.warn('未找到返回按钮，请手动关闭对话框后继续（脚本将等待5秒）');
        await sleep(5000);
        const backBtn = await waitForElement('input.query.yuanjiao', 5000);
        return backBtn !== null;
    }
}

// ==================== 城市详细映射表（自动生成） ====================
const CITY_DETAIL_MAP = __CITY_DETAIL_MAP__;

function getLocationInfo(city) {
    const info = CITY_DETAIL_MAP[city];
    if (!info) {
        console.warn(`未找到城市映射: ${city}，将使用降级处理`);
        // 降级：假设为境外，取第一个词
        const parts = city.split(/[\\s\\-]/);
        const country = parts[0];
        return { zone: "境外", region: country, needThirdSelect: false };
    }
    if (typeof info === 'string') {
        // 境外城市
        return { zone: "境外", region: info, needThirdSelect: false };
    } else if (Array.isArray(info) && info.length >= 1) {
        // 境内城市
        const province = info[0];
        const district = info[1] || null;
        return { zone: "境内", region: province, needThirdSelect: true, district: district };
    }
    return { zone: "境外", region: city, needThirdSelect: false };
}

// ==================== 选择器 ====================
const SELECTORS = {
    addBtnCSS: 'input.query.yuanjiao',
    aircraftSelect: '//*[@id="ele7"]',
    specialSelect: '#specialf',
    certSelect: '#operationCertificate',
    operateSelect: '#businessOperation',
    purposeSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[19]/div/select[1]',
    startDate: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[9]/div/input',
    endDate: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[10]/div/input',
    firstFlightHour: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[1]',
    firstFlightMinute: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[2]',
    firstFlights: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[3]/div/input',
    addSegmentBtn: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div/button',
    secondFlightHour: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[1]',
    secondFlightMinute: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[2]',
    secondFlights: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[3]/div/input',
    detailArea: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[25]/div/input',
    customer: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[27]/div/input',
    base: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[28]/div/input',
    operator: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[29]/div/input',
    phone: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[30]/div/input',
    contractSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[36]/div/select',
    insuranceSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[37]/div/select',
    submitBtn: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[40]/ul/li[2]/input',
};

// ==================== 辅助函数 ====================
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function setSelectValue(selectElement, valueText) {
    for (let i = 0; i < selectElement.options.length; i++) {
        const opt = selectElement.options[i];
        if (opt.text === valueText || opt.text.includes(valueText)) {
            selectElement.selectedIndex = i;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            await sleep(300);
            return true;
        }
    }
    console.warn(`未找到选项: ${valueText}，可用选项：`, Array.from(selectElement.options).map(o => o.text));
    return false;
}

function setDateInput(inputEl, dateStr) {
    if (!inputEl) return false;
    inputEl.value = dateStr;
    inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    inputEl.blur();
    sleep(200);
    return true;
}

// 通用航段填充函数
async function fillSegmentSelects(container, city) {
    const selects = container.querySelectorAll('select');
    if (selects.length < 2) {
        console.warn('航段容器内 select 数量不足');
        return false;
    }
    
    const info = getLocationInfo(city);
    if (info.zone === "境外") {
        await setSelectValue(selects[0], info.zone);
        await setSelectValue(selects[1], info.region);
        return true;
    }
    
    // 境内
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], info.region);
    
    if (selects.length >= 3 && info.district) {
        // 等待1.5秒让第三个下拉框加载
        await sleep(1500);
        const newSelects = container.querySelectorAll('select');
        const thirdSelect = newSelects[2];
        // 查找匹配的区县
        let targetIndex = -1;
        for (let i = 0; i < thirdSelect.options.length; i++) {
            if (thirdSelect.options[i].text.includes(info.district)) {
                targetIndex = i;
                break;
            }
        }
        if (targetIndex !== -1) {
            thirdSelect.selectedIndex = targetIndex;
            thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`已选择第三个下拉框: ${thirdSelect.options[targetIndex].text}`);
        } else if (thirdSelect.options.length > 1) {
            thirdSelect.selectedIndex = 1;
            thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`已选择第三个下拉框的第二个选项: ${thirdSelect.options[1].text}`);
        }
    }
    return true;
}

async function fillFirstSegmentSelects(city) {
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div', 5000, true);
    if (!container) {
        console.warn('未找到第一个航段容器');
        return false;
    }
    return fillSegmentSelects(container, city);
}

async function fillFirstSegmentTime(record) {
    const hourInput = await waitForElement(SELECTORS.firstFlightHour, 5000, true);
    const minuteInput = await waitForElement(SELECTORS.firstFlightMinute, 5000, true);
    const flightsInput = await waitForElement(SELECTORS.firstFlights, 5000, true);
    if (hourInput && minuteInput && flightsInput) {
        hourInput.value = record.flight_hours.toString().padStart(2, '0');
        minuteInput.value = record.flight_minutes.toString().padStart(2, '0');
        flightsInput.value = 1;
        hourInput.dispatchEvent(new Event('input', { bubbles: true }));
        minuteInput.dispatchEvent(new Event('input', { bubbles: true }));
        flightsInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log(`已填入第一个航段时间: ${record.flight_hours}:${record.flight_minutes}, 架次: 1`);
        return true;
    }
    console.warn('无法填入第一个航段时间和架次');
    return false;
}

async function fillSecondSegmentSelects(city) {
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[1]/div/div', 5000, true);
    if (!container) {
        console.warn('未找到第二个航段容器');
        return false;
    }
    return fillSegmentSelects(container, city);
}

async function fillSecondSegmentTime() {
    const hourInput = await waitForElement(SELECTORS.secondFlightHour, 5000, true);
    const minuteInput = await waitForElement(SELECTORS.secondFlightMinute, 5000, true);
    const flightsInput = await waitForElement(SELECTORS.secondFlights, 5000, true);
    if (hourInput && minuteInput && flightsInput) {
        hourInput.value = '00';
        minuteInput.value = '00';
        flightsInput.value = 0;
        hourInput.dispatchEvent(new Event('input', { bubbles: true }));
        minuteInput.dispatchEvent(new Event('input', { bubbles: true }));
        flightsInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入第二个航段时间: 00:00, 架次: 0');
        return true;
    }
    console.warn('无法填入第二个航段时间和架次');
    return false;
}

function formatRegNumber(reg) {
    if (reg.includes('-')) return reg;
    const match = reg.match(/^([A-Z]+)(\\d+[A-Z]*)$/);
    if (match) return `${match[1]}-${match[2]}`;
    return reg;
}

async function selectAircraft(reg) {
    const regForSelect = formatRegNumber(reg);
    console.log(`尝试选择飞机: ${regForSelect}`);
    
    const airbox = await waitForElement('//*[@id="airbox"]', 10000, true);
    if (!airbox) {
        console.warn('未找到飞机选择对话框');
        return false;
    }
    const doc = await getCurrentDoc();
    
    let span = doc.evaluate(`//span[text()='${regForSelect}']`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!span) {
        span = doc.evaluate(`//span[contains(text(), '${regForSelect}')]`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (!span) {
        console.warn(`未找到包含注册号 ${regForSelect} 的 span 元素`);
        return false;
    }
    const li = span.closest('li');
    if (!li) {
        console.warn(`未找到注册号 ${regForSelect} 对应的 li`);
        return false;
    }
    const checkbox = li.querySelector('input[type="checkbox"]');
    if (!checkbox) {
        console.warn(`未找到注册号 ${regForSelect} 的复选框`);
        return false;
    }
    checkbox.click();
    console.log('已勾选飞机复选框');
    await sleep(300);
    
    let closeBtn = doc.evaluate('//*[@id="close7"]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) {
        closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (!closeBtn) {
        closeBtn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (closeBtn) {
        closeBtn.click();
        console.log('已关闭选择对话框');
        await sleep(500);
        return true;
    } else {
        console.warn('未找到关闭按钮，尝试按 ESC 关闭');
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        await sleep(500);
        return false;
    }
}

async function processRecord(record) {
    console.log(`\\n开始处理：${record.reg} - ${record.dep_city} -> ${record.arr_city}`);

    if (!(await ensureListPage())) {
        console.error('无法返回列表页，终止流程');
        return false;
    }

    const addBtn = await waitForElement(SELECTORS.addBtnCSS);
    if (!addBtn) {
        console.error('未找到添加按钮，终止流程');
        return false;
    }
    addBtn.click();
    console.log('已点击添加按钮，等待表单加载...');

    const aircraftSelectBtn = await waitForElement(SELECTORS.aircraftSelect, 15000, true);
    if (!aircraftSelectBtn) {
        console.error('未找到飞机机号选择按钮，终止流程');
        return false;
    }
    console.log('表单加载完成，找到飞机机号选择按钮');

    aircraftSelectBtn.click();
    if (!(await selectAircraft(record.reg))) {
        console.error('选择飞机失败，终止流程');
        return false;
    }

    const doc = await getCurrentDoc();
    const specialSelect = doc.querySelector(SELECTORS.specialSelect);
    if (specialSelect) await setSelectValue(specialSelect, "否");
    else console.warn('未找到是否特殊任务飞行 select');

    const certSelect = doc.querySelector(SELECTORS.certSelect);
    if (certSelect) await setSelectValue(certSelect, "是");
    else console.warn('未找到是否有运行合格证 select');

    const operateSelect = doc.querySelector(SELECTORS.operateSelect);
    if (operateSelect) await setSelectValue(operateSelect, "否");
    else console.warn('未找到是否经营性作业 select');

    const purposeSelect = await waitForElement(SELECTORS.purposeSelect, 10000, true);
    if (purposeSelect) await setSelectValue(purposeSelect, record.purpose);
    else console.warn('未找到用途下拉框');

    const startDateInput = await waitForElement(SELECTORS.startDate, 5000, true);
    const endDateInput = await waitForElement(SELECTORS.endDate, 5000, true);
    if (startDateInput) setDateInput(startDateInput, record.start_date);
    else console.warn('未找到服务开始日期输入框');
    if (endDateInput) setDateInput(endDateInput, record.end_date);
    else console.warn('未找到服务结束日期输入框');

    await fillFirstSegmentSelects(record.dep_city);
    await fillFirstSegmentTime(record);

    const addSegmentBtn = await waitForElement(SELECTORS.addSegmentBtn, 5000, true);
    if (addSegmentBtn) {
        addSegmentBtn.click();
        console.log('已点击添加航段按钮，等待新航段加载...');
        await sleep(1000);
        await fillSecondSegmentSelects(record.arr_city);
        await fillSecondSegmentTime();
    } else {
        console.warn('未找到添加航段按钮');
    }

    const detailAreaInput = await waitForElement(SELECTORS.detailArea, 5000, true);
    if (detailAreaInput) {
        detailAreaInput.value = `${record.dep_city}-${record.arr_city}`;
        detailAreaInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入详细作业地区');
    } else console.warn('未找到详细作业地区输入框');

    const customerInput = await waitForElement(SELECTORS.customer, 5000, true);
    if (customerInput) {
        customerInput.value = "天成商务航空有限公司";
        customerInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入服务客户名称');
    } else console.warn('未找到服务客户名称输入框');

    const baseInput = await waitForElement(SELECTORS.base, 5000, true);
    if (baseInput) {
        baseInput.value = `${record.dep_city}机场-${record.arr_city}机场`;
        baseInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入作业基地名称');
    } else console.warn('未找到作业基地名称输入框');

    const operatorInput = await waitForElement(SELECTORS.operator, 5000, true);
    if (operatorInput) {
        operatorInput.value = "张永一";
        operatorInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入作业负责人姓名');
    } else console.warn('未找到作业负责人姓名输入框');

    const phoneInput = await waitForElement(SELECTORS.phone, 5000, true);
    if (phoneInput) {
        phoneInput.value = "18566725728";
        phoneInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入负责人联系电话');
    } else console.warn('未找到负责人联系电话输入框');

    const contractSelect = await waitForElement(SELECTORS.contractSelect, 5000, true);
    if (contractSelect) await setSelectValue(contractSelect, "已签订");
    else console.warn('未找到合同订立情况下拉框');

    const insuranceSelect = await waitForElement(SELECTORS.insuranceSelect, 5000, true);
    if (insuranceSelect) await setSelectValue(insuranceSelect, "已参保");
    else console.warn('未找到保险情况下拉框');

    const submitBtn = await waitForElement(SELECTORS.submitBtn, 5000, true);
    if (submitBtn) {
        submitBtn.click();
        console.log('已提交，等待弹窗...');
        let confirmBtn = null;
        for (let attempt = 0; attempt < 8; attempt++) {
            confirmBtn = await waitForDialogConfirmButton(2000);
            if (confirmBtn) break;
            console.log(`等待确定按钮... 第${attempt+1}次尝试`);
        }
        if (confirmBtn) {
            confirmBtn.click();
            console.log('已点击确定按钮');
        } else {
            console.warn('未找到确定按钮，请手动点击');
        }
        console.log('等待返回列表页...');
        await waitForElement(SELECTORS.addBtnCSS, 15000);
        console.log(`处理完成：${record.reg}`);
    } else {
        console.warn('未找到提交按钮');
    }
    await sleep(2000);
    return true;
}

// ==================== 执行 ====================
(async () => {
    const flightRecords = __FLIGHT_RECORDS__;
    for (let i = 0; i < flightRecords.length; i++) {
        const success = await processRecord(flightRecords[i]);
        if (!success) {
            console.error(`第 ${i+1} 条处理失败，终止后续执行。`);
            break;
        }
    }
    console.log("所有计划处理完毕");
})();
"""
    # 替换占位符
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = len(json.loads(flight_records_json))
    final_script = template.replace("__DATETIME__", now)
    final_script = final_script.replace("__COUNT__", str(count))
    final_script = final_script.replace("__CITY_DETAIL_MAP__", city_map_json)
    final_script = final_script.replace("__FLIGHT_RECORDS__", flight_records_json)
    return final_script

# ---------- Streamlit UI ----------
st.set_page_config(page_title="飞行计划自动填报代码生成器", layout="wide")
st.title("✈️ 飞行计划自动填报代码生成器")
st.markdown("上传 Excel 文件，自动生成可直接在浏览器控制台运行的 JavaScript 代码（**自动识别境外城市并映射到国家名**）")

# 侧边栏配置
st.sidebar.header("文件读取配置")
header_row = st.sidebar.number_input("标题行行号（从0开始）", min_value=0, max_value=10, value=1, step=1,
                                     help="Excel 中实际列名所在的行索引（第一行为0）。通常您的文件第二行是列名，因此输入 1。")

uploaded_file = st.file_uploader("📂 上传 Excel 文件（航段数据）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 读取 Excel，指定标题行
        df = pd.read_excel(uploaded_file, header=header_row)
        # 清洗列名：去除首尾空格
        df.columns = df.columns.str.strip()
        # 删除全空行（可选）
        df = df.dropna(how='all')
        st.success("文件上传成功！")
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())

        required_cols = ["飞机注册号", "出发日期", "到达日期", "用途", "出发城市", "到达城市", "预计飞行时间"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
            st.info(f"实际列名: {list(df.columns)}")
        else:
            st.info(f"✅ 共读取 {len(df)} 条飞行计划")

            if st.button("🚀 生成 JavaScript 脚本"):
                with st.spinner("正在构建城市映射并生成脚本..."):
                    # 构建完整城市映射
                    full_map = build_full_city_map(df)
                    city_map_json = json.dumps(full_map, ensure_ascii=False, indent=4)
                    # 生成飞行记录 JSON
                    flight_records_json = generate_flight_records(df)
                    # 生成最终脚本
                    final_script = generate_js_script(flight_records_json, city_map_json)
                    st.success("脚本生成成功！")
                    st.subheader("📋 复制以下代码到浏览器控制台（F12）运行")
                    st.code(final_script, language="javascript")
                    st.info("💡 提示：请确保已登录系统并停留在「经营活动信息管理」列表页")
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传 Excel 文件开始")

st.markdown("---")
st.caption("本工具自动识别境外城市并映射到国家名，境内城市需在基础映射中补充区县信息。如需添加新的境内机场，请修改代码中的 BASE_CITY_DETAIL_MAP。")
