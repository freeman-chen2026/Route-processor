import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="外网通航", layout="wide")
st.title("✈️ 外网通航 - 次日计划自动录入脚本生成器")
st.markdown("上传次日计划Excel，自定义页面元素XPath，一键生成精准的控制台脚本。")

st.sidebar.header("文件读取配置")
header_row = st.sidebar.number_input("标题行行号（从0开始）", min_value=0, max_value=10, value=1, step=1)

uploaded_file = st.file_uploader("📂 上传次日计划 Excel 文件", type=["xlsx", "xls"])

# ---------- 机型映射 ----------
def map_reg_to_model(reg):
    mapping = {
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5",
    }
    return mapping.get(reg, "GLF4")

# ---------- 用户自定义 XPath 配置（在侧边栏） ----------
st.sidebar.markdown("## 🔧 页面元素定位（可留空，脚本会自动尝试）")
custom_xpaths = {
    "addBtn": st.sidebar.text_input("新增按钮 XPath", value="", placeholder="/html/body/.../span/span[2]"),
    "modelInput": st.sidebar.text_input("机型输入框 XPath", value="", placeholder="或输入 /html/body/.../ul[2]/li[2]/span"),
    "execDateTrigger": st.sidebar.text_input("执行日期触发器 XPath", value="", placeholder="点击后弹出日期选择器的元素"),
    "remoteRunTrigger": st.sidebar.text_input("异地运行触发器 XPath", value="", placeholder="点击后选择'是'的元素"),
    "missionTypeTrigger": st.sidebar.text_input("任务性质触发器 XPath", value="", placeholder="点击后填写任务性质的元素"),
    "regSpan": st.sidebar.text_input("注册号显示区 XPath", value="", placeholder="第一个注册号填写位置"),
    "regInput": st.sidebar.text_input("注册号输入框 XPath", value="", placeholder="第二个注册号填写位置"),
    "depAirportInput": st.sidebar.text_input("起飞机场输入框 XPath", value="", placeholder="输入四字码的输入框"),
    "arrAirportInput": st.sidebar.text_input("到达机场输入框 XPath", value="", placeholder="输入四字码的输入框"),
    "submitBtn": st.sidebar.text_input("提交/确定按钮 XPath", value="", placeholder="//button[contains(text(),'确定')]"),
}

