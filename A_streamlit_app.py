# streamlit_app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime, date

st.set_page_config(page_title="飞行计划自动化脚本生成器（当日+次日）", layout="wide")
st.title("✈️ 飞行计划自动化脚本生成器（当日 + 次日）")
st.markdown("""
1. 上传 Excel 文件（包含飞行计划）  
2. 自动根据“出发日期”区分：**当日计划（出发日期等于今天）** 和 **次日计划（出发日期晚于今天）**  
3. 生成 JavaScript 脚本，先处理当日计划（匹配列表并填写实际数据），再填报次日计划（新增备案）。  
> **注意**：请确保 Excel 中有“出发日期”列，格式为 YYYY-MM-DD。
""")

# ---------- 当日数据处理脚本模板（可编辑） ----------
DEFAULT_STEP1_TEMPLATE = """
// ================= 当日数据处理脚本 =================
// 用于在列表中查找匹配的飞行记录，并填写实际到达时间等信息。
// 请根据实际页面结构调整以下选择器：
//   ROW_SELECTOR: 表格行选择器
//   REG_SELECTOR: 飞机注册号所在列的选择器
//   SEGMENT_SELECTOR: 航段信息（出发城市->到达城市）所在列的选择器
//   EDIT_BUTTON_SELECTOR: 编辑按钮的选择器（如 button:contains("编辑")）
//   表单内字段选择器（见 fillActualArrival 函数）

// 配置区
const ROW_SELECTOR = 'table tbody:nth-of-type(2) tr';    // 表格行选择器
const REG_SELECTOR = 'td:nth-child(6) div';              // 飞机注册号所在列
const SEGMENT_SELECTOR = 'td:nth-child(7) div';          // 航段信息列（出发城市->到达城市）
const EDIT_BUTTON_SELECTOR = 'button:contains("编辑")';  // 编辑按钮选择器

// 从 Excel 提取的数据（当日计划）
const excelData = __EXCEL_DATA__;

// ================= 辅助函数 =================
async function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function getCurrentDoc() {
    const iframeSelectors = ['#main', 'iframe[id="main"]', 'iframe[name="main"]', 'iframe'];
    let iframe = null;
    for (let sel of iframeSelectors) {
        iframe = document.querySelector(sel);
        if (iframe) break;
    }
    if (!iframe) {
        console.warn('未找到 iframe');
        return null;
    }
    let doc = iframe.contentDocument;
    while (!doc || !doc.querySelector('body')) {
        await sleep(200);
        doc = iframe.contentDocument;
    }
    return doc;
}

async function waitForElement(selector, timeout = 15000, isXPath = false) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const doc = await getCurrentDoc();
        if (!doc) {
            await sleep(500);
            continue;
        }
        let el;
        if (isXPath) {
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        } else {
            el = doc.querySelector(selector);
        }
        if (el) return el;
        await sleep(500);
    }
    console.warn(`等待元素超时: ${selector}`);
    return null;
}

async function clickEditButton(row) {
    const editBtn = row.querySelector(EDIT_BUTTON_SELECTOR);
    if (!editBtn) {
        console.warn('未找到编辑按钮');
        return false;
    }
    editBtn.click();
    await sleep(1000);
    return true;
}

async function fillActualArrival(record) {
    const doc = await getCurrentDoc();
    if (!doc) return false;
    // 实际到达输入框（请根据实际页面调整）
    const actualArrivalInput = doc.querySelector('#actualArrival') || 
                               doc.evaluate('//*[contains(text(), "实际到达")]/following-sibling::*//input', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (actualArrivalInput) {
        actualArrivalInput.value = record.实际到达 || '';
        actualArrivalInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log(`已填入实际到达时间: ${record.实际到达}`);
    } else {
        console.warn('未找到实际到达输入框，跳过该字段');
    }
    // 实际出发输入框（可选）
    const actualDepartureInput = doc.querySelector('#actualDeparture') ||
                                 doc.evaluate('//*[contains(text(), "实际出发")]/following-sibling::*//input', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (actualDepartureInput && record.实际出发) {
        actualDepartureInput.value = record.实际出发;
        actualDepartureInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    // 实际飞行时间输入框（可选）
    const actualFlightTimeInput = doc.querySelector('#actualFlightTime') ||
                                  doc.evaluate('//*[contains(text(), "实际飞行时间")]/following-sibling::*//input', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (actualFlightTimeInput && record.实际飞行时间) {
        actualFlightTimeInput.value = record.实际飞行时间;
        actualFlightTimeInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    // 提交保存按钮
    const submitBtn = doc.evaluate('//button[contains(text(), "保存")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue ||
                      doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (submitBtn) {
        submitBtn.click();
        console.log('已提交保存');
        await sleep(2000);
        await waitForElement('input.query.yuanjiao', 15000);
        return true;
    }
    console.warn('未找到保存按钮');
    return false;
}

async function processOnePlan(row, matchedExcel) {
    console.log(`处理匹配计划: ${matchedExcel.飞机注册号} ${matchedExcel.出发城市} -> ${matchedExcel.到达城市}`);
    if (!await clickEditButton(row)) {
        console.error('无法点击编辑按钮，跳过');
        return false;
    }
    const success = await fillActualArrival(matchedExcel);
    if (!success) {
        console.error('填写失败');
    }
    return success;
}

async function findAllMatches() {
    const doc = await getCurrentDoc();
    if (!doc) return [];
    const rows = doc.querySelectorAll(ROW_SELECTOR);
    const matches = [];
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const regCell = row.querySelector(REG_SELECTOR);
        const segmentCell = row.querySelector(SEGMENT_SELECTOR);
        if (!regCell || !segmentCell) continue;
        const reg = regCell.innerText.trim();
        const segment = segmentCell.innerText.trim();
        for (const record of excelData) {
            const excelReg = record.飞机注册号;
            const excelSegment = `${record.出发城市} -> ${record.到达城市}`;
            if (reg === excelReg && segment === excelSegment) {
                matches.push({ row, matchedExcel: record });
                break;
            }
        }
    }
    console.log(`找到 ${matches.length} 个匹配计划`);
    return matches;
}

async function processToday() {
    console.log('🚀 开始执行当日数据处理流程...');
    const matches = await findAllMatches();
    if (matches.length === 0) {
        console.warn('⚠️ 没有找到任何匹配的计划，跳过当日数据处理');
        return;
    }
    for (let i = 0; i < matches.length; i++) {
        const { row, matchedExcel } = matches[i];
        console.log(`\\n========== 处理第 ${i+1}/${matches.length} 个匹配计划 ==========`);
        try {
            const success = await processOnePlan(row, matchedExcel);
            if (!success) {
                console.error(`⚠️ 第 ${i+1} 个计划处理失败，跳过继续下一个...`);
            } else {
                console.log(`✅ 第 ${i+1} 个计划处理完成并已返回列表页。`);
            }
        } catch (err) {
            console.error(`处理第 ${i+1} 个计划时发生异常:`, err);
        }
    }
    console.log('🎉 当日数据处理完成！');
}
"""

