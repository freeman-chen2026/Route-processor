import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="外网通航", layout="wide")
st.title("✈️ 外网通航 - 次日计划自动录入脚本生成器")
st.markdown("上传次日计划Excel，生成精准控制台脚本，自动填写弹框表单。")

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

# ---------- 用户自定义 XPath 配置（已按您提供的路径预设） ----------
st.sidebar.markdown("## 🔧 页面元素定位（已按您的实际路径预设，可微调）")
custom_xpaths = {
    "addBtn": st.sidebar.text_input("新增按钮 XPath", 
        value="/html/body/div[1]/div[2]/div/table/tbody/tr/td[1]/a[1]/span/span[2]",
        help="列表页「新增」按钮"),
    "modelInput": st.sidebar.text_input("机型输入元素 XPath", 
        value="/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[2]/span",
        help="可编辑的span或input"),
    "execDateInput": st.sidebar.text_input("执行日期输入框 XPath", 
        value="/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/input",
        help="日期输入框"),
    "missionTypeInput": st.sidebar.text_input("任务性质输入框 XPath", 
        value="/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/input",
        help="填“公务飞行”或“调机飞行”"),
    "regInput1": st.sidebar.text_input("第一个飞机注册号输入框 XPath", 
        value="/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span/span/input",
        help="输入注册号"),
    "regInput2": st.sidebar.text_input("第二个飞机注册号位置 XPath", 
        value="/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span",
        help="可能是span或input"),
    "depAirportInput": st.sidebar.text_input("起飞机场输入框 XPath（可选）", 
        value="", placeholder="例如 //input[@placeholder='起飞机场']"),
    "arrAirportInput": st.sidebar.text_input("到达机场输入框 XPath（可选）", 
        value="", placeholder="例如 //input[@placeholder='到达机场']"),
    "submitBtn": st.sidebar.text_input("提交/确定按钮 XPath", 
        value="", placeholder="留空则自动查找含「确定」的按钮"),
}

