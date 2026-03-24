# streamlit_app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ---------- 用户提供的原脚本（完整保留，仅将数据部分替换为占位符） ----------
ORIGINAL_SCRIPT = '''// ==================== 获取最新 iframe 文档 ====================
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

// ==================== 等待元素出现（超时返回 null） ====================
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

// ==================== 在顶层文档和 iframe 内搜索弹窗确定按钮 ====================
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

// ==================== 城市到地区/国家的映射 ====================
const CITY_MAP = {
    // 境外城市 -> 国家名
    "菲律宾马尼拉": "菲律宾",
    "马来西亚吉隆坡": "马来西亚",
    "日本东京": "日本",
    // 境内城市 -> 省级/直辖市（仅用于降级处理）
    "北京首都": "北京",
    "三亚凤凰": "海南",
    "上海": "上海",
};

// 境内机场到（省份，区县）的详细映射
const CITY_DETAIL_MAP = {
    "三亚凤凰": { province: "海南", district: "三亚" },
    "北京首都": { province: "北京", district: "顺义区" },
    "北京大兴": { province: "北京", district: "大兴区" },
    "天津滨海": { province: "天津", district: "滨海新区" },
    "上海虹桥": { province: "上海", district: "闵行区" },
    "上海浦东": { province: "上海", district: "浦东新区" },
    "重庆江北": { province: "重庆", district: "江北区" },
    // 添加其他常见机场的映射
};

function getLocationInfo(city) {
    const domesticKeywords = ['北京', '上海', '广州', '深圳', '成都', '西安', '三亚', '重庆', '天津', '杭州', '南京', '武汉', '长沙', '郑州', '青岛', '大连', '厦门', '福州', '昆明', '贵阳', '南宁', '海口', '兰州', '西宁', '银川', '乌鲁木齐', '拉萨', '呼和浩特', '哈尔滨', '长春', '沈阳', '石家庄', '太原', '济南', '合肥', '南昌'];
    const isDomestic = domesticKeywords.some(keyword => city.includes(keyword));
    
    if (isDomestic) {
        let region = CITY_MAP[city];
        if (!region) {
            const match = city.match(/^([^\\s\\-]+)/);
            region = match ? match[1] : city;
        }
        return { zone: "境内", region: region, needThirdSelect: true };
    } else {
        let country = CITY_MAP[city];
        if (!country) {
            const parts = city.split(/[\\s\\-]/);
            country = parts[0];
        }
        return { zone: "境外", region: country, needThirdSelect: false };
    }
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

// 通用航段填充函数（最终改进版）
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
    
    const detail = CITY_DETAIL_MAP[city];
    if (!detail) {
        console.warn(`未找到城市 ${city} 的详细映射，将使用降级处理`);
        await setSelectValue(selects[0], "境内");
        await setSelectValue(selects[1], info.region);
        if (selects.length >= 3) {
            const thirdSelect = selects[2];
            await sleep(1000);
            if (thirdSelect.options.length > 1) {
                thirdSelect.selectedIndex = 1;
                thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
                console.log(`已选择第三个下拉框的第二个选项: ${thirdSelect.options[1].text}`);
            } else {
                console.warn('第三个下拉框选项不足');
            }
        }
        return true;
    }
    
    // 设置境内和省份
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], detail.province);
    
    // 等待1.5秒，让第三个下拉框的选项加载
    console.log(`等待第三个下拉框选项加载 (${detail.district})...`);
    await sleep(1500);
    
    // 重新获取第三个下拉框元素（因为页面可能动态更新）
    const newSelects = container.querySelectorAll('select');
    if (newSelects.length < 3) {
        console.warn('重新获取后第三个下拉框不存在');
        return false;
    }
    const thirdSelect = newSelects[2];
    
    // 打印选项列表，便于调试
    console.log('第三个下拉框当前选项:', Array.from(thirdSelect.options).map(o => o.text));
    
    // 尝试匹配目标区县
    let targetIndex = -1;
    for (let i = 0; i < thirdSelect.options.length; i++) {
        if (thirdSelect.options[i].text.includes(detail.district)) {
            targetIndex = i;
            break;
        }
    }
    
    if (targetIndex !== -1) {
        thirdSelect.selectedIndex = targetIndex;
        thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
        console.log(`已选择第三个下拉框: ${thirdSelect.options[targetIndex].text}`);
    } else {
        console.warn(`未找到区县选项: ${detail.district}，将选择第二个选项`);
        if (thirdSelect.options.length > 1) {
            thirdSelect.selectedIndex = 1;
            thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`已选择第三个下拉框的第二个选项: ${thirdSelect.options[1].text}`);
        } else {
            console.warn('第三个下拉框选项不足');
        }
    }
    await sleep(500);
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

// ==================== 主流程 ====================
(async () => {
    // ========== 请将你的 JSON 数据粘贴到这里 ==========
    const flightRecords = __FLIGHT_RECORDS_PLACEHOLDER__;
    for (let i = 0; i < flightRecords.length; i++) {
        const success = await processRecord(flightRecords[i]);
        if (!success) {
            console.error(`第 ${i+1} 条处理失败，终止后续执行。`);
            break;
        }
    }
    console.log("流程结束");
})();
'''

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

