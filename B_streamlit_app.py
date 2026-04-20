# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 页面配置
st.set_page_config(
    page_title="飞行计划自动化脚本生成器",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 飞行计划自动化脚本生成器")
st.markdown("""
### 功能说明
1. 上传包含飞行计划的Excel文件（.xlsx或.xls）。
2. 系统自动识别列名（支持中英文），并按飞机注册号分组。
3. 生成一个完整的Python自动化脚本（使用Selenium），该脚本能够：
   - 自动打开您指定的目标网页
   - 根据Excel内容逐架飞机、逐条计划填写表单
   - 支持同一架飞机的多条计划（自动点击“增行”）
   - 每完成一架飞机后暂停，等待人工检查，按Enter继续下一架
4. 下载生成的脚本，在本地运行（需安装Python和Selenium）。
""")

# 侧边栏配置
st.sidebar.header("⚙️ 配置目标网页")
target_url = st.sidebar.text_input(
    "请输入目标网页的完整URL",
    value="https://example.com/flight-plan",
    help="脚本将自动打开此URL并进行填写操作"
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**本地运行脚本前的准备**\n\n"
    "1. 安装Python（≥3.7）\n"
    "2. 安装依赖：`pip install selenium pandas openpyxl`\n"
    "3. 下载Chrome浏览器对应的chromedriver（或使用webdriver-manager自动管理）\n"
    "4. 运行脚本：`python flight_auto.py`"
)

# 列名映射（支持中英文）
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
    """检测Excel中的列名，返回标准化的列名映射字典"""
    cols = df.columns.str.lower().str.strip()
    detected = {}
    for std_name, possible_names in COLUMN_MAPPING.items():
        for name in possible_names:
            matches = [c for c in cols if name.lower() in c]
            if matches:
                detected[std_name] = matches[0]
                break
    # 如果缺少合并的日期时间列，尝试从拆分列组合
    if "planned_dep" not in detected and "dep_date" in detected and "dep_time" in detected:
        detected["planned_dep"] = "combined_dep"
    if "planned_arr" not in detected and "arr_date" in detected and "arr_time" in detected:
        detected["planned_arr"] = "combined_arr"
    return detected

def parse_excel(df, detected):
    """解析Excel，返回每条计划的字典列表"""
    records = []
    reg_col = detected.get("aircraft_reg")
    dep_col = detected.get("departure")
    arr_col = detected.get("arrival")
    purpose_col = detected.get("purpose")
    planned_dep_col = detected.get("planned_dep")
    planned_arr_col = detected.get("planned_arr")

    if not all([reg_col, dep_col, arr_col, purpose_col]):
        missing = [c for c in [reg_col, dep_col, arr_col, purpose_col] if c is None]
        st.error(f"Excel缺少必要列：{missing}。请确保包含飞机注册号、出发地、到达地、用途列。")
        return None

    for _, row in df.iterrows():
        reg = str(row[reg_col]).strip()
        if pd.isna(reg) or reg == "nan" or reg == "":
            continue

        dep = str(row[dep_col]).strip()
        arr = str(row[arr_col]).strip()
        if pd.isna(dep) or pd.isna(arr) or dep == "" or arr == "":
            continue

        # 用途转换
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

        # 预计到达时间
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

        # 提取出发日期（YYYY-MM-DD）
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

def generate_script(records_by_aircraft, target_url):
    """生成Selenium自动化脚本（字符串）"""
    script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动飞行计划填写脚本
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
目标网页: {target_url}
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ==================== 配置 ====================
TARGET_URL = "{target_url}"
WAIT_TIME = 10

# 从Excel解析的飞行计划数据（按飞机分组）
FLIGHT_DATA = {repr(records_by_aircraft)}

# ==================== 辅助函数 ====================
def wait_and_find_element(driver, by, selector, timeout=WAIT_TIME):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, selector))
    )

def click_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.5)
    element.click()

def input_text(element, text):
    element.clear()
    element.send_keys(text)

def fill_cell_by_column_index(row_element, col_index, value):
    """
    在表格行的指定列中填入值（适配可编辑div单元格）
    row_element: 行的WebElement
    col_index: 列索引（从1开始）
    value: 要填入的文本
    """
    try:
        # 定位单元格
        cell = row_element.find_element(By.XPATH, f"./td[{col_index}]//div[contains(@class, 'single-line-and-ellipsis')]")
        click_element(driver, cell)
        time.sleep(0.3)
        # 查找可编辑区域
        try:
            editable = cell.find_element(By.XPATH, ".//div[@contenteditable='true'] | .//input | .//textarea")
        except:
            editable = cell
        editable.clear()
        editable.send_keys(value)
        time.sleep(0.2)
        editable.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"❌ 填写第{col_index}列失败: {{e}}")

