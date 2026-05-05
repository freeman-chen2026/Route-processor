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
    "B8309": "GLF5",   # 新增
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
    display_cols = ["出发日期", "飞机注册号", "出发地", "到达地", "计划出发", "预计到达", "用途"]
    if "航班号" in df.columns:
        display_cols.insert(1, "航班号")
    st.dataframe(df_filtered[display_cols])

    # 准备数据供 JavaScript 使用
    records = df_filtered.to_dict(orient="records")
    for rec in records:
        rec.pop("出发日期_obj", None)
        rec["出发日期_yyyymmdd"] = pd.to_datetime(rec["出发日期"]).strftime("%Y%m%d")
        rec["计划出发_hhmm"] = rec["计划出发"].replace(":", "") if isinstance(rec["计划出发"], str) else ""
        rec["计划到达_hhmm"] = rec["预计到达"].replace(":", "") if isinstance(rec["预计到达"], str) else ""
        rec["机型"] = get_aircraft_type(rec["飞机注册号"])
        rec["任务性质"] = "调机飞行" if rec["用途"] in ["调机", "维修"] else "公务飞行"

    js_data = json.dumps(records, ensure_ascii=False, indent=2)

    script = f"""
// ================= 自动生成的当日/次日计划备案脚本 =================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 需要比对的计划数: {len(df_filtered)}
// ================================================================

// ================= 配置区 =================
const ROW_XPATH = '/html/body/div[1]/div[3]/div/div/div/div[2]/div[4]/div[2]/div/table/tbody/tr';
const DATE_SELECTOR = 'td:nth-child(10) div';
const REG_SELECTOR = 'td:nth-child(8) div';
const DEP_AIRPORT_SELECTOR = 'td:nth-child(11) div';
const ARR_AIRPORT_SELECTOR = 'td:nth-child(14) div';
const ADD_BTN_XPATH = '/html/body/div[1]/div[2]/div/table/tbody/tr/td[1]/a[1]/span/span[2]';
const MODAL_ROOT_XPATH = '/html/body/div[2]';
const AIRCRAFT_TYPE_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[2]/span/span/input';
const DATE_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[4]/span/span/input';
const REMOTE_RUN_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[2]/li[6]/span/span/input';
const TASK_TYPE_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[6]/span/span/input';
const FLIGHT_NO_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span/span/input';
const REG_SPAN_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[8]/span';
const REG_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[1]/li[10]/span/span/input';
const DEP_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[2]/span/span/input';
const ARR_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[8]/span/span/input';
const DEP_TIME_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[4]/span/span/input';
const ARR_TIME_INPUT_XPATH = '/html/body/div[2]/div/div[2]/div[2]/div/ul[3]/li[6]/span/span/input';

const pendingPlans = {js_data};

// ================= 辅助函数 =================
function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}
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
function setInputValue(el, value) {{
    if (!el) return false;
    el.value = value;
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    el.blur();
    return true;
}}
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
function isPlanExists(plan, existingPlans) {{
    return existingPlans.some(p => 
        p.date === plan.出发日期_yyyymmdd &&
        p.reg === plan.飞机注册号 &&
        p.dep === plan.出发地 &&
        p.arr === plan.到达地
    );
}}

// ================= 改进的弹窗关闭检测 =================
async function waitForModalClose() {{
    console.log('✅ 表单填写完成，请手动点击“保存”按钮。');
    console.log('⏳ 等待弹窗关闭（可切换到其他页面，脚本会继续等待）...');
    console.log('💡 如果弹窗已关闭但脚本未继续，请在控制台输入 window.__forceContinue = true 并回车。');
    
    window.__forceContinue = false;
    
    while (true) {{
        await sleep(2000);
        
        if (window.__forceContinue) {{
            console.log('🔓 手动强制继续，跳过弹窗检测');
            window.__forceContinue = false;
            break;
        }}
        
        const modalRoot = document.evaluate(MODAL_ROOT_XPATH, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!modalRoot) {{
            console.log('✅ 弹窗已关闭（元素不存在），继续下一条');
            break;
        }}
        
        const style = window.getComputedStyle(modalRoot);
        const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        if (!isVisible) {{
            console.log('✅ 弹窗已关闭（不可见），继续下一条');
            break;
        }}
    }}
    return true;
}}

// ================= 填写单条计划 =================
async function fillAndWait(plan) {{
    console.log(`\\n🔧 开始备案计划：${{plan.飞机注册号}} ${{plan.出发地}} -> ${{plan.到达地}}`);
    if (!(await clickElement(ADD_BTN_XPATH))) return false;
    await sleep(1000);

    const aircraftInput = await waitForElement(AIRCRAFT_TYPE_XPATH, 10000);
    if (aircraftInput) {{
        setInputValue(aircraftInput, plan.机型);
        console.log(`📝 已填写机型: ${{plan.机型}}`);
    }}
    const dateInput = await waitForElement(DATE_INPUT_XPATH, 10000);
    if (dateInput) {{
        setInputValue(dateInput, plan.出发日期);
        console.log(`📅 已填写日期: ${{plan.出发日期}}`);
    }}
    const remoteInput = await waitForElement(REMOTE_RUN_INPUT_XPATH, 5000);
    if (remoteInput) {{
        setInputValue(remoteInput, '是');
        console.log('✅ 已填写异地运行: 是');
    }}
    const taskInput = await waitForElement(TASK_TYPE_INPUT_XPATH, 5000);
    if (taskInput) {{
        setInputValue(taskInput, plan.任务性质);
        console.log(`📝 已填写任务性质: ${{plan.任务性质}}`);
    }}
    const flightNoInput = await waitForElement(FLIGHT_NO_XPATH, 5000);
    if (flightNoInput) {{
        setInputValue(flightNoInput, plan.飞机注册号);
        console.log(`📝 已填写航班号/注册号: ${{plan.飞机注册号}}`);
    }}
    const regSpan = await waitForElement(REG_SPAN_XPATH, 5000);
    if (regSpan) setInputValue(regSpan, plan.飞机注册号);
    const regInput = await waitForElement(REG_INPUT_XPATH, 5000);
    if (regInput) setInputValue(regInput, plan.飞机注册号);
    const depInput = await waitForElement(DEP_INPUT_XPATH, 5000);
    if (depInput) setInputValue(depInput, plan.出发地);
    const arrInput = await waitForElement(ARR_INPUT_XPATH, 5000);
    if (arrInput) setInputValue(arrInput, plan.到达地);
    const depTimeInput = await waitForElement(DEP_TIME_INPUT_XPATH, 5000);
    if (depTimeInput) setInputValue(depTimeInput, plan.计划出发_hhmm);
    const arrTimeInput = await waitForElement(ARR_TIME_INPUT_XPATH, 5000);
    if (arrTimeInput) setInputValue(arrTimeInput, plan.计划到达_hhmm);

    await waitForModalClose();
    return true;
}}

// ================= 主流程 =================
(async () => {{
    console.log('🚀 开始执行备案流程...');
    const existingPlans = getExistingPlans();
    console.log(`📋 网页中已有 ${{existingPlans.length}} 条计划`);
    const toRecord = pendingPlans.filter(plan => !isPlanExists(plan, existingPlans));
    console.log(`📊 需要备案的计划数: ${{toRecord.length}}`);
    if (toRecord.length === 0) {{
        console.log('🎉 所有计划均已备案，无需操作。');
        return;
    }}
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
    # 使用普通 pre/code 避免动态导入错误
    st.markdown(f"<div style='background:#f0f2f6;padding:1rem;border-radius:0.5rem;overflow-x:auto;font-family:monospace;font-size:0.9rem;'><pre>{script}</pre></div>", unsafe_allow_html=True)
    st.info("复制以上代码，在目标网页（当日/次日计划列表页）按 F12 打开控制台，粘贴并回车执行。脚本将自动比对并填写未备案的计划，每填完一条后等待您手动点击“保存”，然后继续下一条。")
    st.download_button(
        label="💾 下载脚本文件 (.js)",
        data=script,
        file_name="daily_plan_record.js",
        mime="application/javascript"
    )
else:
    st.info("请上传 Excel 文件以开始生成脚本。")
