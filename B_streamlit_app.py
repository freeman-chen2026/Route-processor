#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streamlit应用：上传Excel飞行计划，生成Selenium自动化脚本
该脚本可自动在目标网页（如航班计划系统）中填写多架飞机的飞行计划。
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="飞行计划自动化脚本生成器",
    page_icon="✈️",
    layout="wide"
)

# 标题与说明
st.title("✈️ 飞行计划自动化脚本生成器")
st.markdown("""
### 功能说明
1. 上传包含飞行计划的Excel文件。
2. 系统解析数据，并按飞机注册号分组。
3. 生成一个Python自动化脚本（使用Selenium），该脚本可以：
   - 自动打开目标网页
   - 根据Excel内容逐架飞机、逐条计划填写表单
   - 支持同一架飞机的多条计划（自动增行）
   - 每完成一架飞机后等待用户确认，再继续下一架
4. 下载生成的脚本，在本地运行（需安装Python和Selenium）。
""")

# 侧边栏：配置目标网页URL
st.sidebar.header("⚙️ 配置目标网页")
target_url = st.sidebar.text_input(
    "请输入目标网页的完整URL",
    value="https://example.com/flight-plan",
    help="脚本将自动打开此URL并进行填写操作"
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**使用前准备**\n\n"
    "1. 安装Python环境\n"
    "2. 安装依赖：`pip install selenium pandas openpyxl`\n"
    "3. 下载并配置浏览器驱动（Chrome需chromedriver，或使用webdriver-manager）\n"
    "4. 运行生成的脚本：`python flight_auto.py`"
)

# 主区域：文件上传
uploaded_file = st.file_uploader(
    "📂 上传Excel文件（.xlsx 或 .xls）",
    type=["xlsx", "xls"],
    help="Excel必须包含以下列：飞机注册号, 出发地, 到达地, 用途, 计划出发, 预计到达。\n"
         "或者包含：出发日期, 计划出发时间, 预计到达日期, 预计到达时间。"
)

# 定义期望的列名映射（支持多种命名方式）
COLUMN_MAPPING = {
    "aircraft_reg": ["飞机注册号", "注册号", "机号", "Aircraft Reg", "Registration"],
    "departure": ["出发地", "起飞机场", "Dep", "Departure"],
    "arrival": ["到达地", "目的机场", "Arr", "Arrival"],
    "purpose": ["用途", "任务类型", "Purpose", "Flight Type"],
    "planned_dep": ["计划出发", "计划起飞时间", "Planned Departure", "Off-block Time"],
    "planned_arr": ["预计到达", "计划到达时间", "Planned Arrival", "On-block Time"],
    # 备选拆分列
    "dep_date": ["出发日期", "日期", "Flight Date"],
    "dep_time": ["计划出发时间", "起飞时间", "Departure Time"],
    "arr_date": ["到达日期", "预计到达日期", "Arrival Date"],
    "arr_time": ["预计到达时间", "到达时间", "Arrival Time"],
}

def detect_columns(df):
    """检测Excel中的列名，返回标准化的列名映射字典"""
    cols = df.columns.str.lower().str.strip()
    detected = {}
    
    # 尝试检测合并的日期时间列
    for std_name, possible_names in COLUMN_MAPPING.items():
        for name in possible_names:
            matches = [c for c in cols if name.lower() in c]
            if matches:
                detected[std_name] = matches[0]
                break
    
    # 如果缺少计划出发/到达，尝试从拆分列组合
    if "planned_dep" not in detected and "dep_date" in detected and "dep_time" in detected:
        detected["planned_dep"] = "combined_dep"
    if "planned_arr" not in detected and "arr_date" in detected and "arr_time" in detected:
        detected["planned_arr"] = "combined_arr"
    
    return detected