def add_new_row(driver, add_button):
    """点击增行按钮并返回新添加的行元素"""
    table = driver.find_element(By.XPATH, "//table/tbody")
    rows_before = len(table.find_elements(By.XPATH, "./tr"))
    click_element(driver, add_button)
    time.sleep(1)
    WebDriverWait(driver, WAIT_TIME).until(
        lambda d: len(table.find_elements(By.XPATH, "./tr")) > rows_before
    )
    rows = table.find_elements(By.XPATH, "./tr")
    return rows[-1]

def fill_flight_plan_row(row_element, plan):
    """填充一行飞行计划的所有字段（列索引基于用户提供的XPath）"""
    fill_cell_by_column_index(row_element, 3, plan['dep_arr_combo'])
    fill_cell_by_column_index(row_element, 4, plan['reg'])
    fill_cell_by_column_index(row_element, 5, plan['purpose'])
    fill_cell_by_column_index(row_element, 6, plan['reg'])
    fill_cell_by_column_index(row_element, 7, plan['departure'])
    fill_cell_by_column_index(row_element, 8, plan['arrival'])
    if plan['departure_date']:
        fill_cell_by_column_index(row_element, 10, plan['departure_date'])
    if plan['planned_departure']:
        fill_cell_by_column_index(row_element, 11, plan['planned_departure'])
    if plan['planned_arrival']:
        fill_cell_by_column_index(row_element, 12, plan['planned_arrival'])
    print(f"    ✅ 计划 {{plan['dep_arr_combo']}} 填写完成")

# ==================== 主流程 ====================
def main():
    print("🚀 启动浏览器...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(TARGET_URL)
        print(f"✅ 已打开目标网页: {{TARGET_URL}}")
        time.sleep(3)

        # 定位顶部飞机注册号输入框（使用用户提供的XPath和备用定位）
        try:
            reg_input = wait_and_find_element(driver, By.XPATH, "//input[@class='nc-input refer-input'] | //input[@placeholder='']")
        except:
            reg_input = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div[1]/div[2]/div/div/span/div[1]/div/div/div/div/span[8]/div[2]/div[2]/div/div/div[2]/div/ul/li[2]/div/input")

        # 定位增行按钮
        try:
            add_btn = wait_and_find_element(driver, By.XPATH, "//button[contains(text(),'增行')] | //button[@fieldid='FlightPlanUTC_AddLine_btn']")
        except:
            add_btn = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/div/div/div[2]/div/div/div/div/div/div/main/div/div/section/div[2]/header/div[3]/div/div/span/div/button[1]")

        # 逐架飞机处理
        for idx, (reg, plans) in enumerate(FLIGHT_DATA.items(), 1):
            print(f"\\n✈️ 正在处理第{{idx}}架飞机: {{reg}} (共{{len(plans)}}条计划)")
            input_text(reg_input, reg)
            print(f"   📝 已输入顶部注册号: {{reg}}")
            time.sleep(1)

            # 第一条计划
            print("   ➕ 点击增行，添加第一条计划...")
            first_row = add_new_row(driver, add_btn)
            fill_flight_plan_row(first_row, plans[0])

            # 后续计划
            for plan in plans[1:]:
                print("   ➕ 再次点击增行，添加下一条计划...")
                new_row = add_new_row(driver, add_btn)
                fill_flight_plan_row(new_row, plan)

            print(f"✅ 飞机 {{reg}} 的所有计划填写完毕！")
            input("\\n⏸️ 请人工检查当前飞机的填写是否正确。按 Enter 键继续处理下一架飞机...")

        print("\\n🎉 所有飞机的飞行计划已填写完成！脚本结束。")
        input("按 Enter 键关闭浏览器...")
    except Exception as e:
        print(f"❌ 发生错误: {{e}}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
'''
    return script

# 主界面：文件上传
uploaded_file = st.file_uploader("📂 上传Excel文件（.xlsx 或 .xls）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 文件上传成功！共 {df.shape[0]} 行，{df.shape[1]} 列")
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())

        # 列识别
        detected = detect_columns(df)
        st.subheader("🔍 列名识别结果")
        st.json(detected)

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
            records_by_aircraft.setdefault(reg, []).append(rec)

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

            script_content = generate_script(records_by_aircraft, target_url)
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
            3. （可选）使用 `webdriver-manager` 自动管理驱动。
            4. 在命令行运行：`python flight_auto.py`
            5. 脚本将打开浏览器，自动执行填写，每架飞机完成后会暂停等待您的检查。
            """)
    except Exception as e:
        st.error(f"处理Excel时出错: {e}")
        st.exception(e)
else:
    st.info("👈 请上传Excel文件开始")

st.markdown("---")
st.caption("本工具生成Selenium脚本，请在受信任的环境中运行。如遇元素定位问题，请根据实际网页结构调整脚本中的XPath。")
