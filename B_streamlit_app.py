# streamlit_app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="飞行计划自动化脚本生成器（当日+次日）", layout="wide")
st.title("✈️ 飞行计划自动化脚本生成器（当日 + 次日）")
st.markdown("""
1. 上传一个包含**当日飞行数据**（有实际到达时间）和**次日计划**（无实际到达时间）的 Excel 文件  
2. 自动生成一个 JavaScript 脚本，在控制台运行后，会**先处理当日实际记录，再填报次日计划**。  

> **注意**：次日脚本已完整内置，当日脚本提供了极简模板，您可以根据需要修改或替换。
""")

# ---------- 当日数据处理脚本模板（极简版，确保无语法错误） ----------
DEFAULT_STEP1_TEMPLATE = """
// ================= 当日数据处理脚本 =================
// 请根据您的实际需求修改此脚本。要求包含一个 async function processToday()，
// 并使用 __EXCEL_DATA__ 作为从 Excel 提取的数据数组。
async function processToday() {
    const excelData = __EXCEL_DATA__;
    console.log(`📅 开始处理当日 ${excelData.length} 条记录...`);
    // 在此处添加您的实际处理逻辑
    // 示例：循环打印数据
    for (let i = 0; i < excelData.length; i++) {
        const record = excelData[i];
        console.log(`处理记录: ${record.飞机注册号} ${record.出发城市} -> ${record.到达城市}`);
    }
    console.log("🎉 当日数据处理完成！");
}
"""

# ---------- 次日计划填报脚本（完整内嵌，使用 RegExp 避免转义问题） ----------
STEP2_SCRIPT_TEMPLATE = """
// ================= 次日计划填报脚本 =================
// 生成时间: __DATETIME__
// 总计 __COUNT__ 条计划

// ================= 获取最新 iframe 文档 ====================
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

// ================= 等待元素出现 ====================
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

// ================= 弹窗确定按钮搜索 ====================
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

// ================= 确保当前在列表页 ====================
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

// ================= 城市到地区/国家的映射 ====================
const CITY_MAP = {
    "菲律宾马尼拉": "菲律宾",
    "马来西亚吉隆坡": "马来西亚",
    "日本东京": "日本",
    "北京首都": "北京",
    "三亚凤凰": "海南",
    "上海": "上海",
    "成都双流": "四川",
    "香港": "香港",
    "哈萨克斯坦阿拉木图": "哈萨克斯坦",
    "贵阳龙洞堡": "贵州",
    "杭州萧山": "浙江",
    "日照山字河": "山东"
};

const CITY_DETAIL_MAP = {
    "三亚凤凰": { province: "海南", district: "三亚" },
    "北京首都": { province: "北京", district: "顺义区" },
    "北京大兴": { province: "北京", district: "大兴区" },
    "天津滨海": { province: "天津", district: "滨海新区" },
    "上海虹桥": { province: "上海", district: "闵行区" },
    "上海浦东": { province: "上海", district: "浦东新区" },
    "重庆江北": { province: "重庆", district: "江北区" },
    "成都双流": { province: "四川", district: "成都" },
    "贵阳龙洞堡": { province: "贵州", district: "贵阳" },
    "杭州萧山": { province: "浙江", district: "杭州" },
    "日照山字河": { province: "山东", district: "日照" }
};

const DOMESTIC_KEYWORDS = [
    '北京', '上海', '广州', '深圳', '成都', '西安', '三亚', '重庆', '天津',
    '杭州', '南京', '武汉', '长沙', '郑州', '青岛', '大连', '厦门', '福州',
    '昆明', '贵阳', '南宁', '海口', '兰州', '西宁', '银川', '乌鲁木齐',
    '拉萨', '呼和浩特', '哈尔滨', '长春', '沈阳', '石家庄', '太原', '济南',
    '合肥', '南昌', '四川', '贵州', '浙江', '山东', '广东'
];

function getLocationInfo(city) {
    const isDomestic = DOMESTIC_KEYWORDS.some(keyword => city.includes(keyword));
    if (isDomestic) {
        let region = CITY_MAP[city];
        if (!region) {
            // 使用 RegExp 代替字面量，避免转义问题
            const match = city.match(new RegExp('^([^\\s\\-]+)'));
            region = match ? match[1] : city;
        }
        return { zone: "境内", region: region, needThirdSelect: true };
    } else {
        let country = CITY_MAP[city];
        if (!country) {
            const parts = city.split(new RegExp('[\\s\\-]'));
            country = parts[0];
        }
        return { zone: "境外", region: country, needThirdSelect: false };
    }
}

// ================= 选择器 ====================
const SELECTORS = {
    addBtnCSS: 'input.query.yuanjiao',
    aircraftSelect: '//*[@id="ele7"]',
    specialSelect: '#specialf',
    certSelect: '#operationCertificate',
    operateSelect: '#businessOperation',
    purposeSelect: '//*[contains(text(), "非经营活动")]/following-sibling::*//select',
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

// ================= 辅助函数 ====================
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
    const detail = CITY_DETAIL_MAP[city];
    if (!detail) {
        console.warn(`未找到城市 ${city} 的详细映射，将使用降级处理`);
        await setSelectValue(selects[0], "境内");
        await setSelectValue(selects[1], info.region);
        if (selects.length >= 3) {
            const thirdSelect = selects[2];
            let chooseBtn = null;
            const possibleButtons = container.querySelectorAll('button, div, span');
            for (let el of possibleButtons) {
                if (el.innerText && el.innerText.includes('请选择')) {
                    chooseBtn = el;
                    break;
                }
            }
            if (chooseBtn) {
                chooseBtn.click();
                await sleep(1000);
            }
            await sleep(1000);
            if (thirdSelect.options.length > 1) {
                console.warn(`未找到区县选项，第三个下拉框将保持当前选择（默认为第一个选项）`);
            } else {
                console.warn('第三个下拉框选项不足');
            }
        }
        return true;
    }
    
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], detail.province);
    console.log(`等待第三个下拉框选项加载 (${detail.district})...`);
    await sleep(1500);
    
    const newSelects = container.querySelectorAll('select');
    if (newSelects.length < 3) {
        console.warn('重新获取后第三个下拉框不存在');
        return false;
    }
    const thirdSelect = newSelects[2];
    console.log('第三个下拉框当前选项:', Array.from(thirdSelect.options).map(o => o.text));
    
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
        console.warn(`未找到区县选项: ${detail.district}，请手动选择或补充映射。`);
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

async function processTomorrow() {
    console.log('🚀 开始执行次日计划填报流程...');
    const flightRecords = __FLIGHT_RECORDS__;
    for (let i = 0; i < flightRecords.length; i++) {
        const record = flightRecords[i];
        console.log(`开始处理：${record.reg} - ${record.dep_city} -> ${record.arr_city}`);
        await processRecord(record);
    }
    console.log('🎉 次日计划填报完成！');
}

// 原脚本中的 processRecord 函数（已从原脚本复制）
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
"""

