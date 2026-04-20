# app.py
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="飞行计划自动化脚本生成器（JS版）", page_icon="✈️", layout="wide")

st.title("✈️ 飞行计划自动化脚本生成器（浏览器控制台版）")
st.markdown("""
### 使用流程
1. 上传Excel文件（包含飞机注册号、出发地、到达地、用途、计划出发时间等）
2. 系统自动解析并按飞机分组
3. 下载或复制生成的**JavaScript脚本**
4. 打开目标网页（您要填写的那个系统），按 `F12` 打开开发者工具，切换到 **Console（控制台）** 标签
5. 粘贴脚本并回车执行
6. 脚本会自动填写，每架飞机完成后会弹出提示，等待您确认后继续下一架
""")

# 侧边栏配置
st.sidebar.header("⚙️ 配置目标网页（仅用于脚本提示）")
target_url_hint = st.sidebar.text_input("目标网页URL（可选）", placeholder="https://example.com/flight-plan")
st.sidebar.markdown("---")
st.sidebar.info(
    "**如何运行脚本？**\n\n"
    "1. 打开目标网页\n"
    "2. 按 `F12` 打开开发者工具\n"
    "3. 点击 `Console` 标签\n"
    "4. 粘贴生成的脚本，按回车执行\n"
    "5. 脚本会自动填写，并在每架飞机完成后弹出确认框"
)

# 列名映射
COLUMN_MAPPING = {
    "aircraft_reg": ["飞机注册号", "注册号", "机号", "Aircraft Reg", "Registration"],
    "departure": ["出发地", "起飞机场", "Dep", "Departure"],
    "arrival": ["到达地", "目的机场", "Arr", "Arrival"],
    "purpose": ["用途", "任务类型", "Purpose", "Flight Type"],
    "planned_dep": ["计划出发", "计划起飞时间", "Planned Departure", "Off-block Time"],
    "planned_arr": ["预计到达", "计划到达时间", "Planned Arrival", "On-block Time"],
    "dep_date": ["出发日期", "日期", "Flight Date"],
    "dep_time": ["计划出发时间", "起飞时间", "Departure Time"],
    "arr_date": ["到达日期", "预计到达日期", "Arrival Date"],
    "arr_time": ["预计到达时间", "到达时间", "Arrival Time"],
}

def detect_columns(df):
    cols = df.columns.str.lower().str.strip()
    detected = {}
    for std_name, possible_names in COLUMN_MAPPING.items():
        for name in possible_names:
            matches = [c for c in cols if name.lower() in c]
            if matches:
                detected[std_name] = matches[0]
                break
    if "planned_dep" not in detected and "dep_date" in detected and "dep_time" in detected:
        detected["planned_dep"] = "combined_dep"
    if "planned_arr" not in detected and "arr_date" in detected and "arr_time" in detected:
        detected["planned_arr"] = "combined_arr"
    return detected

def parse_excel(df, detected):
    records = []
    reg_col = detected.get("aircraft_reg")
    dep_col = detected.get("departure")
    arr_col = detected.get("arrival")
    purpose_col = detected.get("purpose")
    planned_dep_col = detected.get("planned_dep")
    planned_arr_col = detected.get("planned_arr")

    if not all([reg_col, dep_col, arr_col, purpose_col]):
        missing = [c for c in [reg_col, dep_col, arr_col, purpose_col] if c is None]
        st.error(f"Excel缺少必要列：{missing}")
        return None

    for _, row in df.iterrows():
        reg = str(row[reg_col]).strip()
        if pd.isna(reg) or reg == "nan" or reg == "":
            continue
        dep = str(row[dep_col]).strip()
        arr = str(row[arr_col]).strip()
        if pd.isna(dep) or pd.isna(arr) or dep == "" or arr == "":
            continue

        purpose_raw = str(row[purpose_col]).lower() if not pd.isna(row[purpose_col]) else ""
        if "调机" in purpose_raw or "维修" in purpose_raw or "ferry" in purpose_raw:
            purpose = "Ferry"
        else:
            purpose = "Business"

        # 计划出发时间
        planned_dep_str = ""
        if planned_dep_col == "combined_dep":
            dep_date = row[detected.get("dep_date")]
            dep_time = row[detected.get("dep_time")]
            if pd.notna(dep_date) and pd.notna(dep_time):
                try:
                    dt = pd.to_datetime(f"{dep_date} {dep_time}", errors='coerce')
                    if pd.notna(dt):
                        planned_dep_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        elif planned_dep_col:
            val = row[planned_dep_col]
            if pd.notna(val):
                try:
                    dt = pd.to_datetime(val)
                    planned_dep_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    planned_dep_str = str(val)

        planned_arr_str = ""
        if planned_arr_col == "combined_arr":
            arr_date = row[detected.get("arr_date")]
            arr_time = row[detected.get("arr_time")]
            if pd.notna(arr_date) and pd.notna(arr_time):
                try:
                    dt = pd.to_datetime(f"{arr_date} {arr_time}", errors='coerce')
                    if pd.notna(dt):
                        planned_arr_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        elif planned_arr_col:
            val = row[planned_arr_col]
            if pd.notna(val):
                try:
                    dt = pd.to_datetime(val)
                    planned_arr_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    planned_arr_str = str(val)

        dep_date_only = planned_dep_str.split()[0] if planned_dep_str else ""

        records.append({
            "reg": reg,
            "departure": dep,
            "arrival": arr,
            "dep_arr_combo": f"{dep}-{arr}",
            "purpose": purpose,
            "departure_date": dep_date_only,
            "planned_departure": planned_dep_str,
            "planned_arrival": planned_arr_str,
        })
    return records

