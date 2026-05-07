import streamlit as st
import pandas as pd
import time
from typing import List, Dict, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import datetime
import re
import os
import json

# ---------- 页面配置 ----------
st.set_page_config(page_title="飞行计划备案自动化工具", layout="wide")
st.title("✈️ 飞行计划备案自动化助手")

# ---------- 辅助函数 ----------
def date_format_for_compare(excel_date):
    """将Excel中的日期 '2026-04-04' 转换为 '20260404' 用于网页匹配"""
    if isinstance(excel_date, str):
        return excel_date.replace('-', '')
    elif isinstance(excel_date, (datetime.date, pd.Timestamp)):
        return excel_date.strftime('%Y%m%d')
    else:
        return str(excel_date).replace('-', '')

def get_aircraft_type(reg: str) -> str:
    """根据飞机注册号返回机型（用于弹框中的机型字段）"""
    mapping = {
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60",
        "B658L": "GLF6",
        "B8105": "GLEX",
        "B8160": "GLF5"
    }
    return mapping.get(reg, "GLF4")   # 默认GLF4

def get_task_type(purpose: str) -> str:
    """根据用途列决定任务性质"""
    if purpose in ["调机", "维修"]:
        return "调机飞行"
    else:
        return "公务飞行"

# ---------- Selenium 管理器 ----------
class FlightPlanAutomation:
    def __init__(self, headless=False, debugger_address=None):
        self.driver = None
        self.headless = headless
        self.debugger_address = debugger_address

    def connect(self):
        """启动或连接浏览器"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        if self.debugger_address:
            # 连接已存在的Chrome调试端口 (远程调试模式，保留登录态)
            chrome_options.add_experimental_option("debuggerAddress", self.debugger_address)
            self.driver = webdriver.Chrome(options=chrome_options)
            st.info(f"已连接到远程调试浏览器 (地址: {self.debugger_address})")
        else:
            # 普通模式，自动管理驱动
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            st.info("已启动新的Chrome浏览器窗口，请手动完成登录后点击「继续」按钮")
            # 等待用户手动登录
            if st.button("✅ 我已登录完成，继续执行"):
                st.session_state.continue_flag = True
            # 通过会话状态阻塞
            while not st.session_state.get("continue_flag", False):
                time.sleep(0.5)
            st.session_state.continue_flag = False

    def get_existing_plans(self, url: str, row_xpath: str, cells_map: Dict[str, int]) -> List[Tuple]:
        """
        抓取网页表格中的已有计划
        row_xpath: 定位每一行的XPath (例如 "//table/tbody/tr")
        cells_map: 列索引映射 {'exec_date': 10, 'reg': 8, 'dep': 11, 'arr': 14} (从1开始)
        返回 [(exec_date_yyyymmdd, reg, dep, arr), ...]
        """
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.presence_of_element_located((By.XPATH, row_xpath)))
        rows = self.driver.find_elements(By.XPATH, row_xpath)
        plans = []
        for row in rows:
            try:
                # 获取各单元格相对当前行的XPath
                exec_date_elem = row.find_element(By.XPATH, f"./td[{cells_map['exec_date']}]/div")
                reg_elem = row.find_element(By.XPATH, f"./td[{cells_map['reg']}]/div")
                dep_elem = row.find_element(By.XPATH, f"./td[{cells_map['dep']}]/div")
                arr_elem = row.find_element(By.XPATH, f"./td[{cells_map['arr']}]/div")
                exec_date = exec_date_elem.text.strip()
                reg = reg_elem.text.strip()
                dep = dep_elem.text.strip()
                arr = arr_elem.text.strip()
                if exec_date and reg and dep and arr:
                    plans.append((exec_date, reg, dep, arr))
            except Exception as e:
                # 跳过解析失败的行
                continue
        return plans

    def add_new_plan(self, plan: Dict, xpath_config: Dict) -> bool:
        """
        新增一条飞行计划
        plan: 包含以下字段
            - reg: 注册号
            - exec_date: 出发日期 (原始格式 '2026-04-04')
            - dep: 出发地
            - arr: 到达地
            - purpose: 用途
        xpath_config: 弹框中各类元素的Xpath映射
        """
        try:
            # 点击新增按钮
            add_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_config['add_button']))
            )
            add_btn.click()
            time.sleep(1)

            # 1. 机型
            ac_type = get_aircraft_type(plan['reg'])
            ac_type_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath_config['ac_type']))
            )
            ac_type_input.clear()
            ac_type_input.send_keys(ac_type)

            # 2. 执行日期
            date_input = self.driver.find_element(By.XPATH, xpath_config['exec_date_input'])
            # 尝试直接输入值（兼容多种日期控件）
            date_input.clear()
            date_input.send_keys(plan['exec_date'])
            # 可选：触发change事件
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", date_input)
            time.sleep(0.5)

            # 3. 异地运行 -> 是
            remote_op = self.driver.find_element(By.XPATH, xpath_config['remote_run'])
            remote_op.click()
            # 展开下拉框后选择"是"
            is_option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_config['remote_yes_option']))
            )
            is_option.click()

            # 4. 任务性质
            task_type = get_task_type(plan['purpose'])
            task_input = self.driver.find_element(By.XPATH, xpath_config['task_type'])
            task_input.click()
            # 如果是可编辑下拉框，直接输入文本
            task_input.send_keys(task_type)
            # 可选点击回车或下拉选项
            # 部分系统需要从下拉列表选择，这里简化处理：输入后按回车
            task_input.send_keys("\n")

            # 5. 两个注册号字段
            reg_field1 = self.driver.find_element(By.XPATH, xpath_config['reg_field1'])
            reg_field1.clear()
            reg_field1.send_keys(plan['reg'])

            reg_field2 = self.driver.find_element(By.XPATH, xpath_config['reg_field2'])
            reg_field2.clear()
            reg_field2.send_keys(plan['reg'])

            # 6. 起飞机场
            dep_input = self.driver.find_element(By.XPATH, xpath_config['departure'])
            dep_input.clear()
            dep_input.send_keys(plan['dep'])

            # 7. 落地机场
            arr_input = self.driver.find_element(By.XPATH, xpath_config['arrival'])
            arr_input.clear()
            arr_input.send_keys(plan['arr'])

            # 8. 保存
            save_btn = self.driver.find_element(By.XPATH, xpath_config['save_button'])
            save_btn.click()
            time.sleep(1)

            # 尝试关闭可能的成功提示
            try:
                close_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'关闭') or contains(text(),'确定')]")
                close_btn.click()
            except:
                pass
            return True
        except Exception as e:
            st.error(f"计划 {plan['reg']} {plan['exec_date']} 备案失败: {str(e)}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()

# ---------- Streamlit 界面 ----------
st.sidebar.header("🔧 配置面板")

# 浏览器连接设置
use_remote = st.sidebar.checkbox("使用已登录的远程浏览器 (推荐)", value=True, help="若勾选，请先手动用Chrome打开目标网站并登录，然后以远程调试模式启动Chrome")
remote_addr = st.sidebar.text_input("远程调试地址", value="localhost:9222", disabled=not use_remote)
headless_mode = st.sidebar.checkbox("无头模式 (不可见浏览器)", value=False)

# 目标网页URL
page_url = st.sidebar.text_input("目标网页URL（计划列表页）", value="http://your-inner-system.com/plan/list")

# 表格解析配置 (抓取现有计划)
st.sidebar.subheader("📋 现有计划表格配置")
row_xpath = st.sidebar.text_input("表格行XPath", value="//table/tbody/tr")
col_exec_date = st.sidebar.number_input("执行日列号(从1开始)", min_value=1, value=10)
col_reg = st.sidebar.number_input("注册号列号", min_value=1, value=8)
col_dep = st.sidebar.number_input("起飞机场列号", min_value=1, value=11)
col_arr = st.sidebar.number_input("落地机场列号", min_value=1, value=14)
cells_map = {'exec_date': col_exec_date, 'reg': col_reg, 'dep': col_dep, 'arr': col_arr}

# 新增弹窗配置
st.sidebar.subheader("➕ 新增弹窗元素定位（XPath）")
add_btn_xpath = st.sidebar.text_input("「新增」按钮XPath", value="//a[contains(@class,'add')]/span[2]")
ac_type_xpath = st.sidebar.text_input("机型输入框XPath", value="//div[@class='modal']//input[@placeholder='机型']")
exec_date_input_xpath = st.sidebar.text_input("执行日期输入框XPath", value="//div[@class='modal']//input[@placeholder='执行日期']")
remote_run_xpath = st.sidebar.text_input("异地运行下拉框XPath", value="//span[contains(text(),'异地运行')]/following::span[1]")
remote_yes_option_xpath = st.sidebar.text_input("异地运行「是」选项XPath", value="//li[text()='是']")
task_type_xpath = st.sidebar.text_input("任务性质输入框XPath", value="//div[@class='modal']//input[@placeholder='任务性质']")
reg_field1_xpath = st.sidebar.text_input("注册号字段1 XPath", value="//div[@class='modal']//ul[1]/li[8]/span")
reg_field2_xpath = st.sidebar.text_input("注册号字段2 XPath", value="//div[@class='modal']//ul[1]/li[10]/span/span/input")
departure_xpath = st.sidebar.text_input("起飞机场输入框XPath", value="//div[@class='modal']//input[@placeholder='起飞机场']")
arrival_xpath = st.sidebar.text_input("落地机场输入框XPath", value="//div[@class='modal']//input[@placeholder='落地机场']")
save_btn_xpath = st.sidebar.text_input("保存按钮XPath", value="//button[contains(text(),'保存')]")

xpath_config = {
    'add_button': add_btn_xpath,
    'ac_type': ac_type_xpath,
    'exec_date_input': exec_date_input_xpath,
    'remote_run': remote_run_xpath,
    'remote_yes_option': remote_yes_option_xpath,
    'task_type': task_type_xpath,
    'reg_field1': reg_field1_xpath,
    'reg_field2': reg_field2_xpath,
    'departure': departure_xpath,
    'arrival': arrival_xpath,
    'save_button': save_btn_xpath
}

# 上传Excel
uploaded_file = st.file_uploader("📂 上传飞行计划Excel文件", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📊 Excel解析结果")
    st.dataframe(df.head(20))
    required_cols = ['出发日期', '飞机注册号', '出发地', '到达地', '用途']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Excel缺少必需列: {missing}，请确保包含 {required_cols}")
        st.stop()
    # 提取计划
    excel_plans = []
    for _, row in df.iterrows():
        plan = {
            'exec_date': str(row['出发日期']).split()[0],   # 取日期部分
            'reg': row['飞机注册号'].strip(),
            'dep': row['出发地'].strip(),
            'arr': row['到达地'].strip(),
            'purpose': row['用途'].strip()
        }
        excel_plans.append(plan)
    st.success(f"读取到 {len(excel_plans)} 条飞行计划")

    # 执行自动化
    if st.button("🚀 开始匹配与自动备案"):
        # 初始化会话状态中的继续标志
        if 'continue_flag' not in st.session_state:
            st.session_state.continue_flag = False

        auto = FlightPlanAutomation(headless=headless_mode, debugger_address=remote_addr if use_remote else None)
        try:
            auto.connect()
            # 1. 抓取现有计划
            with st.spinner("正在抓取网页中的已有计划..."):
                existing = auto.get_existing_plans(page_url, row_xpath, cells_map)
            st.info(f"已抓取到 {len(existing)} 条已有备案计划")
            # 展示部分样例
            if existing:
                st.write("已有计划示例（前5条）：", existing[:5])

            # 2. 匹配筛选
            existing_set = set()
            for e in existing:
                # e = (exec_date_str, reg, dep, arr)
                existing_set.add((e[0], e[1], e[2], e[3]))
            unmatched = []
            for plan in excel_plans:
                comp_date = date_format_for_compare(plan['exec_date'])
                if (comp_date, plan['reg'], plan['dep'], plan['arr']) not in existing_set:
                    unmatched.append(plan)
            st.success(f"需要备案的计划数量: {len(unmatched)}")
            if not unmatched:
                st.balloons()
                st.info("所有计划均已备案，无需操作！")
                return

            # 3. 逐条备案
            progress_bar = st.progress(0)
            log_area = st.empty()
            success_count = 0
            for idx, plan in enumerate(unmatched):
                log_area.text(f"正在备案: {plan['reg']} - {plan['exec_date']} ({idx+1}/{len(unmatched)})")
                if auto.add_new_plan(plan, xpath_config):
                    success_count += 1
                # 每次新增后稍作停顿，避免过速
                time.sleep(1.5)
                progress_bar.progress((idx + 1) / len(unmatched))

            st.success(f"✅ 备案完成！成功 {success_count} 条，失败 {len(unmatched)-success_count} 条")
            if success_count == len(unmatched):
                st.balloons()
        except Exception as e:
            st.error(f"自动化过程发生错误: {str(e)}")
        finally:
            auto.close()
else:
    st.info("👈 请先在左侧配置好页面元素XPath，然后上传Excel文件")

st.markdown("---")
st.caption("💡 使用说明：\n"
           "1. 首次使用请务必根据实际网页，在侧边栏正确配置所有XPath定位器（尤其是弹框内的各个输入框）\n"
           "2. 推荐使用远程调试浏览器，避免处理登录和验证码：\n"
           "   - 在命令行启动Chrome: `chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\selenium_profile`\n"
           "   - 然后手动打开目标网站并登录，再回到本工具勾选「使用已登录的远程浏览器」并填写端口\n"
           "3. 若不使用远程调试，工具会弹出新浏览器窗口，你需要手动登录后点击「我已登录完成，继续执行」按钮")