def parse_excel(df, detected_cols):
    """解析并标准化Excel数据，返回每行计划的字典列表"""
    records = []
    # 获取实际列名
    reg_col = detected_cols.get("aircraft_reg")
    dep_col = detected_cols.get("departure")
    arr_col = detected_cols.get("arrival")
    purpose_col = detected_cols.get("purpose")
    planned_dep_col = detected_cols.get("planned_dep")
    planned_arr_col = detected_cols.get("planned_arr")
    
    # 检查必要列
    required = [reg_col, dep_col, arr_col, purpose_col]
    if not all(required):
        missing = [col for col in required if col is None]
        st.error(f"Excel缺少必要列：{missing}。请确保包含飞机注册号、出发地、到达地、用途列。")
        return None
    
    for idx, row in df.iterrows():
        # 飞机注册号
        reg = str(row[reg_col]).strip()
        if pd.isna(reg) or reg == "nan":
            continue
        
        # 出发地、到达地
        dep = str(row[dep_col]).strip()
        arr = str(row[arr_col]).strip()
        if pd.isna(dep) or pd.isna(arr):
            continue
        
        # 用途：判断是否调机或维修
        purpose_raw = str(row[purpose_col]).lower() if not pd.isna(row[purpose_col]) else ""
        if "调机" in purpose_raw or "维修" in purpose_raw or "ferry" in purpose_raw:
            purpose = "Ferry"
        else:
            purpose = "Business"
        
        # 计划出发时间处理
        planned_dep_str = ""
        if planned_dep_col == "combined_dep":
            # 从拆分列组合
            dep_date = row[detected_cols.get("dep_date")]
            dep_time = row[detected_cols.get("dep_time")]
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
        
        # 预计到达时间处理
        planned_arr_str = ""
        if planned_arr_col == "combined_arr":
            arr_date = row[detected_cols.get("arr_date")]
            arr_time = row[detected_cols.get("arr_time")]
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
        
        # 额外提取出发日期（用于单独日期字段）
        dep_date_only = ""
        if planned_dep_str:
            dep_date_only = planned_dep_str.split()[0]
        
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