# ---------- 辅助函数 ----------
def parse_flight_time(time_str):
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours, minutes
    except:
        return 0, 0

def generate_js_script(df_today, df_tomorrow, step1_template, step2_template):
    # 生成当日数据的 JSON
    today_records = []
    for _, row in df_today.iterrows():
        record = {
            "飞机注册号": row.get("飞机注册号", ""),
            "出发城市": row.get("出发城市", ""),
            "到达城市": row.get("到达城市", ""),
            "实际飞行时间": row.get("实际飞行时间", ""),
            "实际出发": str(row.get("实际出发", "")),
            "实际到达": str(row.get("实际到达", ""))
        }
        today_records.append(record)
    today_json = json.dumps(today_records, ensure_ascii=False, indent=4)

    # 生成次日计划的 JSON
    tomorrow_records = []
    for _, row in df_tomorrow.iterrows():
        purpose_raw = row.get("用途", "")
        if "维修" in purpose_raw or "调机" in purpose_raw:
            purpose = "调机"
        else:
            purpose = "自用飞行"
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
        tomorrow_records.append(record)
    tomorrow_json = json.dumps(tomorrow_records, ensure_ascii=False, indent=4)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 替换当日脚本占位符
    today_script = step1_template.replace("__EXCEL_DATA__", today_json)
    today_script = today_script.replace("__DATETIME__", now)
    today_script = today_script.replace("__COUNT__", str(len(df_today)))
    # 替换次日脚本占位符
    tomorrow_script = step2_template.replace("__FLIGHT_RECORDS__", tomorrow_json)
    tomorrow_script = tomorrow_script.replace("__DATETIME__", now)
    tomorrow_script = tomorrow_script.replace("__COUNT__", str(len(df_tomorrow)))

    combined_script = f"""
// ==================== 自动生成的合并脚本 ====================
// 生成时间: {now}
// 当日记录数: {len(df_today)}，次日计划数: {len(df_tomorrow)}
// ============================================================

// ------------------ 当日数据处理部分 ------------------
{today_script}

// ------------------ 次日计划填报部分 ------------------
{tomorrow_script}

// ------------------ 主流程：顺序执行 ------------------
(async () => {{
    console.log("========== 开始执行当日数据处理 ==========");
    await processToday();
    console.log("========== 当日数据处理完成，开始执行次日计划填报 ==========");
    await processTomorrow();
    console.log("========== 所有任务执行完毕 ==========");
}})();
"""
    return combined_script

# ---------- Streamlit UI ----------
uploaded_file = st.file_uploader("📂 上传 Excel 文件（包含当日数据和次日计划）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 读取 Excel，假设表头在第二行（索引1）
        df = pd.read_excel(uploaded_file, header=1)
        df.columns = df.columns.str.strip()
        st.success("文件上传成功！")
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())

        # 分离当日和次日数据
        if "实际到达" in df.columns:
            df_today = df[df["实际到达"].notna() & (df["实际到达"] != "")].copy()
            df_tomorrow = df[df["实际到达"].isna() | (df["实际到达"] == "")].copy()
        else:
            df_today = pd.DataFrame()
            df_tomorrow = df.copy()
            st.warning("Excel 中未找到“实际到达”列，将全部视为次日计划。")

        st.info(f"✅ 当日记录数: {len(df_today)}，次日计划数: {len(df_tomorrow)}")

        if len(df_today) == 0 and len(df_tomorrow) == 0:
            st.error("❌ 没有找到任何有效数据，请检查文件格式。")
            st.stop()

        # 允许用户编辑当日脚本模板（可选）
        with st.expander("✏️ 编辑当日数据处理脚本（可选）"):
            step1_template = st.text_area("当日脚本", value=DEFAULT_STEP1_TEMPLATE, height=300, key="step1")
        step2_template = STEP2_SCRIPT_TEMPLATE  # 次日脚本固定

        with st.spinner("正在生成脚本..."):
            final_script = generate_js_script(df_today, df_tomorrow, step1_template, step2_template)

        st.subheader("📜 生成的合并 JavaScript 脚本")
        st.code(final_script, language="javascript")
        st.info("💡 复制以上代码，在目标网页（飞行计划列表页）按 F12 打开控制台，粘贴并回车执行。")
        st.download_button(
            label="💾 下载脚本文件 (.js)",
            data=final_script,
            file_name="combined_flight_plan.js",
            mime="application/javascript"
        )
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传 Excel 文件开始。")