def generate_full_script(records, custom_xpaths):
    records_json = json.dumps(records, ensure_ascii=False, indent=4)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    num_records = len(records)

    script_template = """
// ================= 次日计划自动录入脚本（自定义XPath版） =================
// 生成时间: {now_str}
// 待处理计划数: {num_records}
// ====================================================================

// ----------------------------- 用户自定义配置（已从页面传入） -----------------------------
const CUSTOM_XPATHS = {custom_xpaths_json};

// ----------------------------- 公共辅助函数 ---------------------------------
function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

/**
 * 等待元素出现（支持XPath或CSS，自动处理iframe）
 * @param {{string}} selector - XPath 或 CSS 选择器
 * @param {{number}} timeout - 超时(ms)
 * @param {{boolean}} isXPath - 是否为XPath
 * @returns {{Promise<Element|null>}}
 */
async function waitForElement(selector, timeout = 15000, isXPath = true) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        let el = null;
        const doc = document;
        if (isXPath) {{
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }} else {{
            el = doc.querySelector(selector);
        }}
        if (el) return el;
        await sleep(200);
    }}
    console.warn(`⚠️ 等待超时: ${{selector}}`);
    return null;
}}

/**
 * 通过文本内容查找元素（更通用）
 * @param {{string[]}} texts - 可能包含的文本数组
 * @param {{number}} timeout
 * @param {{string}} tag - 限定标签类型，如 'button','a','span','input'
 */
async function findByText(texts, timeout = 15000, tag = null) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const doc = document;
        for (let text of texts) {{
            let xpath = tag ? `//${{tag}}[contains(text(), '${{text}}')]` : `//*[contains(text(), '${{text}}')]`;
            const el = doc.evaluate(xpath, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (el) return el;
        }}
        await sleep(200);
    }}
    return null;
}}

function setInputValue(inputEl, value) {{
    if (!inputEl) return false;
    inputEl.value = value;
    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('blur', {{ bubbles: true }}));
    return true;
}}

async function clickElement(el) {{
    if (!el) return false;
    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    await sleep(200);
    el.click();
    await sleep(500);
    return true;
}}

// ----------------------------- 业务逻辑（根据自定义XPath优先） ---------------------------------
function getModelByReg(reg) {{
    const map = {{
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5"
    }};
    return map[reg] || "GLF4";
}}

async function openAddDialog() {{
    let btn = null;
    if (CUSTOM_XPATHS.addBtn) {{
        btn = await waitForElement(CUSTOM_XPATHS.addBtn, 10000, true);
    }}
    if (!btn) btn = await findByText(["新增", "添加", "新建"], 10000);
    if (!btn) btn = await waitForElement(".add-btn, .btn-add, button.add", 3000, false);
    if (btn) {{
        await clickElement(btn);
        return true;
    }}
    console.error("❌ 未找到新增按钮");
    return false;
}}

async function setExecDate(dateStr) {{
    // 优先使用自定义日期触发器
    let trigger = null;
    if (CUSTOM_XPATHS.execDateTrigger) {{
        trigger = await waitForElement(CUSTOM_XPATHS.execDateTrigger, 5000, true);
    }}
    if (!trigger) {{
        // 尝试直接设置日期输入框
        const dateInput = document.querySelector('input[type="date"], input[placeholder*="日期"]');
        if (dateInput && dateInput.value !== undefined) {{
            setInputValue(dateInput, dateStr);
            console.log(`✅ 直接设置日期: ${{dateStr}}`);
            return true;
        }}
        // 尝试通过文本查找日期触发器
        trigger = await findByText(["执行日期", "日期"], 5000);
    }}
    if (!trigger) {{
        console.warn("未找到日期触发器，跳过日期填写");
        return false;
    }}
    await clickElement(trigger);
    await sleep(800);
    const day = parseInt(dateStr.split('-')[2], 10);
    const dayCell = document.evaluate(`//td[contains(@class, 'day') and text()='${{day}}']`, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (dayCell) {{
        await clickElement(dayCell);
        console.log(`✅ 已选择日期: ${{dateStr}}`);
        return true;
    }}
    console.warn("未能自动选择日期，请手动选择");
    return false;
}}

async function processOneRecord(record, index) {{
    console.log(`\\n========== 处理第 ${{index+1}} 条计划 ==========`);
    console.log(`${{record.reg}} | ${{record.dep_airport}} -> ${{record.arr_airport}} | ${{record.dep_date}}`);
    
    if (!(await openAddDialog())) return false;
    await sleep(1500);
    
    // 1. 机型
    const model = getModelByReg(record.reg);
    let modelInput = null;
    if (CUSTOM_XPATHS.modelInput) {{
        modelInput = await waitForElement(CUSTOM_XPATHS.modelInput, 8000, true);
    }}
    if (!modelInput) {{
        modelInput = await findByText(["机型"], 5000);
        if (modelInput) {{
            // 如果找到的是标签，则找相邻输入框
            let input = modelInput.nextElementSibling || modelInput.closest('li')?.querySelector('input');
            if (input) modelInput = input;
        }}
    }}
    if (modelInput && (modelInput.tagName === 'INPUT' || modelInput.isContentEditable)) {{
        setInputValue(modelInput, model);
        console.log(`✅ 填写机型: ${{model}}`);
    }} else {{
        console.warn("未找到机型输入框，尝试通过span设置文本");
        const modelSpan = await waitForElement("//span[contains(@class,'model')]", 2000, true);
        if (modelSpan) modelSpan.innerText = model;
    }}
    
    // 2. 日期
    await setExecDate(record.dep_date);
    
    // 3. 异地运行
    let remoteTrigger = null;
    if (CUSTOM_XPATHS.remoteRunTrigger) {{
        remoteTrigger = await waitForElement(CUSTOM_XPATHS.remoteRunTrigger, 5000, true);
    }}
    if (!remoteTrigger) remoteTrigger = await findByText(["异地运行"], 5000);
    if (remoteTrigger) {{
        await clickElement(remoteTrigger);
        await sleep(500);
        const yesOpt = await findByText(["是"], 2000);
        if (yesOpt) await clickElement(yesOpt);
    }}
    
    // 4. 任务性质
    let missionText = (record.purpose && (record.purpose.includes("调机") || record.purpose.includes("维修"))) ? "调机飞行" : "公务飞行";
    let missionTrigger = null;
    if (CUSTOM_XPATHS.missionTypeTrigger) {{
        missionTrigger = await waitForElement(CUSTOM_XPATHS.missionTypeTrigger, 5000, true);
    }}
    if (!missionTrigger) missionTrigger = await findByText(["任务性质", "任务类型"], 5000);
    if (missionTrigger) {{
        await clickElement(missionTrigger);
        await sleep(500);
        let input = document.activeElement;
        if (input) {{
            if (input.isContentEditable) {{
                input.innerText = missionText;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }} else {{
                setInputValue(input, missionText);
            }}
            console.log(`✅ 填写任务性质: ${{missionText}}`);
        }}
    }}
    
    // 5. 注册号（两处）
    if (CUSTOM_XPATHS.regSpan) {{
        let span = await waitForElement(CUSTOM_XPATHS.regSpan, 3000, true);
        if (span) span.innerText = record.reg;
    }}
    if (CUSTOM_XPATHS.regInput) {{
        let inp = await waitForElement(CUSTOM_XPATHS.regInput, 3000, true);
        if (inp) setInputValue(inp, record.reg);
    }}
    
    // 6. 起飞机场
    let depInput = null;
    if (CUSTOM_XPATHS.depAirportInput) {{
        depInput = await waitForElement(CUSTOM_XPATHS.depAirportInput, 5000, true);
    }}
    if (!depInput) depInput = await findByText(["起飞机场", "出发机场"], 5000);
    if (depInput) {{
        let input = depInput.tagName === 'INPUT' ? depInput : depInput.querySelector('input') || depInput.nextElementSibling;
        if (input) setInputValue(input, record.dep_airport);
    }}
    
    // 7. 到达机场
    let arrInput = null;
    if (CUSTOM_XPATHS.arrAirportInput) {{
        arrInput = await waitForElement(CUSTOM_XPATHS.arrAirportInput, 5000, true);
    }}
    if (!arrInput) arrInput = await findByText(["到达机场", "降落机场"], 5000);
    if (arrInput) {{
        let input = arrInput.tagName === 'INPUT' ? arrInput : arrInput.querySelector('input') || arrInput.nextElementSibling;
        if (input) setInputValue(input, record.arr_airport);
    }}
    
    // 8. 提交
    let submitBtn = null;
    if (CUSTOM_XPATHS.submitBtn) {{
        submitBtn = await waitForElement(CUSTOM_XPATHS.submitBtn, 8000, true);
    }}
    if (!submitBtn) submitBtn = await findByText(["确定", "保存", "提交"], 8000, 'button');
    if (submitBtn) {{
        await clickElement(submitBtn);
        console.log("🔘 已提交，等待保存...");
        await sleep(3000);
        // 简单判断：如果新增按钮重新变为可点击，视为返回列表页
        await openAddDialog(); 
        console.log(`✅ 第 ${{index+1}} 条完成`);
        return true;
    }} else {{
        console.error("❌ 未找到提交按钮");
        return false;
    }}
}}

// ----------------------------- 主流程 ---------------------------------
const flightRecords = {records_json};

async function runAutoEntry() {{
    console.log(`🚀 开始录入，共 ${{flightRecords.length}} 条计划`);
    for (let i = 0; i < flightRecords.length; i++) {{
        const success = await processOneRecord(flightRecords[i], i);
        if (!success) break;
        await sleep(1000);
    }}
    console.log("🎉 全部完成");
}}
runAutoEntry();
"""
    custom_xpaths_json = json.dumps({k: v for k, v in custom_xpaths.items() if v and v.strip()}, ensure_ascii=False)
    return script_template.format(now_str=now_str, num_records=num_records, records_json=records_json, custom_xpaths_json=custom_xpaths_json)