def generate_automation_script(records_by_aircraft, target_url):
    """生成Selenium自动化脚本（内嵌数据）"""
    script_lines = []
    script_lines.append("#!/usr/bin/env python3")
    script_lines.append("# -*- coding: utf-8 -*-")
    script_lines.append("\"\"\"")
    script_lines.append("自动飞行计划填写脚本")
    script_lines.append(f"目标网页: {target_url}")
    script_lines.append("生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    script_lines.append("\"\"\"")
    script_lines.append("")
    script_lines.append("import time")
    script_lines.append("from selenium import webdriver")
    script_lines.append("from selenium.webdriver.common.by import By")
    script_lines.append("from selenium.webdriver.support.ui import WebDriverWait")
    script_lines.append("from selenium.webdriver.support import expected_conditions as EC")
    script_lines.append("from selenium.webdriver.common.keys import Keys")
    script_lines.append("from selenium.common.exceptions import TimeoutException, NoSuchElementException")
    script_lines.append("")
    script_lines.append("# ==================== 配置区域 ====================")
    script_lines.append(f"TARGET_URL = \"{target_url}\"")
    script_lines.append("WAIT_TIME = 10  # 显式等待超时时间")
    script_lines.append("")
    script_lines.append("# 以下为从Excel解析出的飞行计划数据（按飞机分组）")
    script_lines.append("FLIGHT_DATA = " + repr(records_by_aircraft))
    script_lines.append("")
    script_lines.append("# ==================== 辅助函数 ====================")
    script_lines.append("")
    script_lines.append("def wait_and_find_element(driver, by, selector, timeout=WAIT_TIME):")
    script_lines.append("    \"\"\"等待元素可见并返回\"\"\"")
    script_lines.append("    return WebDriverWait(driver, timeout).until(")
    script_lines.append("        EC.visibility_of_element_located((by, selector))")
    script_lines.append("    )")
    script_lines.append("")
    script_lines.append("def click_element(driver, element):")
    script_lines.append("    \"\"\"安全点击元素\"\"\"")
    script_lines.append("    driver.execute_script(\"arguments[0].scrollIntoView(true);\", element)")
    script_lines.append("    time.sleep(0.5)")
    script_lines.append("    element.click()")
    script_lines.append("")
    script_lines.append("def input_text(element, text):")
    script_lines.append("    \"\"\"清空并输入文本\"\"\"")
    script_lines.append("    element.clear()")
    script_lines.append("    element.send_keys(text)")
    script_lines.append("")
    script_lines.append("def fill_cell_by_column_index(row_element, col_index, value):")
    script_lines.append("    \"\"\"")
    script_lines.append("    在表格行的指定列中填入值（适配可编辑div单元格）")
    script_lines.append("    参数: row_element - 行的WebElement, col_index - 列索引(从1开始), value - 要填入的文本")
    script_lines.append("    \"\"\"")
    script_lines.append("    try:")
    script_lines.append("        # 定位该行下第col_index列的单元格")
    script_lines.append("        cell = row_element.find_element(By.XPATH, f\"./td[{col_index}]//div[contains(@class, 'single-line-and-ellipsis') or @class]\"))")
    script_lines.append("        # 点击单元格激活编辑")
    script_lines.append("        click_element(driver, cell)")
    script_lines.append("        time.sleep(0.3)")
    script_lines.append("        # 查找可编辑区域（可能是div或input）")
    script_lines.append("        try:")
    script_lines.append("            editable = cell.find_element(By.XPATH, \".//div[@contenteditable='true'] | .//input | .//textarea\")")
    script_lines.append("        except:")
    script_lines.append("            editable = cell")
    script_lines.append("        # 清空并输入新值")
    script_lines.append("        editable.clear()")
    script_lines.append("        editable.send_keys(value)")
    script_lines.append("        time.sleep(0.2)")
    script_lines.append("        # 按回车确认（模拟失去焦点）")
    script_lines.append("        editable.send_keys(Keys.ENTER)")
    script_lines.append("    except Exception as e:")
    script_lines.append("        print(f\"❌ 填写第{col_index}列失败: {e}\")")
    script_lines.append("")
    script_lines.append("def add_new_row(driver, add_button):")
    script_lines.append("    \"\"\"点击增行按钮并返回新添加的行元素\"\"\"")
    script_lines.append("    # 记录当前行数")
    script_lines.append("    table = driver.find_element(By.XPATH, \"//table/tbody\")")
    script_lines.append("    rows_before = len(table.find_elements(By.XPATH, \"./tr\"))")
    script_lines.append("    click_element(driver, add_button)")
    script_lines.append("    time.sleep(1)")
    script_lines.append("    # 等待行数增加")
    script_lines.append("    WebDriverWait(driver, WAIT_TIME).until(")
    script_lines.append("        lambda d: len(table.find_elements(By.XPATH, \"./tr\")) > rows_before")
    script_lines.append("    )")
    script_lines.append("    rows = table.find_elements(By.XPATH, \"./tr\")")
    script_lines.append("    return rows[-1]  # 返回最后一行")
    script_lines.append("")
    script_lines.append("def fill_flight_plan_row(row_element, plan):")
    script_lines.append("    \"\"\"填充一行飞行计划的所有字段\"\"\"")
    script_lines.append("    # 列索引根据目标网页结构定义（3:出发地-到达地组合, 4:注册号, 5:用途, 6:注册号再次, 7:出发地, 8:到达地, 10:出发日期, 11:计划出发, 12:预计到达）")
    script_lines.append("    fill_cell_by_column_index(row_element, 3, plan['dep_arr_combo'])")
    script_lines.append("    fill_cell_by_column_index(row_element, 4, plan['reg'])")
    script_lines.append("    fill_cell_by_column_index(row_element, 5, plan['purpose'])")
    script_lines.append("    fill_cell_by_column_index(row_element, 6, plan['reg'])")
    script_lines.append("    fill_cell_by_column_index(row_element, 7, plan['departure'])")
    script_lines.append("    fill_cell_by_column_index(row_element, 8, plan['arrival'])")
    script_lines.append("    if plan['departure_date']:")
    script_lines.append("        fill_cell_by_column_index(row_element, 10, plan['departure_date'])")
    script_lines.append("    if plan['planned_departure']:")
    script_lines.append("        fill_cell_by_column_index(row_element, 11, plan['planned_departure'])")
    script_lines.append("    if plan['planned_arrival']:")
    script_lines.append("        fill_cell_by_column_index(row_element, 12, plan['planned_arrival'])")
    script_lines.append("    print(f\"    ✅ 计划 {plan['dep_arr_combo']} 填写完成\")")
    script_lines.append("")
    script_lines.append("# ==================== 主流程 ====================")
    script_lines.append("def main():")
    script_lines.append("    # 初始化浏览器")
    script_lines.append("    print(\"🚀 启动浏览器...\")")
    script_lines.append("    options = webdriver.ChromeOptions()")
    script_lines.append("    options.add_argument(\"--start-maximized\")")
    script_lines.append("    driver = webdriver.Chrome(options=options)  # 如使用其他浏览器请修改")
    script_lines.append("    try:")
    script_lines.append("        driver.get(TARGET_URL)")
    script_lines.append("        print(f\"✅ 已打开目标网页: {TARGET_URL}\")")
    script_lines.append("        time.sleep(3)  # 等待页面初始加载")
    script_lines.append("")
    script_lines.append("        # 定位顶部飞机注册号输入框（根据提供的XPath特征）")
    script_lines.append("        # 尝试多种定位方式")
    script_lines.append("        try:")
    script_lines.append("            reg_input = wait_and_find_element(driver, By.XPATH, \"//input[@class='nc-input refer-input'] | //input[@placeholder=''] | //div[contains(@class,'refer-input')]/input\"))")
    script_lines.append("        except:")
    script_lines.append("            # 如果找不到，使用备用绝对路径（用户提供）")
    script_lines.append("            reg_input = driver.find_element(By.XPATH, \"/html/body/div[1]/div/div[1]/div[1]/div[2]/div/div/span/div[1]/div/div/div/div/span[8]/div[2]/div[2]/div/div/div[2]/div/ul/li[2]/div/input\")")
    script_lines.append("")
    script_lines.append("        # 定位增行按钮")
    script_lines.append("        try:")
    script_lines.append("            add_btn = wait_and_find_element(driver, By.XPATH, \"//button[contains(text(),'增行')] | //button[@fieldid='FlightPlanUTC_AddLine_btn']\"))")
    script_lines.append("        except:")
    script_lines.append("            add_btn = driver.find_element(By.XPATH, \"/html/body/div[1]/div/div[1]/div[2]/div/div/div[2]/div/div/div/div/div/div/main/div/div/section/div[2]/header/div[3]/div/div/span/div/button[1]\")")
    script_lines.append("")
    script_lines.append("        # 遍历每架飞机")
    script_lines.append("        for idx, (reg, plans) in enumerate(FLIGHT_DATA.items(), 1):")
    script_lines.append("            print(f\"\\n✈️ 正在处理第{idx}架飞机: {reg} (共{len(plans)}条计划)\")")
    script_lines.append("            # 输入顶部飞机注册号")
    script_lines.append("            input_text(reg_input, reg)")
    script_lines.append("            print(f\"   📝 已输入顶部注册号: {reg}\")")
    script_lines.append("            time.sleep(1)")
    script_lines.append("")
    script_lines.append("            # 处理该飞机的第一条计划（需要先点击增行）")
    script_lines.append("            print(\"   ➕ 点击增行，添加第一条计划...\")")
    script_lines.append("            first_row = add_new_row(driver, add_btn)")
    script_lines.append("            fill_flight_plan_row(first_row, plans[0])")
    script_lines.append("")
    script_lines.append("            # 处理剩余的后续计划（如果有）")
    script_lines.append("            for plan in plans[1:]:")
    script_lines.append("                print(\"   ➕ 再次点击增行，添加下一条计划...\")")
    script_lines.append("                new_row = add_new_row(driver, add_btn)")
    script_lines.append("                fill_flight_plan_row(new_row, plan)")
    script_lines.append("")
    script_lines.append("            print(f\"✅ 飞机 {reg} 的所有计划填写完毕！\")")
    script_lines.append("            # 等待用户检查确认")
    script_lines.append("            input(\"\\n⏸️ 请人工检查当前飞机的填写是否正确。按 Enter 键继续处理下一架飞机...\")")
    script_lines.append("")
    script_lines.append("        print(\"\\n🎉 所有飞机的飞行计划已填写完成！脚本结束。\")")
    script_lines.append("        input(\"按 Enter 键关闭浏览器...\")")
    script_lines.append("    except Exception as e:")
    script_lines.append("        print(f\"❌ 发生错误: {e}\")")
    script_lines.append("        import traceback")
    script_lines.append("        traceback.print_exc()")
    script_lines.append("        input(\"按 Enter 键退出...\")")
    script_lines.append("    finally:")
    script_lines.append("        driver.quit()")
    script_lines.append("")
    script_lines.append("if __name__ == \"__main__\":")
    script_lines.append("    main()")
    
    return "\n".join(script_lines)

