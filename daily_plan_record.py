import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta

# ---------- 页面配置 ----------
st.set_page_config(page_title="公务机次日计划自动录入生成器", layout="wide")
st.title("✈️ 次日计划自动录入脚本生成器")
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

# ---------- 机型映射 ----------
def map_reg_to_model(reg):
    """根据飞机注册号映射机型代码"""
    mapping = {
        "B652Q": "GLF4",
        "B652R": "GLF4",
        "B652S": "GLF4",
        "B8262": "GLF4",
        "B3926": "LJ60",
        "B658L": "GLF6",
        "B8105": "GLEX",
        "B8160": "GLF5",
    }
    return mapping.get(reg, "GLF4")  # 默认GLF4

# ---------- 生成完整脚本 ----------
def generate_full_script(records):
    """
    records: list of dict, 每条包含:
        - reg: 飞机注册号
        - dep_date: 出发日期（字符串 YYYY-MM-DD）
        - dep_airport: 出发地（四字码，如ZGSZ）
        - arr_airport: 到达地（四字码）
        - purpose: 用途（用于判断任务性质）
    """
    records_json = json.dumps(records, ensure_ascii=False, indent=4)
    
    script = f"""
// ================= 次日计划自动录入脚本 =================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 待处理计划数: {len(records)}
// ======================================================

// ----------------------------- 公共辅助函数 ---------------------------------
function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

/**
 * 等待元素出现（支持多种选择器方式）
 * @param {{string}} selector - XPath 或 CSS 选择器
 * @param {{number}} timeout - 超时时间(ms)
 * @param {{boolean}} isXPath - 是否为XPath
 * @returns {{
 */
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
        await sleep(300);
    }}
    console.warn(`⚠️ 等待元素超时: ${{selector}}`);
    return null;
}}

/**
 * 设置输入框的值并触发事件
 * @param {HTMLElement} inputEl 输入框元素
 * @param {string} value 要设置的值
 */
function setInputValue(inputEl, value) {{
    if (!inputEl) return false;
    inputEl.value = value;
    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('blur', {{ bubbles: true }}));
    return true;
}}

/**
 * 点击元素并等待一小段时间
 */
async function clickElement(el) {{
    if (!el) return false;
    el.click();
    await sleep(500);
    return true;
}}

/**
 * 模拟在下拉框中选中指定文本
 */
async function selectDropdownOption(selectEl, targetText) {{
    if (!selectEl) return false;
    // 如果是原生 select
    if (selectEl.tagName === 'SELECT') {{
        for (let i = 0; i < selectEl.options.length; i++) {{
            if (selectEl.options[i].text === targetText || selectEl.options[i].text.includes(targetText)) {{
                selectEl.selectedIndex = i;
                selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
        }}
    }}
    // 否则可能是自定义下拉，尝试点击选项
    const options = document.evaluate(`//li[contains(text(), '${{targetText}}')]`, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (options) {{
        options.click();
        return true;
    }}
    return false;
}

// ----------------------------- 配置区（可根据实际页面微调XPath） ---------------------------------
// 注意：以下XPath基于您提供的典型页面结构，如页面有变化可手动调整
const XPATHS = {{
    // 新增按钮（在列表页）
    addBtn: "/html/body/div[1]/div[2]/div/table/tbody/tr/td[1]/a[1]/span/span[2]",
    
    // 弹框内的字段（相对于弹框根节点，但可全文档搜索）
    // 机型输入框（假设通过标签定位，若不准可修改）
    modelInput: "//*[contains(text(), '机型')]/following::input[1]",
    
    // 执行日期触发器（点击后会弹出日期选择器）
    execDateTrigger: "/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/span/span[2]",
    // 异地运行触发器
    remoteRunTrigger: "/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[6]/span/span/span/span[2]",
    // 任务性质触发器
    missionTypeTrigger: "/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/span/span[2]",
    // 注册号填充位置1（显示）
    regSpan: "/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span",
    // 注册号填充位置2（输入框）
    regInput: "/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span/span/input",
    // 起飞机场输入框
    depAirportInput: "//*[contains(text(), '起飞机场')]/following::input[1]",
    // 到达机场输入框（如果存在，需要填写）
    arrAirportInput: "//*[contains(text(), '到达机场')]/following::input[1]",
    // 提交/保存按钮（常见文本包含'确定'或'保存'）
    submitBtn: "//button[contains(text(), '确定')] | //button[contains(text(), '保存')] | //a[contains(text(), '确定')]",
}};

// ----------------------------- 核心业务函数 ---------------------------------
/**
 * 根据注册号获取机型
 */
function getModelByReg(reg) {{
    const map = {{
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60", "B658L": "GLF6", "B8105": "GLEX", "B8160": "GLF5"
    }};
    return map[reg] || "GLF4";
}}

/**
 * 设置日期（通过触发器打开日期面板并选择指定日期）
 * 注意：此版本简化处理，尝试直接查找日期输入框设置，若失败则尝试点击日期触发器并模拟点击日历。
 * 若您的系统日期控件复杂，可能需要手动调整此函数。
 */
async function setExecDate(dateStr) {{
    // 方式1：尝试直接寻找可见的日期输入框
    const dateInput = document.querySelector('input[type="date"], input[placeholder*="日期"], .date-input');
    if (dateInput && dateInput.value !== undefined) {{
        setInputValue(dateInput, dateStr);
        console.log(`✅ 直接设置日期输入框: ${{dateStr}}`);
        return true;
    }}
    // 方式2：点击触发器，然后尝试使用日期面板（简化版，假设日期面板包含标准年月日选择）
    const trigger = await waitForElement(XPATHS.execDateTrigger, 5000, true);
    if (!trigger) {{
        console.warn("未找到执行日期触发器，跳过日期填写");
        return false;
    }}
    trigger.click();
    await sleep(800);
    // 尝试在日期选择器中点击对应日期（需要解析 dateStr 的日）
    const day = parseInt(dateStr.split('-')[2], 10);
    // 查找包含了当日的单元格并点击（通常日期选择器表格中）
    const dayCell = document.evaluate(`//td[contains(@class, 'day') and text()='${{day}}']`, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (dayCell) {{
        dayCell.click();
        console.log(`✅ 已选择日期: ${{dateStr}}`);
        return true;
    }}
    console.warn("未能自动选择日期，请手动选择");
    return false;
}}

/**
 * 填写一条完整的飞行计划
 */
async function processOneRecord(record, index) {{
    console.log(`\\n========== 开始处理第 ${{index + 1}} 条计划 ==========`);
    console.log(`注册号: ${{record.reg}} | 起飞机场: ${{record.dep_airport}} | 到达机场: ${{record.arr_airport}} | 日期: ${{record.dep_date}}`);
    
    // 1. 点击新增按钮，打开弹框
    const addBtn = await waitForElement(XPATHS.addBtn, 10000, true);
    if (!addBtn) {{
        console.error("❌ 未找到新增按钮，请确认当前页面在列表页且XPath正确");
        return false;
    }}
    addBtn.click();
    await sleep(1500); // 等待弹框加载
    
    // 2. 填写机型
    const model = getModelByReg(record.reg);
    let modelInput = await waitForElement(XPATHS.modelInput, 8000, true);
    if (!modelInput) {{
        // 降级：尝试通过标签查找
        modelInput = document.evaluate("//input[@placeholder='机型'] | //input[contains(@name, 'model')]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }}
    if (modelInput) {{
        setInputValue(modelInput, model);
        console.log(`✅ 填写机型: ${{model}}`);
    }} else {{
        console.warn("⚠️ 未找到机型输入框，跳过机型填写");
    }}
    
    // 3. 设置执行日期
    await setExecDate(record.dep_date);
    
    // 4. 航空器是否异地运行 -> 选择“是”
    const remoteTrigger = await waitForElement(XPATHS.remoteRunTrigger, 5000, true);
    if (remoteTrigger) {{
        remoteTrigger.click();
        await sleep(500);
        // 尝试选择“是”选项（可能在下拉菜单中）
        const yesOption = document.evaluate("//li[contains(text(),'是')] | //span[contains(text(),'是')]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (yesOption) {{
            yesOption.click();
            console.log("✅ 已选择异地运行: 是");
        }} else {{
            console.warn("未找到'是'选项，可能已默认");
        }}
    }} else {{
        console.warn("未找到异地运行触发器");
    }}
    
    // 5. 任务性质：根据用途判断
    let missionText = "公务飞行";
    if (record.purpose && (record.purpose.includes("调机") || record.purpose.includes("维修"))) {{
        missionText = "调机飞行";
    }}
    const missionTrigger = await waitForElement(XPATHS.missionTypeTrigger, 5000, true);
    if (missionTrigger) {{
        missionTrigger.click();
        await sleep(500);
        // 输入任务性质文本（可能是可编辑div或input）
        let missionInput = document.activeElement;
        if (missionInput && (missionInput.tagName === 'INPUT' || missionInput.isContentEditable)) {{
            if (missionInput.isContentEditable) {{
                missionInput.innerText = missionText;
                missionInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }} else {{
                setInputValue(missionInput, missionText);
            }}
            console.log(`✅ 填写任务性质: ${{missionText}}`);
        }} else {{
            console.warn("未找到任务性质输入框，尝试直接设置值");
        }
    }}
    
    // 6. 填写飞机注册号（两个位置）
    const regSpan = await waitForElement(XPATHS.regSpan, 3000, true);
    if (regSpan) {{
        regSpan.innerText = record.reg;
        console.log(`✅ 填写注册号显示区: ${{record.reg}}`);
    }}
    const regInput = await waitForElement(XPATHS.regInput, 5000, true);
    if (regInput) {{
        setInputValue(regInput, record.reg);
        console.log(`✅ 填写注册号输入框: ${{record.reg}}`);
    }}
    
    // 7. 起飞机场
    const depInput = await waitForElement(XPATHS.depAirportInput, 5000, true);
    if (depInput) {{
        setInputValue(depInput, record.dep_airport);
        console.log(`✅ 填写起飞机场: ${{record.dep_airport}}`);
    }} else {{
        console.warn("未找到起飞机场输入框");
    }}
    
    // 8. 到达机场（额外补充，如需填写）
    const arrInput = await waitForElement(XPATHS.arrAirportInput, 5000, true);
    if (arrInput) {{
        setInputValue(arrInput, record.arr_airport);
        console.log(`✅ 填写到达机场: ${{record.arr_airport}}`);
    }} else {{
        console.warn("未找到到达机场输入框（可能不需要或已自动填充）");
    }}
    
    // 9. 提交保存
    const submitBtn = await waitForElement(XPATHS.submitBtn, 8000, true);
    if (submitBtn) {{
        submitBtn.click();
        console.log("🔘 已点击提交按钮，等待保存...");
        await sleep(2000);
        // 可选：等待弹框关闭，检测列表页“新增”按钮重新出现
        await waitForElement(XPATHS.addBtn, 10000, true);
        console.log(`✅ 第 ${{index + 1}} 条计划处理完成并已返回列表页`);
        return true;
    }} else {{
        console.error("❌ 未找到提交按钮，请手动检查");
        return false;
    }}
}}

// ----------------------------- 主执行流程 ---------------------------------
const flightRecords = {records_json};

async function runAutoEntry() {{
    console.log(`🚀 开始执行次日计划自动录入，共 ${{flightRecords.length}} 条计划`);
    for (let i = 0; i < flightRecords.length; i++) {{
        const success = await processOneRecord(flightRecords[i], i);
        if (!success) {{
            console.error(`❌ 第 ${{i+1}} 条处理失败，终止后续执行`);
            break;
        }}
        await sleep(1000); // 间隔一秒，避免过快
    }}
    console.log("🎉 所有次日计划处理完毕！");
}}

// 启动
runAutoEntry();
"""
    return script