def generate_js_script(records_by_aircraft):
    """生成可在浏览器控制台运行的JavaScript脚本"""
    # 将数据转为JSON字符串
    import json
    data_json = json.dumps(records_by_aircraft, ensure_ascii=False, indent=2)
    
    script = f"""
// ==================== 飞行计划自动填写脚本 ====================
// 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// 使用方法: 在目标网页按F12打开控制台，粘贴此脚本并回车

(function() {{
    // 从Excel解析的飞行计划数据（按飞机注册号分组）
    const FLIGHT_DATA = {data_json};

    // ========== 辅助函数 ==========
    function sleep(ms) {{
        return new Promise(resolve => setTimeout(resolve, ms));
    }}

    // 模拟输入文本（触发完整事件）
    function simulateInput(element, value) {{
        // 聚焦
        element.focus();
        // 清空原有内容
        element.value = '';
        // 触发input事件清空
        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
        // 输入新值
        element.value = value;
        // 触发input、change、blur事件
        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
        element.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        // 对于React等框架，可能还需要手动触发
        if (typeof element._valueTracker !== 'undefined') {{
            element._valueTracker.setValue(value);
        }}
    }}

    // 等待元素出现（基于XPath或CSS选择器）
    function waitForElement(xpath, timeout = 10000) {{
        return new Promise((resolve, reject) => {{
            const startTime = Date.now();
            const checkInterval = setInterval(() => {{
                const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (element) {{
                    clearInterval(checkInterval);
                    resolve(element);
                }} else if (Date.now() - startTime > timeout) {{
                    clearInterval(checkInterval);
                    reject(new Error(`等待元素超时: ${{xpath}}`));
                }}
            }}, 200);
        }});
    }}

    // 点击元素（滚动到可见区域）
    function clickElement(element) {{
        element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        return new Promise(resolve => setTimeout(() => {{
            element.click();
            resolve();
        }}, 300));
    }}

    // 填写单元格（基于行元素和列索引）
    async function fillCell(rowElement, colIndex, value) {{
        // 定位单元格内的可编辑div
        const cellDiv = rowElement.querySelector(`td:nth-child(${{colIndex}}) div[class*="single-line-and-ellipsis"]`);
        if (!cellDiv) {{
            console.warn(`未找到第${{colIndex}}列的单元格`);
            return;
        }}
        await clickElement(cellDiv);
        await sleep(200);
        // 查找可编辑区域（可能是contenteditable的div或input）
        let editable = cellDiv.querySelector('[contenteditable="true"], input, textarea');
        if (!editable) {{
            editable = cellDiv;
        }}
        if (editable.isContentEditable) {{
            // contenteditable元素
            editable.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, value);
            editable.dispatchEvent(new Event('input', {{ bubbles: true }}));
            editable.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        }} else {{
            simulateInput(editable, value);
        }}
        await sleep(150);
    }}

    // 点击增行按钮并返回新添加的行元素
    async function addNewRow() {{
        const addBtnXpath = "//button[contains(text(),'增行')] | //button[@fieldid='FlightPlanUTC_AddLine_btn']";
        let addBtn = document.evaluate(addBtnXpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!addBtn) {{
            // 备用绝对路径
            addBtn = document.evaluate("/html/body/div[1]/div/div[1]/div[2]/div/div/div[2]/div/div/div/div/div/div/main/div/div/section/div[2]/header/div[3]/div/div/span/div/button[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }}
        if (!addBtn) throw new Error("未找到增行按钮");
        
        const table = document.querySelector("table tbody");
        const rowsBefore = table ? table.querySelectorAll("tr").length : 0;
        await clickElement(addBtn);
        await sleep(1000);
        // 等待行数增加
        let retries = 0;
        while (retries < 20) {{
            const rowsNow = table ? table.querySelectorAll("tr").length : 0;
            if (rowsNow > rowsBefore) break;
            await sleep(300);
            retries++;
        }}
        const newRows = table.querySelectorAll("tr");
        return newRows[newRows.length - 1];
    }}

    // 填写一行计划
    async function fillPlanRow(rowElement, plan) {{
        await fillCell(rowElement, 3, plan.dep_arr_combo);
        await fillCell(rowElement, 4, plan.reg);
        await fillCell(rowElement, 5, plan.purpose);
        await fillCell(rowElement, 6, plan.reg);
        await fillCell(rowElement, 7, plan.departure);
        await fillCell(rowElement, 8, plan.arrival);
        if (plan.departure_date) {{
            await fillCell(rowElement, 10, plan.departure_date);
        }}
        if (plan.planned_departure) {{
            await fillCell(rowElement, 11, plan.planned_departure);
        }}
        if (plan.planned_arrival) {{
            await fillCell(rowElement, 12, plan.planned_arrival);
        }}
        console.log(`✅ 已填写计划: ${{plan.dep_arr_combo}}`);
    }}

    // ========== 主流程 ==========
    async function main() {{
        console.log("🚀 开始执行飞行计划自动填写脚本");
        
        // 定位顶部飞机注册号输入框
        let regInput = document.querySelector("input.nc-input.refer-input");
        if (!regInput) {{
            regInput = document.evaluate("/html/body/div[1]/div/div[1]/div[1]/div[2]/div/div/span/div[1]/div/div/div/div/span[8]/div[2]/div[2]/div/div/div[2]/div/ul/li[2]/div/input", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }}
        if (!regInput) {{
            alert("❌ 未找到顶部飞机注册号输入框，请检查页面是否已打开且元素正确");
            return;
        }}

        for (const [reg, plans] of Object.entries(FLIGHT_DATA)) {{
            console.log(`✈️ 正在处理飞机: ${{reg}} (共${{plans.length}}条计划)`);
            // 输入顶部注册号
            simulateInput(regInput, reg);
            await sleep(500);
            
            // 处理第一条计划
            console.log("   ➕ 添加第一条计划...");
            const firstRow = await addNewRow();
            await fillPlanRow(firstRow, plans[0]);
            
            // 处理后续计划
            for (let i = 1; i < plans.length; i++) {{
                console.log(`   ➕ 添加第${{i+1}}条计划...`);
                const newRow = await addNewRow();
                await fillPlanRow(newRow, plans[i]);
            }}
            
            console.log(`✅ 飞机 ${{reg}} 填写完成`);
            // 等待用户确认
            const userConfirmed = confirm(`飞机 ${{reg}} 的所有计划已填写完毕。\\n请检查是否正确，点击“确定”继续下一架，点击“取消”终止脚本。`);
            if (!userConfirmed) {{
                console.log("用户终止脚本");
                break;
            }}
        }}
        console.log("🎉 所有飞行计划处理完毕！");
        alert("脚本执行完成！");
    }}

    // 执行主函数并捕获错误
    main().catch(err => {{
        console.error("脚本执行出错:", err);
        alert("脚本出错: " + err.message);
    }});
}})();
"""
    return script

