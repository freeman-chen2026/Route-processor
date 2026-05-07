import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="外网通航", layout="wide")
st.title("✈️ 外网通航 - 次日计划自动录入脚本生成器")
st.markdown("上传次日飞行计划Excel，自动生成浏览器控制台脚本，**一键自动录入次日计划数据**。")

st.sidebar.header("文件读取配置")
header_row = st.sidebar.number_input(
    "标题行行号（从0开始）",
    min_value=0,
    max_value=10,
    value=1,
    step=1,
    help="Excel中实际列名所在的行索引（第一行为0）。通常您的文件第二行是列名，因此输入 1。"
)

uploaded_file = st.file_uploader("📂 上传次日计划 Excel 文件", type=["xlsx", "xls"])

def map_reg_to_model(reg):
    mapping = {
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5",
    }
    return mapping.get(reg, "GLF4")

def generate_full_script(records):
    records_json = json.dumps(records, ensure_ascii=False, indent=4)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    num_records = len(records)

    # 脚本模板 - 使用 .format() 避免花括号冲突，并增强健壮性
    script_template = """
// ================= 次日计划自动录入脚本（增强版） =================
// 生成时间: {now_str}
// 待处理计划数: {num_records}
// ================================================================

// ----------------------------- 可自定义配置 ---------------------------------
const CONFIG = {{
    // 是否启用详细日志
    verbose: true,
    // 等待元素超时(ms)
    timeout: 15000,
    // 若页面使用了 iframe，请填写 iframe 的 ID 或选择器（例如 '#main'），否则留空 null
    iframeSelector: null,   // 例如 '#main' 或 'iframe'
    // 新增按钮的文本（支持多种）
    addButtonTexts: ["新增", "添加", "新建", "New"],
    // 自定义 XPath（留空则自动使用文本查找）
    customAddBtnXPath: "",
}};

// ----------------------------- 公共辅助函数（支持 iframe） ---------------------------------
let mainDoc = document;

function getMainDocument() {{
    return mainDoc;
}}

async function setIframeDocument(selector) {{
    if (!selector) return;
    const iframe = document.querySelector(selector);
    if (!iframe) {{
        console.warn(`未找到 iframe: ${{selector}}，将使用顶层文档`);
        return;
    }}
    // 等待 iframe 加载
    await new Promise(resolve => {{
        if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {{
            resolve();
        }} else {{
            iframe.onload = () => resolve();
        }}
    }});
    mainDoc = iframe.contentDocument || iframe.contentWindow.document;
    console.log(`已切换到 iframe 文档: ${{selector}}`);
}}

function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

/**
 * 等待元素出现（支持 XPath 和 CSS，自动在 iframe 内查找）
 */
async function waitForElement(selector, timeout = CONFIG.timeout, isXPath = true) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        let el = null;
        const doc = getMainDocument();
        if (!doc) return null;
        if (isXPath) {{
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }} else {{
            el = doc.querySelector(selector);
        }}
        if (el) return el;
        await sleep(300);
    }}
    console.warn(`⚠️ 等待元素超时: ${{selector}}`);
    return null;
}}

/**
 * 通过文本内容查找按钮（更通用）
 */
async function findButtonByText(texts, timeout = CONFIG.timeout) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const doc = getMainDocument();
        if (!doc) return null;
        for (let text of texts) {{
            // 尝试通过 XPath 查找包含文本的按钮、链接或 span
            const xpath = `//button[contains(text(), '${{text}}')] | //a[contains(text(), '${{text}}')] | //span[contains(text(), '${{text}}')]`;
            const el = doc.evaluate(xpath, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (el) return el;
        }}
        await sleep(300);
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
    await sleep(300);
    el.click();
    await sleep(500);
    return true;
}}

// ----------------------------- 业务函数 ---------------------------------
function getModelByReg(reg) {{
    const map = {{
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5"
    }};
    return map[reg] || "GLF4";
}}

async function openAddDialog() {{
    // 1. 优先使用自定义 XPath
    if (CONFIG.customAddBtnXPath) {{
        let btn = await waitForElement(CONFIG.customAddBtnXPath, CONFIG.timeout, true);
        if (btn) {{
            await clickElement(btn);
            return true;
        }}
    }}
    // 2. 通过文本查找
    let btn = await findButtonByText(CONFIG.addButtonTexts, CONFIG.timeout);
    if (btn) {{
        await clickElement(btn);
        return true;
    }}
    // 3. 尝试常见的 CSS 选择器
    const selectors = ['.add-btn', '.btn-add', 'button.add', 'a.add'];
    for (let sel of selectors) {{
        let el = await waitForElement(sel, 1000, false);
        if (el) {{
            await clickElement(el);
            return true;
        }}
    }}
    console.error("❌ 未能找到新增按钮，请检查页面或手动配置 customAddBtnXPath");
    return false;
}}

async function setExecDate(dateStr) {{
    // 尝试直接设置日期输入框
    const dateInput = getMainDocument().querySelector('input[type="date"], input[placeholder*="日期"], .date-input');
    if (dateInput && dateInput.value !== undefined) {{
        setInputValue(dateInput, dateStr);
        console.log(`✅ 直接设置日期输入框: ${{dateStr}}`);
        return true;
    }}
    // 否则尝试点击日期触发器（您提供的 XPath）
    const triggerXPath = "/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/span/span[2]";
    const trigger = await waitForElement(triggerXPath, 5000, true);
    if (!trigger) {{
        console.warn("未找到执行日期触发器，跳过日期填写");
        return false;
    }}
    await clickElement(trigger);
    await sleep(800);
    const day = parseInt(dateStr.split('-')[2], 10);
    const dayCell = getMainDocument().evaluate(`//td[contains(@class, 'day') and text()='${{day}}']`, getMainDocument(), null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (dayCell) {{
        await clickElement(dayCell);
        console.log(`✅ 已选择日期: ${{dateStr}}`);
        return true;
    }}
    console.warn("未能自动选择日期，请手动选择");
    return false;
}}

async function processOneRecord(record, index) {{
    console.log(`\\n========== 开始处理第 ${{index + 1}} 条计划 ==========`);
    console.log(`注册号: ${{record.reg}} | 起飞机场: ${{record.dep_airport}} | 到达机场: ${{record.arr_airport}} | 日期: ${{record.dep_date}}`);
    
    // 打开新增弹框
    if (!(await openAddDialog())) {{
        console.error("❌ 打开新增弹框失败，终止流程");
        return false;
    }}
    await sleep(1500); // 等待弹框加载
    
    // 填写机型
    const model = getModelByReg(record.reg);
    let modelInput = await waitForElement("//*[contains(text(), '机型')]/following::input[1]", 8000, true);
    if (!modelInput) {{
        modelInput = getMainDocument().evaluate("//input[@placeholder='机型'] | //input[contains(@name, 'model')]", getMainDocument(), null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }}
    if (modelInput) {{
        setInputValue(modelInput, model);
        console.log(`✅ 填写机型: ${{model}}`);
    }} else {{
        console.warn("⚠️ 未找到机型输入框，跳过机型填写");
    }}
    
    // 设置日期
    await setExecDate(record.dep_date);
    
    // 异地运行选择“是”
    const remoteTrigger = await waitForElement("/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[6]/span/span/span/span[2]", 5000, true);
    if (remoteTrigger) {{
        await clickElement(remoteTrigger);
        await sleep(500);
        const yesOption = getMainDocument().evaluate("//li[contains(text(),'是')] | //span[contains(text(),'是')]", getMainDocument(), null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (yesOption) await clickElement(yesOption);
    }}
    
    // 任务性质
    let missionText = "公务飞行";
    if (record.purpose && (record.purpose.includes("调机") || record.purpose.includes("维修"))) {{
        missionText = "调机飞行";
    }}
    const missionTrigger = await waitForElement("/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/span/span[2]", 5000, true);
    if (missionTrigger) {{
        await clickElement(missionTrigger);
        await sleep(500);
        let missionInput = getMainDocument().activeElement;
        if (missionInput && (missionInput.tagName === 'INPUT' || missionInput.isContentEditable)) {{
            if (missionInput.isContentEditable) {{
                missionInput.innerText = missionText;
                missionInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }} else {{
                setInputValue(missionInput, missionText);
            }}
            console.log(`✅ 填写任务性质: ${{missionText}}`);
        }}
    }}
    
    // 填写注册号（两处）
    const regSpan = await waitForElement("/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span", 3000, true);
    if (regSpan) regSpan.innerText = record.reg;
    const regInput = await waitForElement("/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span/span/input", 5000, true);
    if (regInput) setInputValue(regInput, record.reg);
    
    // 起飞机场
    const depInput = await waitForElement("//*[contains(text(), '起飞机场')]/following::input[1]", 5000, true);
    if (depInput) setInputValue(depInput, record.dep_airport);
    
    // 到达机场
    const arrInput = await waitForElement("//*[contains(text(), '到达机场')]/following::input[1]", 5000, true);
    if (arrInput) setInputValue(arrInput, record.arr_airport);
    
    // 提交
    const submitBtn = await waitForElement("//button[contains(text(), '确定')] | //button[contains(text(), '保存')] | //a[contains(text(), '确定')]", 8000, true);
    if (submitBtn) {{
        await clickElement(submitBtn);
        console.log("🔘 已点击提交按钮，等待保存...");
        await sleep(3000);
        // 等待弹框关闭，重新回到列表页（通过检测新增按钮是否再次可见）
        await openAddDialog();  // 检测是否可再次打开，以此判断是否已返回列表页
        console.log(`✅ 第 ${{index + 1}} 条计划处理完成并已返回列表页`);
        return true;
    }} else {{
        console.error("❌ 未找到提交按钮，请手动检查");
        return false;
    }}
}}

// ----------------------------- 主流程 ---------------------------------
const flightRecords = {records_json};

async function runAutoEntry() {{
    // 如果配置了 iframe，先切换到 iframe
    if (CONFIG.iframeSelector) {{
        await setIframeDocument(CONFIG.iframeSelector);
    }}
    console.log(`🚀 开始执行次日计划自动录入，共 ${{flightRecords.length}} 条计划`);
    for (let i = 0; i < flightRecords.length; i++) {{
        const success = await processOneRecord(flightRecords[i], i);
        if (!success) {{
            console.error(`❌ 第 ${{i+1}} 条处理失败，终止后续执行`);
            break;
        }}
        await sleep(1000);
    }}
    console.log("🎉 所有次日计划处理完毕！");
}}

runAutoEntry();
"""
    return script_template.format(now_str=now_str, num_records=num_records, records_json=records_json)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=header_row)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        
        required_cols = ["飞机注册号", "出发日期", "出发地", "到达地"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
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
                    "reg": reg,
                    "dep_date": dep_date,
                    "dep_airport": dep_airport,
                    "arr_airport": arr_airport,
                    "purpose": purpose
                })
            
            st.success(f"✅ 文件上传成功！共读取 {len(records)} 条次日计划")
            st.subheader("📊 数据预览")
            st.dataframe(pd.DataFrame(records))
            
            final_script = generate_full_script(records)
            st.subheader("📋 生成的自动化脚本（复制到浏览器控制台运行）")
            st.code(final_script, language="javascript")
            st.download_button(
                label="💾 下载脚本文件 (.js)",
                data=final_script,
                file_name="nextday_auto_entry.js",
                mime="application/javascript"
            )
            st.info("""
            **使用说明：**
            1. 登录目标系统，停留在列表页。
            2. 如果页面在 iframe 中（例如主内容在 `<iframe id="main">` 里），请在生成脚本的顶部 `CONFIG` 中设置 `iframeSelector: "#main"`。
            3. 如果「新增」按钮的 XPath 不正确，可以在 `CONFIG` 中设置 `customAddBtnXPath` 为您实际的绝对 XPath，或修改 `addButtonTexts` 数组。
            4. 按 F12 -> Console，粘贴脚本回车运行。
            """)
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传次日计划 Excel 文件开始生成脚本")

st.markdown("---")
st.caption("本工具自动生成浏览器控制台脚本，支持 iframe 和多种元素查找方式。")