def generate_flight_records(df):
    """从 DataFrame 生成 flightRecords 的 JSON 字符串"""
    records = []
    for _, row in df.iterrows():
        # 处理用途：除“调机”外统一为“自用飞行”
        purpose_raw = row.get("用途", "")
        purpose = "调机" if "调机" in purpose_raw else "自用飞行"

        # 日期处理（直接使用字符串，原脚本 pd.to_datetime 可处理）
        start_date = str(row["出发日期"])
        end_date = str(row["到达日期"])

        # 飞行时间
        flight_time = row.get("预计飞行时间", "")
        hours, minutes = parse_flight_time(flight_time)

        # 城市信息
        dep_city_raw = row["出发城市"]
        arr_city_raw = row["到达城市"]

        # 注册号（保持原样，原脚本的 formatRegNumber 会处理）
        reg_raw = row["飞机注册号"]

        record = {
            "reg": reg_raw,
            "start_date": start_date,
            "end_date": end_date,
            "purpose": purpose,
            "dep_city": dep_city_raw,
            "arr_city": arr_city_raw,
            "flight_hours": hours,
            "flight_minutes": minutes
        }
        records.append(record)

    # 生成 JSON 字符串，保持缩进（与原脚本格式一致）
    return json.dumps(records, ensure_ascii=False, indent=4)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="飞行计划自动填报代码生成器", layout="wide")
st.title("✈️ 飞行计划自动填报代码生成器")
st.markdown("上传 Excel 文件，自动生成可直接在浏览器控制台运行的 JavaScript 代码（**仅替换飞行计划数据，脚本逻辑完全保留**）")

uploaded_file = st.file_uploader("📂 上传 Excel 文件（航段数据）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        # 清洗列名：去除首尾空格
        df.columns = df.columns.str.strip()
        st.success("文件上传成功！")
        
        # 显示数据预览
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())
        
        # 检查必要列
        required_cols = ["飞机注册号", "出发日期", "到达日期", "用途", "出发城市", "到达城市", "预计飞行时间"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
            st.info(f"实际列名: {list(df.columns)}")
        else:
            st.info(f"✅ 共读取 {len(df)} 条飞行计划")
            
            # 生成脚本
            if st.button("🚀 生成 JavaScript 脚本"):
                with st.spinner("正在生成脚本..."):
                    # 生成新的 flightRecords 数组
                    new_records_json = generate_flight_records(df)
                    # 替换占位符
                    final_script = ORIGINAL_SCRIPT.replace("__FLIGHT_RECORDS_PLACEHOLDER__", new_records_json)
                    # 添加生成时间注释（可选）
                    final_script = f"// 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{final_script}"
                    st.success("脚本生成成功！")
                    st.subheader("📋 复制以下代码到浏览器控制台（F12）运行")
                    st.code(final_script, language="javascript")
                    st.info("💡 提示：请确保已登录系统并停留在「经营活动信息管理」列表页")
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传 Excel 文件开始")

st.markdown("---")
st.caption("本工具根据上传的 Excel 自动生成飞行计划数据，并嵌入到已调试好的脚本模板中。模板包含完整的填报逻辑，您无需担心修改。")