def generate_full_script(records, custom_xpaths):
    records_json = json.dumps(records, ensure_ascii=False, indent=4)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    num_records = len(records)
    # 过滤掉空的自定义路径
    xpaths = {k: v for k, v in custom_xpaths.items() if v and v.strip()}
    xpaths_json = json.dumps(xpaths, ensure_ascii=False)

    script_template = """
// ================= 次日计划自动录入脚本（精准路径版） =================
// 生成时间: {now_str}
// 待处理计划数: {num_records}
// ====================================================================

// ----------------------------- 用户自定义XPath（已精确配置） -----------------------------
const XPATHS = {xpaths_json};

// ----------------------------- 公共辅助函数 ---------------------------------
function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

async function waitForElement(selector, timeout = 15000, isXPath = true) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        let el = null;
        if (isXPath) {{
            el = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }} else {{
            el = document.querySelector(selector);
        }}
        if (el) return el;
        await sleep(200);
    }}
    console.warn(`⚠️ 等待超时: ${{selector}}`);
    return null;
}}

async function findByText(texts, timeout = 15000, tag = null) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        for (let text of texts) {{
            let xpath = tag ? `//${{tag}}[contains(text(), '${{text}}')]` : `//*[contains(text(), '${{text}}')]`;
            const el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (el) return el;
        }}
        await sleep(200);
    }}
    return null;
}}

function setInputValue(inputEl, value) {{
    if (!inputEl) return false;
    // 对普通input框
    if (inputEl.tagName === 'INPUT' || inputEl.tagName === 'TEXTAREA') {{
        inputEl.value = value;
        inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
        inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
        inputEl.dispatchEvent(new Event('blur', {{ bubbles: true }}));
    }}
    // 对可编辑span/div
    else if (inputEl.isContentEditable || inputEl.getAttribute('contenteditable') === 'true') {{
        inputEl.innerText = value;
        inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
        inputEl.dispatchEvent(new Event('blur', {{ bubbles: true }}));
    }}
    else {{
        // 尝试设置innerText
        inputEl.innerText = value;
    }}
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

// ----------------------------- 业务函数 ---------------------------------
function getModelByReg(reg) {{
    const map = {{
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5"
    }};
    return map[reg] || "GLF4";
}}

async function openAddDialog() {{
    let btn = null;
    if (XPATHS.addBtn) {{
        btn = await waitForElement(XPATHS.addBtn, 10000, true);
    }}
    if (!btn) btn = await findByText(["新增", "添加", "新建"], 10000);
    if (btn) {{
        await clickElement(btn);
        return true;
    }}
    console.error("❌ 未找到新增按钮");
    return false;
}}

async function processOneRecord(record, index) {{
    console.log(`\\n========== 处理第 ${{index+1}} 条计划 ==========`);
    console.log(`${{record.reg}} | ${{record.dep_airport}} -> ${{record.arr_airport}} | ${{record.dep_date}}`);
    
    if (!(await openAddDialog())) return false;
    await sleep(1500);  // 等待弹框完全加载
    
    // 1. 填写机型
    const model = getModelByReg(record.reg);
    let modelEl = await waitForElement(XPATHS.modelInput, 8000, true);
    if (modelEl) {{
        setInputValue(modelEl, model);
        console.log(`✅ 填写机型: ${{model}}`);
    }} else {{
        console.warn("未找到机型元素");
    }}
    
    // 2. 填写执行日期
    let dateInput = null;
    if (XPATHS.execDateInput) {{
        dateInput = await waitForElement(XPATHS.execDateInput, 5000, true);
    }}
    if (dateInput) {{
        setInputValue(dateInput, record.dep_date);
        console.log(`✅ 填写日期: ${{record.dep_date}}`);
    }} else {{
        console.warn("未找到日期输入框");
    }}
    
    // 3. 填写任务性质
    let missionText = (record.purpose && (record.purpose.includes("调机") || record.purpose.includes("维修"))) ? "调机飞行" : "公务飞行";
    let missionInput = null;
    if (XPATHS.missionTypeInput) {{
        missionInput = await waitForElement(XPATHS.missionTypeInput, 5000, true);
    }}
    if (missionInput) {{
        setInputValue(missionInput, missionText);
        console.log(`✅ 填写任务性质: ${{missionText}}`);
    }} else {{
        console.warn("未找到任务性质输入框");
    }}
    
    // 4. 填写第一个注册号
    let reg1 = null;
    if (XPATHS.regInput1) {{
        reg1 = await waitForElement(XPATHS.regInput1, 5000, true);
    }}
    if (reg1) {{
        setInputValue(reg1, record.reg);
        console.log(`✅ 填写注册号1: ${{record.reg}}`);
    }}
    
    // 5. 填写第二个注册号（可能是span）
    let reg2 = null;
    if (XPATHS.regInput2) {{
        reg2 = await waitForElement(XPATHS.regInput2, 5000, true);
    }}
    if (reg2) {{
        setInputValue(reg2, record.reg);
        console.log(`✅ 填写注册号2: ${{record.reg}}`);
    }}
    
    // 6. 起飞机场（优先使用自定义XPath，否则通过文本查找）
    let depEl = null;
    if (XPATHS.depAirportInput) {{
        depEl = await waitForElement(XPATHS.depAirportInput, 5000, true);
    }}
    if (!depEl) {{
        const label = await findByText(["起飞机场", "出发机场"], 3000);
        if (label) {{
            depEl = label.querySelector('input') || label.nextElementSibling;
        }}
    }}
    if (depEl) {{
        setInputValue(depEl, record.dep_airport);
        console.log(`✅ 填写起飞机场: ${{record.dep_airport}}`);
    }} else {{
        console.warn("未找到起飞机场输入框");
    }}
    
    // 7. 到达机场
    let arrEl = null;
    if (XPATHS.arrAirportInput) {{
        arrEl = await waitForElement(XPATHS.arrAirportInput, 5000, true);
    }}
    if (!arrEl) {{
        const label = await findByText(["到达机场", "降落机场"], 3000);
        if (label) {{
            arrEl = label.querySelector('input') || label.nextElementSibling;
        }}
    }}
    if (arrEl) {{
        setInputValue(arrEl, record.arr_airport);
        console.log(`✅ 填写到达机场: ${{record.arr_airport}}`);
    }} else {{
        console.warn("未找到到达机场输入框");
    }}
    
    // 8. 提交按钮
    let submitBtn = null;
    if (XPATHS.submitBtn) {{
        submitBtn = await waitForElement(XPATHS.submitBtn, 8000, true);
    }}
    if (!submitBtn) {{
        submitBtn = await findByText(["确定", "保存", "提交"], 8000, 'button');
    }}
    if (submitBtn) {{
        await clickElement(submitBtn);
        console.log("🔘 已提交，等待保存...");
        await sleep(3000);
        // 等待弹框关闭，重新检测列表页新增按钮
        await openAddDialog();
        console.log(`✅ 第 ${{index+1}} 条处理完成`);
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
    return script_template.format(now_str=now_str, num_records=num_records, 
                                   records_json=records_json, xpaths_json=xpaths_json)

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
            1. 登录系统，停留在列表页。
            2. 按 F12 → Console，粘贴脚本，回车执行。
            3. 脚本将自动点击「新增」，按您提供的XPath填写机型、日期、任务性质、注册号（两处）、起降机场。
            4. 如起降机场未自动填入，请补充侧边栏中「起飞机场输入框XPath」和「到达机场输入框XPath」。
            """)
    except Exception as e:
        st.error(f"处理出错: {e}")
else:
    st.info("请上传 Excel 文件")