# 当文件上传后处理
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 文件上传成功！共 {df.shape[0]} 行，{df.shape[1]} 列")
        
        # 显示数据预览
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())
        
        # 检测列映射
        detected = detect_columns(df)
        st.subheader("🔍 列名识别结果")
        col_markdown = ""
        for std, actual in detected.items():
            col_markdown += f"- **{std}** → `{actual}`\n"
        st.markdown(col_markdown)
        
        # 解析数据
        with st.spinner("解析Excel数据..."):
            records = parse_excel(df, detected)
        
        if records is None:
            st.stop()
        
        if len(records) == 0:
            st.warning("未找到有效的飞行计划数据，请检查Excel内容。")
            st.stop()
        
        # 按飞机注册号分组
        records_by_aircraft = {}
        for rec in records:
            reg = rec["reg"]
            if reg not in records_by_aircraft:
                records_by_aircraft[reg] = []
            records_by_aircraft[reg].append(rec)
        
        st.subheader("✈️ 解析结果（按飞机分组）")
        for reg, plans in records_by_aircraft.items():
            st.markdown(f"**{reg}**：{len(plans)} 条计划")
            for p in plans:
                st.caption(f"  {p['dep_arr_combo']} | {p['planned_departure']} → {p['planned_arrival']} | {p['purpose']}")
        
        # 生成脚本按钮
        if st.button("🚀 生成自动化脚本", type="primary"):
            if not target_url or target_url == "https://example.com/flight-plan":
                st.warning("请在侧边栏填写正确的目标网页URL！")
                st.stop()
            
            script_content = generate_automation_script(records_by_aircraft, target_url)
            
            # 提供下载
            st.download_button(
                label="📥 下载脚本 (flight_auto.py)",
                data=script_content,
                file_name="flight_auto.py",
                mime="text/x-python",
                help="点击下载生成的Python自动化脚本"
            )
            
            st.info("""
            **使用生成的脚本**：
            1. 将下载的 `flight_auto.py` 保存到本地。
            2. 确保已安装依赖：`pip install selenium pandas`
            3. 如需自动管理驱动，可安装 `webdriver-manager` 并修改脚本。
            4. 在命令行运行：`python flight_auto.py`
            5. 脚本将打开浏览器，自动执行填写，每架飞机完成后会暂停等待您的检查。
            """)
            
    except Exception as e:
        st.error(f"处理Excel时出错: {e}")
        st.exception(e)
else:
    st.info("👈 请从左侧上传Excel文件开始")

# 页脚
st.markdown("---")
st.caption("本工具生成Selenium脚本，请在受信任的环境中运行。如遇元素定位问题，请根据实际网页结构调整XPath。")
