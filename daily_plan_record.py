import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="当日/次日计划备案脚本生成器", layout="wide")
st.title("✈️ 当日/次日国内计划备案脚本生成器")
st.markdown("上传每日导出的 Excel 文件，自动生成浏览器控制台脚本，用于批量备案未匹配的当日/次日计划。")

# 机型映射规则
AIRCRAFT_TYPE_MAP = {
    "B652Q": "GLF4",
    "B652R": "GLF4",
    "B652S": "GLF4",
    "B8262": "GLF4",
    "B3926": "LJ60",
    "B658L": "GLF6",
    "B8105": "GLEX",
    "B8160": "GLF5",
}

def get_aircraft_type(reg: str) -> str:
    """根据注册号前缀返回机型"""
    for key, value in AIRCRAFT_TYPE_MAP.items():
        if reg.startswith(key):
            return value
    return "GLF4"  # 默认

# 读取 Excel
uploaded_file = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name=0, header=1)
    st.success(f"文件加载成功，共 {len(df)} 条记录")

    # 必要的列检查
    required_cols = ["出发日期", "飞机注册号", "出发地", "到达地", "计划出发", "计划到达", "用途"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Excel 缺少以下列: {missing}")
        st.stop()

    # 获取今天的日期和明天的日期
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # 筛选当日和次日的计划
    df["出发日期_obj"] = pd.to_datetime(df["出发日期"], errors='coerce')
    df_filtered = df[df["出发日期_obj"].dt.date.isin([today, tomorrow])].copy()
    if df_filtered.empty:
        st.warning("没有找到当日或次日的飞行计划。")
        st.stop()

    st.info(f"共筛选出 {len(df_filtered)} 条当日/次日计划（今日: {(df_filtered['出发日期_obj'].dt.date == today).sum()}, 明日: {(df_filtered['出发日期_obj'].dt.date == tomorrow).sum()}）")

    # 显示预览
    st.subheader("📊 待处理的计划（当日/次日）")
    st.dataframe(df_filtered[["出发日期", "飞机注册号", "出发地", "到达地", "计划出发", "计划到达", "用途"]])

    # 准备数据供 JavaScript 使用
    records = df_filtered.to_dict(orient="records")
    for rec in records:
        # 转换日期格式为 YYYYMMDD
        rec["出发日期_yyyymmdd"] = rec["出发日期_obj"].strftime("%Y%m%d")
        # 转换起飞/落地时间为 HHMM
        rec["计划出发_hhmm"] = rec["计划出发"].replace(":", "") if isinstance(rec["计划出发"], str) else ""
        rec["计划到达_hhmm"] = rec["计划到达"].replace(":", "") if isinstance(rec["计划到达"], str) else ""
        # 映射机型
        rec["机型"] = get_aircraft_type(rec["飞机注册号"])
        # 任务性质
        rec["任务性质"] = "调机飞行" if rec["用途"] in ["调机", "维修"] else "公务飞行"

    js_data = json.dumps(records, ensure_ascii=False, indent=2)

    # 生成 JavaScript 脚本
    script = f"""
// ================= 自动生成的当日/次日计划备案脚本 =================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 需要备案的计划数: {len(df_filtered)}
// ================================================================

// ================= 配置区 =================
// 网页中表格行 XPath（注意：使用实际的 XPath，这里根据您提供的结构）
const ROW_XPATH = '/html/body/div[1]/div[3]/div/div/div/div[2]/div[4]/div[2]/div/table/tbody/tr';
// 各列的选择器（相对于行）
const DATE_SELECTOR = 'td:nth-child(10) div';      // 执行日
const REG_SELECTOR = 'td:nth-child(8) div';        // 注册号
const DEP_AIRPORT_SELECTOR = 'td:nth-child(11) div'; // 起飞机场
const ARR_AIRPORT_SELECTOR = 'td:nth-child(14) div'; // 落地机场

// 从 Excel 提取的待备案计划（已过滤当日/次日）
const pendingPlans = {js_data};

// ================= 辅助函数 =================
function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

// 等待元素出现（XPath）
async function waitForElement(xpath, timeout = 15000) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (el) return el;
        await sleep(300);
    }}
    console.warn(`⚠️ 等待元素超时: ${{xpath}}`);
    return null;
}}

// 等待元素出现（CSS 选择器）
async function waitForSelector(selector, timeout = 15000) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const el = document.querySelector(selector);
        if (el) return el;
        await sleep(300);
    }}
    return null;
}}

// 获取网页中所有已存在的计划（用于比对）
function getExistingPlans() {{
    const rows = document.evaluate(ROW_XPATH, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const plans = [];
    for (let i = 0; i < rows.snapshotLength; i++) {{
        const row = rows.snapshotItem(i);
        const dateEl = row.querySelector(DATE_SELECTOR);
        const regEl = row.querySelector(REG_SELECTOR);
        const depEl = row.querySelector(DEP_AIRPORT_SELECTOR);
        const arrEl = row.querySelector(ARR_AIRPORT_SELECTOR);
        if (dateEl && regEl && depEl && arrEl) {{
            plans.push({{
                date: dateEl.innerText.trim(),
                reg: regEl.innerText.trim(),
                dep: depEl.innerText.trim(),
                arr: arrEl.innerText.trim(),
            }});
        }}
    }}
    return plans;
}}

// 判断一个计划是否已存在于网页中
function isPlanExists(plan, existingPlans) {{
    return existingPlans.some(p => 
        p.date === plan.出发日期_yyyymmdd &&
        p.reg === plan.飞机注册号 &&
        p.dep === plan.出发地 &&
        p.arr === plan.到达地
    );
}}

// 填写输入框（支持 input, textarea）
function setInputValue(el, value) {{
    if (!el) return false;
    el.value = value;
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    el.blur();
    return true;
}}

// 设置 select 选择指定文本
async function setSelectValue(selectEl, valueText) {{
    if (!selectEl) return false;
    for (let i = 0; i < selectEl.options.length; i++) {{
        const opt = selectEl.options[i];
        if (opt.text === valueText || opt.text.includes(valueText)) {{
            selectEl.selectedIndex = i;
            selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await sleep(300);
            console.log(`✅ 已选择 "${{valueText}}"`);
            return true;
        }}
    }}
    console.warn(`⚠️ 未找到选项 "${{valueText}}"`);
    return false;
}}

// 点击元素
async function clickElement(xpath, timeout = 10000) {{
    const el = await waitForElement(xpath, timeout);
    if (el) {{
        el.click();
        await sleep(500);
        return true;
    }}
    console.error(`❌ 未找到元素: ${{xpath}}`);
    return false;
}}

// 备案单个计划
async function recordOnePlan(plan) {{
    console.log(`\\n🔧 开始备案计划：${{plan.飞机注册号}} ${{plan.出发地}} -> ${{plan.到达地}}`);

    // 1. 点击“新增”
    const addBtnXPath = '/html/body/div[1]/div[2]/div/table/tbody/tr/td[1]/a[1]/span/span[2]';
    if (!(await clickElement(addBtnXPath))) return false;
    await sleep(1000); // 等待弹框出现

    // 2. 选择机型（弹框内第一个选择框？实际是输入框还是选择框？根据描述，需要输入机型文本）
    // 机型输入框 XPath（根据您提供的第2步描述，可能是一个输入框，但未给具体XPath，我们假设是一个输入框，需定位）
    // 由于您未提供弹框内具体字段的 XPath，这里使用通用方法：根据 label 定位或使用已知结构。
    // 以下为示例，实际需要您根据网页调整。如果弹框内字段顺序固定，可以按顺序获取 input。
    // 这里假设弹框内第一个输入框是机型输入框。
    const modal = document.querySelector('div[role="dialog"]'); // 或者更精确的选择器
    if (!modal) {{
        console.error('未找到弹框');
        return false;
    }}
    const aircraftTypeInput = modal.querySelector('input'); // 假设第一个 input 是机型
    if (aircraftTypeInput) {{
        setInputValue(aircraftTypeInput, plan.机型);
        console.log(`📝 已填写机型: ${{plan.机型}}`);
    }} else {{
        console.warn('未找到机型输入框，请检查');
    }}

    // 3. 选择日期（点击日期选择器，然后选择日期）
    const datePickerXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/span/span[2]';
    if (!(await clickElement(datePickerXPath))) return false;
    // 等待日期选择器出现，然后选择日期（需要将 plan.出发日期 转换为 YYYY-MM-DD 格式，然后点击对应日期）
    // 这里简化：假设日期选择器是一个 input，可以直接设置值，或者需要点击日期。由于 XPath 指向的是一个 span，可能不是直接输入框。
    // 根据需求，选择日期需要点击后出现日历，选择具体日期。我们暂时用直接设置值的方式，如果不行需要调整。
    // 先尝试找到日期输入框（可能是一个 input）
    const dateInput = modal.querySelector('input[type="date"]') || modal.querySelector('input[placeholder*="日期"]');
    if (dateInput) {{
        setInputValue(dateInput, plan.出发日期); // 假设输入框接受 YYYY-MM-DD
    }} else {{
        // 如果不行，可能需要模拟点击日历，这里暂不实现，请根据实际情况修改
        console.warn('无法自动选择日期，请手动选择');
    }}

    // 4. 本计划航空器是否异地运行选择"是"
    const remoteRunXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[6]/span/span/span/span[2]';
    if (!(await clickElement(remoteRunXPath))) return false;
    // 等待下拉选择框出现，选择"是"
    await sleep(500);
    const remoteSelect = modal.querySelector('select'); // 假设是 select，需要定位实际的下拉框
    if (remoteSelect) await setSelectValue(remoteSelect, '是');
    else console.warn('未找到异地运行下拉框');

    // 5. 任务性质
    const taskTypeXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/span/span[2]';
    if (!(await clickElement(taskTypeXPath))) return false;
    await sleep(500);
    const taskInput = modal.querySelector('input[placeholder*="任务"]') || modal.querySelector('input');
    if (taskInput) setInputValue(taskInput, plan.任务性质);
    else console.warn('未找到任务性质输入框');

    // 6. 填写飞机注册号（两个地方）
    const reg1Span = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span';
    const reg2Input = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span/span/input';
    const regSpan = await waitForElement(reg1Span, 5000);
    if (regSpan) setInputValue(regSpan, plan.飞机注册号);
    const regInput = await waitForElement(reg2Input, 5000);
    if (regInput) setInputValue(regInput, plan.飞机注册号);

    // 7. 起飞机场
    const depInputXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[2]/span/span/input'; // 根据您提供的第7步，但您给的XPath不完整，需要补全
    // 实际第7步 XPath 您未提供完整，这里使用示例，请根据实际调整
    const depInput = await waitForElement('/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[2]/span/span/input', 5000);
    if (depInput) setInputValue(depInput, plan.出发地);

    // 8. 落地机场
    const arrInputXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[8]/span/span/input';
    const arrInput = await waitForElement(arrInputXPath, 5000);
    if (arrInput) setInputValue(arrInput, plan.到达地);

    // 9. 起飞时间
    const depTimeInputXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[4]/span/span/input';
    const depTimeInput = await waitForElement(depTimeInputXPath, 5000);
    if (depTimeInput) setInputValue(depTimeInput, plan.计划出发_hhmm);

    // 10. 落地时间
    const arrTimeInputXPath = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[6]/span/span/input';
    const arrTimeInput = await waitForElement(arrTimeInputXPath, 5000);
    if (arrTimeInput) setInputValue(arrTimeInput, plan.计划到达_hhmm);

    console.log('✅ 表单填写完成，请手动点击“保存”按钮。');
    // 等待用户点击保存（需要检测弹框关闭或等待下一个循环）
    // 这里简单地等待一段时间，实际应等待弹框消失或用户手动触发继续
    // 由于需要等待用户点击保存后继续，我们采用一个无限等待，直到弹框消失或检测到某个条件
    // 更优雅的做法：等待弹框消失（比如通过 mutationObserver 或轮询）
    console.log('⏳ 等待您点击“保存”后继续...');
    while (true) {{
        await sleep(2000);
        const modalStillExists = document.querySelector('div[role="dialog"]');
        if (!modalStillExists) {{
            console.log('✅ 弹框已关闭，继续下一条');
            break;
        }}
    }}
    return true;
}}

// ================= 主流程 =================
(async () => {{
    console.log('🚀 开始执行备案流程...');

    // 1. 获取网页中已存在的计划
    const existingPlans = getExistingPlans();
    console.log(`📋 网页中已有 ${{existingPlans.length}} 条计划`);

    // 2. 筛选出需要备案的计划（未匹配的）
    const toRecord = pendingPlans.filter(plan => !isPlanExists(plan, existingPlans));
    console.log(`📊 需要备案的计划数: ${{toRecord.length}}`);

    if (toRecord.length === 0) {{
        console.log('🎉 所有计划均已备案，无需操作。');
        return;
    }}

    // 3. 依次备案
    for (let i = 0; i < toRecord.length; i++) {{
        console.log(`\\n========== 处理第 ${{i+1}}/${{toRecord.length}} 条计划 ==========`);
        const success = await recordOnePlan(toRecord[i]);
        if (!success) {{
            console.error(`❌ 第 ${{i+1}} 条计划备案失败，停止后续。`);
            break;
        }}
        await sleep(1000);
    }}

    console.log('\\n🎉 所有需要备案的计划处理完毕！');
}})();
"""

    st.subheader("📜 生成的 JavaScript 脚本")
    st.code(script, language="javascript")
    st.info("复制以上代码，在目标网页（当日/次日计划列表页）按 F12 打开控制台，粘贴并回车执行。脚本将自动比对并填写未备案的计划，每填完一条后等待您手动点击“保存”，然后继续下一条。")

    st.download_button(
        label="💾 下载脚本文件 (.js)",
        data=script,
        file_name="daily_plan_record.js",
        mime="application/javascript"
    )
else:
    st.info("请上传 Excel 文件以开始生成脚本。")