# ---------- Streamlit 主体 ----------
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=header_row)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        
        required = ["飞机注册号", "出发日期", "出发地", "到达地"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"缺少列: {missing}")
            st.info(f"实际列名: {list(df.columns)}")
        else:
            df["出发日期"] = pd.to_datetime(df["出发日期"]).dt.date
            records = []
            for _, row in df.iterrows():
                reg = str(row["飞机注册号"]).strip()
                dep_date = row["出发日期"].strftime("%Y-%m-%d")
                dep_airport = str(row["出发地"]).strip()
                arr_airport = str(row["到达地"]).strip()
                purpose = str(row.get("用途", "")).strip() if "用途" in df.columns else ""
                records.append({
                    "reg": reg, "dep_date": dep_date,
                    "dep_airport": dep_airport, "arr_airport": arr_airport, "purpose": purpose
                })
            
            st.success(f"✅ 共 {len(records)} 条次日计划")
            st.dataframe(pd.DataFrame(records))
            
            final_script = generate_full_script(records, custom_xpaths)
            st.subheader("📋 生成的自动化脚本（复制到控制台运行）")
            st.code(final_script, language="javascript")
            st.download_button("💾 下载脚本", final_script, "nextday_auto.js", "application/javascript")
            
            st.info("""
            **使用步骤：**
            1. 根据您实际页面的元素，在左侧边栏填入对应的 XPath（如机型输入框、日期触发器、起飞机场输入框等）。
            2. 如果某个输入框留空，脚本会尝试通过文本（如“机型”、“起飞机场”）自动查找。
            3. 登录系统并停留在列表页，打开控制台（F12），粘贴脚本回车。
            4. 观察控制台输出，若仍有元素未找到，请根据输出的警告信息调整对应 XPath。
            """)
    except Exception as e:
        st.error(f"处理出错: {e}")
else:
    st.info("请上传 Excel 文件")