# ---------- Streamlit 主逻辑 ----------
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=header_row)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        
        # 检查必要列
        required_cols = ["飞机注册号", "出发日期", "出发地", "到达地"]
        optional_cols = ["用途"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
            st.info(f"实际列名: {list(df.columns)}")
        else:
            # 只筛选出发日期 >= 今天（次日计划）？但用户上传的应该就是次日计划，直接全量使用
            # 转换日期格式
            df["出发日期"] = pd.to_datetime(df["出发日期"]).dt.date
            # 默认今天为基准，筛选明天及以后的（若需要严格次日可取消注释）
            # tomorrow = date.today() + timedelta(days=1)
            # df = df[df["出发日期"] >= tomorrow].copy()
            
            records = []
            for _, row in df.iterrows():
                reg = str(row["飞机注册号"]).strip()
                dep_date = row["出发日期"].strftime("%Y-%m-%d")
                dep_airport = str(row["出发地"]).strip()
                arr_airport = str(row["到达地"]).strip()
                purpose = str(row.get("用途", "")).strip() if "用途" in row else ""
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
            
            # 生成脚本
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
            1. 请确保已登录目标系统，并停留在「经营活动信息管理」列表页。
            2. 按 F12 打开开发者工具，切换到 Console（控制台）选项卡。
            3. 粘贴上面生成的脚本代码，按回车执行。
            4. 脚本将自动弹出新增弹框并逐条填写次日计划，每次提交后自动返回列表页处理下一条。
            5. 如遇到特定XPath与您的系统不一致，可修改脚本开头的 `XPATHS` 对象进行适配。
            """)
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传次日计划 Excel 文件开始生成脚本")

st.markdown("---")
st.caption("本工具根据次日计划 Excel 生成浏览器控制台脚本，实现自动录入飞行计划数据。支持机型自动映射、任务性质判断、日期填写等。")
