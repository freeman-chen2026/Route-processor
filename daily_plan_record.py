import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="当日/次日计划备案脚本生成器", layout="wide")
st.title("✈️ 当日/次日国内计划备案脚本生成器")
st.markdown("上传每日导出的 Excel 文件，自动生成浏览器控制台脚本，用于批量备案未匹配的当日/次日计划。")

# 机型映射规则（根据注册号前缀）
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
    for key, value in AIRCRAFT_TYPE_MAP.items():
        if reg.startswith(key):
            return value
    return "GLF4"  # 默认

uploaded_file = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name=0, header=1)
    st.success(f"文件加载成功，共 {len(df)} 条记录")

    required_cols = ["出发日期", "飞机注册号", "出发地", "到达地", "计划出发", "预计到达", "用途"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Excel 缺少以下列: {missing}")
        st.stop()

    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    df["出发日期_obj"] = pd.to_datetime(df["出发日期"], errors='coerce')
    df_filtered = df[df["出发日期_obj"].dt.date.isin([today, tomorrow])].copy()
    if df_filtered.empty:
        st.warning("没有找到当日或次日的飞行计划。")
        st.stop()

    st.info(f"共筛选出 {len(df_filtered)} 条当日/次日计划（今日: {(df_filtered['出发日期_obj'].dt.date == today).sum()}, 明日: {(df_filtered['出发日期_obj'].dt.date == tomorrow).sum()}）")
    st.subheader("📊 待处理的计划（当日/次日）")
    st.dataframe(df_filtered[["出发日期", "飞机注册号", "出发地", "到达地", "计划出发", "预计到达", "用途"]])

    # 准备数据供 JavaScript 使用
    records = df_filtered.to_dict(orient="records")
    for rec in records:
        # 删除不可 JSON 序列化的 Timestamp 字段
        rec.pop("出发日期_obj", None)
        # 转换日期格式为 YYYYMMDD
        rec["出发日期_yyyymmdd"] = pd.to_datetime(rec["出发日期"]).strftime("%Y%m%d")
        rec["计划出发_hhmm"] = rec["计划出发"].replace(":", "") if isinstance(rec["计划出发"], str) else ""
        rec["计划到达_hhmm"] = rec["预计到达"].replace(":", "") if isinstance(rec["预计到达"], str) else ""
        rec["机型"] = get_aircraft_type(rec["飞机注册号"])
        rec["任务性质"] = "调机飞行" if rec["用途"] in ["调机", "维修"] else "公务飞行"

    js_data = json.dumps(records, ensure_ascii=False, indent=2)

    # 生成 JavaScript 脚本（使用用户提供的所有精确 XPath，并修正弹窗检测）
    script = f"""
// ================= 自动生成的当日/次日计划备案脚本 =================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 需要比对的计划数: {len(df_filtered)}
// ================================================================

// ================= 配置区（使用用户提供的精确 XPath） =================
// 表格行 XPath（用于获取所有计划行）
const ROW_XPATH = '/html/body/div[1]/div[3]/div/div/div/div[2]/div[4]/div[2]/div/table/tbody/tr';
// 行内各字段的 CSS 选择器（相对于行）
const DATE_SELECTOR = 'td:nth-child(10) div';      // 执行日（格式 20260404）
const REG_SELECTOR = 'td:nth-child(8) div';        // 注册号
const DEP_AIRPORT_SELECTOR = 'td:nth-child(11) div'; // 起飞机场
const ARR_AIRPORT_SELECTOR = 'td:nth-child(14) div'; // 落地机场

// 新增按钮 XPath
const ADD_BTN_XPATH = '/html/body/div[1]/div[2]/div/table/tbody/tr/td[1]/a[1]/span/span[2]';

// 弹窗根元素 XPath（用于检测弹窗是否关闭）
const MODAL_ROOT_XPATH = '/html/body/div[2]';

// 弹窗内各字段的 XPath（用户提供）
const AIRCRAFT_TYPE_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[2]/span/span/input';
const DATE_PICKER_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/span/span[2]';
const REMOTE_RUN_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[6]/span/span/input';
const TASK_TYPE_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/input';
const REG_SPAN_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span';
const REG_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span/span/input';
const DEP_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[2]/span/span/input';
const ARR_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[8]/span/span/input';
const DEP_TIME_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[4]/span/span/input';
const ARR_TIME_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[6]/span/span/input';

// 从 Excel 提取的待比对计划
const pendingPlans = {js_data};

// ================= 辅助函数 =================
function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

// 等待元素（XPath）
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

// 设置输入框的值
function setInputValue(el, value) {{
    if (!el) return false;
    el.value = value;
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    el.blur();
    return true;
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

// 获取网页中已存在的计划（用于比对）
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

// 判断计划是否已存在
function isPlanExists(plan, existingPlans) {{
    return existingPlans.some(p => 
        p.date === plan.出发日期_yyyymmdd &&
        p.reg === plan.飞机注册号 &&
        p.dep === plan.出发地 &&
        p.arr === plan.到达地
    );
}}

// 填写弹窗内的表单（等待用户手动点击“保存”）
async function fillAndWait(plan) {{
    console.log(`\\n🔧 开始备案计划：${{plan.飞机注册号}} ${{plan.出发地}} -> ${{plan.到达地}}`);

    // 1. 点击“新增”
    if (!(await clickElement(ADD_BTN_XPATH))) return false;
    await sleep(1000); // 等待弹窗出现

    // 2. 填写机型
    const aircraftInput = await waitForElement(AIRCRAFT_TYPE_XPATH, 10000);
    if (aircraftInput) {{
        setInputValue(aircraftInput, plan.机型);
        console.log(`📝 已填写机型: ${{plan.机型}}`);
    }} else {{
        console.warn('未找到机型输入框，跳过');
    }}

    // 3. 选择日期（点击日期选择器）
    await clickElement(DATE_PICKER_XPATH);
    await sleep(500);
    // 尝试直接设置日期输入框（如果存在）
    const dateInput = document.querySelector('input[type="date"]');
    if (dateInput) {{
        setInputValue(dateInput, plan.出发日期); // 格式 YYYY-MM-DD
        console.log(`📅 已设置日期: ${{plan.出发日期}}`);
    }} else {{
        console.warn('无法自动选择日期，请手动选择日期后继续');
        // 等待用户手动选择日期（简单等待5秒）
        await sleep(5000);
    }}

    // 4. 本计划航空器是否异地运行：直接填入"是"
    const remoteInput = await waitForElement(REMOTE_RUN_INPUT_XPATH, 5000);
    if (remoteInput) {{
        setInputValue(remoteInput, '是');
        console.log('✅ 已填写异地运行: 是');
    }} else {{
        console.warn('未找到异地运行输入框，请手动填写');
    }}

    // 5. 任务性质：直接输入
    const taskInput = await waitForElement(TASK_TYPE_INPUT_XPATH, 5000);
    if (taskInput) {{
        setInputValue(taskInput, plan.任务性质);
        console.log(`📝 已填写任务性质: ${{plan.任务性质}}`);
    }} else {{
        console.warn('未找到任务性质输入框，请手动填写');
    }}

    // 6. 填写注册号（两处）
    const regSpan = await waitForElement(REG_SPAN_XPATH, 5000);
    if (regSpan) setInputValue(regSpan, plan.飞机注册号);
    const regInput = await waitForElement(REG_INPUT_XPATH, 5000);
    if (regInput) setInputValue(regInput, plan.飞机注册号);

    // 7. 起飞机场
    const depInput = await waitForElement(DEP_INPUT_XPATH, 5000);
    if (depInput) setInputValue(depInput, plan.出发地);

    // 8. 落地机场
    const arrInput = await waitForElement(ARR_INPUT_XPATH, 5000);
    if (arrInput) setInputValue(arrInput, plan.到达地);

    // 9. 起飞时间
    const depTimeInput = await waitForElement(DEP_TIME_INPUT_XPATH, 5000);
    if (depTimeInput) setInputValue(depTimeInput, plan.计划出发_hhmm);

    // 10. 落地时间
    const arrTimeInput = await waitForElement(ARR_TIME_INPUT_XPATH, 5000);
    if (arrTimeInput) setInputValue(arrTimeInput, plan.计划到达_hhmm);

    console.log('✅ 表单填写完成，请手动点击“保存”按钮。');
    // 等待弹窗根元素消失（用户点击保存后弹窗关闭）
    while (true) {{
        await sleep(2000);
        const modalRoot = document.evaluate(MODAL_ROOT_XPATH, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!modalRoot) {{
            console.log('✅ 弹窗已关闭，继续下一条');
            break;
        }}
    }}
    return true;
}}

// ================= 主流程 =================
(async () => {{
    console.log('🚀 开始执行备案流程...');

    // 获取网页中已有的计划
    const existingPlans = getExistingPlans();
    console.log(`📋 网页中已有 ${{existingPlans.length}} 条计划`);

    // 筛选需要备案的计划（未匹配）
    const toRecord = pendingPlans.filter(plan => !isPlanExists(plan, existingPlans));
    console.log(`📊 需要备案的计划数: ${{toRecord.length}}`);

    if (toRecord.length === 0) {{
        console.log('🎉 所有计划均已备案，无需操作。');
        return;
    }}

    // 依次处理
    for (let i = 0; i < toRecord.length; i++) {{
        console.log(`\\n========== 处理第 ${{i+1}}/${{toRecord.length}} 条计划 ==========`);
        const success = await fillAndWait(toRecord[i]);
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