# 上传文件界面
uploaded_file = st.file_uploader("📂 上传Excel文件（.xlsx 或 .xls）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 上传成功！共 {df.shape[0]} 行，{df.shape[1]} 列")
        st.subheader("📊 数据预览")
        st.dataframe(df.head())

        detected = detect_columns(df)
        st.subheader("🔍 识别到的列")
        st.json(detected)

        with st.spinner("解析数据..."):
            records = parse_excel(df, detected)
        if records is None or len(records) == 0:
            st.error("未找到有效数据")
            st.stop()

        # 分组
        records_by_aircraft = {}
        for rec in records:
            records_by_aircraft.setdefault(rec["reg"], []).append(rec)

        st.subheader("✈️ 飞行计划分组预览")
        for reg, plans in records_by_aircraft.items():
            st.markdown(f"**{reg}**：{len(plans)} 条计划")
            for p in plans:
                st.caption(f"  {p['dep_arr_combo']} | {p['planned_departure']} → {p['planned_arrival']} | {p['purpose']}")

        # 生成JS脚本
        js_script = generate_js_script(records_by_aircraft)
        
        st.subheader("📜 生成的JavaScript脚本")
        st.code(js_script, language="javascript")
        
        st.download_button(
            label="📥 下载脚本 (flight_auto.js)",
            data=js_script,
            file_name="flight_auto.js",
            mime="text/javascript",
            help="下载后可用文本编辑器打开，复制全部内容"
        )
        
        st.success("✅ 脚本已生成！请复制上方代码，在目标网页按F12打开控制台，粘贴后回车运行。")
        st.info("💡 提示：如果脚本运行时元素定位失败，请检查目标网页是否完全加载，或根据实际页面结构调整脚本中的XPath。")
        
    except Exception as e:
        st.error(f"处理出错: {e}")
        st.exception(e)
else:
    st.info("👈 请上传Excel文件开始")

st.markdown("---")
st.caption("本工具生成JavaScript脚本，需在目标网页的浏览器控制台中运行。无需安装任何本地软件。")