# ---------- 次日计划填报脚本（与之前相同，省略，实际使用时保持完整） ----------
# 为节省篇幅，此处仅作示意，实际部署时请将您稳定的次日脚本粘贴过来
# 由于之前已经提供过完整的次日脚本，这里重复使用 STEP2_SCRIPT_TEMPLATE（需复制完整内容）
# 注意：此模板中 __FLIGHT_RECORDS__ 占位符将被替换

# 为了代码简洁，我们复用之前已经定义好的 STEP2_SCRIPT_TEMPLATE（假设它在代码中已定义）
# 如果是在这个文件中，需要将完整的次日脚本粘贴到下面的字符串中。
# 由于之前已提供过完整次日脚本，此处不再重复，实际使用时请将您的次日脚本内容复制到 STEP2_SCRIPT_TEMPLATE 变量中。

# 以下为次日脚本的占位符，实际部署时请替换为真实内容
STEP2_SCRIPT_TEMPLATE = """
// 请将您完整的次日计划填报脚本粘贴在此处，并保留 __FLIGHT_RECORDS__ 和 __DATETIME__ 等占位符
// 例如：
// async function processRecord(record) { ... }
// async function processTomorrow() { ... }
// 等等
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
    # 生成当日数据的 JSON（只包含需要匹配的字段）
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
    today_script = step1_template.replace("__EXCEL_DATA__", today_json)
    today_script = today_script.replace("__DATETIME__", now)
    today_script = today_script.replace("__COUNT__", str(len(df_today)))

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
uploaded_file = st.file_uploader("📂 上传 Excel 文件（包含飞行计划）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=1)
        df.columns = df.columns.str.strip()
        st.success("文件上传成功！")
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())

        # 获取今天的日期（只比较日期，忽略时间）
        today_date = date.today()
        if "出发日期" in df.columns:
            # 将出发日期列转换为 datetime，并提取日期部分
            df["出发日期_dt"] = pd.to_datetime(df["出发日期"]).dt.date
            df_today = df[df["出发日期_dt"] == today_date].copy()
            df_tomorrow = df[df["出发日期_dt"] > today_date].copy()
            # 删除辅助列
            df_today.drop(columns=["出发日期_dt"], inplace=True)
            df_tomorrow.drop(columns=["出发日期_dt"], inplace=True)
        else:
            st.error("Excel 中缺少“出发日期”列，无法区分当日和次日计划")
            st.stop()

        st.info(f"✅ 当日记录数（出发日期={today_date}）: {len(df_today)}，次日记录数（出发日期>{today_date}）: {len(df_tomorrow)}")

        if len(df_today) == 0 and len(df_tomorrow) == 0:
            st.error("❌ 没有找到任何有效数据，请检查文件格式。")
            st.stop()

        # 显示预览
        with st.expander("📋 当日计划（将匹配并填入实际数据）"):
            if len(df_today) > 0:
                st.dataframe(df_today[["飞机注册号", "出发城市", "到达城市", "实际出发", "实际到达", "实际飞行时间"]])
            else:
                st.write("无当日计划")

        with st.expander("📋 次日计划（将新增备案）"):
            if len(df_tomorrow) > 0:
                st.dataframe(df_tomorrow[["飞机注册号", "出发日期", "到达日期", "用途", "出发城市", "到达城市", "预计飞行时间"]])
            else:
                st.write("无次日计划")

        with st.expander("✏️ 编辑当日数据处理脚本（可选）"):
            step1_template = st.text_area("当日脚本", value=DEFAULT_STEP1_TEMPLATE, height=400, key="step1")
        # 次日脚本需要您自行粘贴完整内容，这里提供一个占位提示
        step2_template = st.text_area("次日计划填报脚本（请粘贴完整内容）", value=STEP2_SCRIPT_TEMPLATE, height=400, key="step2")

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
