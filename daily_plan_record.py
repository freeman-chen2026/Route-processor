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
    """根据飞机注册号返回机型"""
    mapping = {
        "B652Q": "GLF4", "B652R": "GLF4", "B652S": "GLF4", "B8262": "GLF4",
        "B3926": "LJ60",
        "B658L": "GLF6",
        "B8105": "GLEX",
        "B8160": "GLF5"
    }
    return mapping.get(reg, "GLF4")

def get_task_type(purpose: str) -> str:
    """根据用途列决定任务性质"""
    return "调机飞行" if purpose in ["调机", "维修"] else "公务飞行"

# ---------- Selenium 自动化类 ----------
class FlightPlanAutomation:
    def __init__(self, driver):
        self.driver = driver

    def get_existing_plans(self, url: str, row_xpath: str, cells_map: Dict[str, int]) -> List[Tuple]:
        """抓取网页表格中的已有计划"""
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.presence_of_element_located((By.XPATH, row_xpath)))
        rows = self.driver.find_elements(By.XPATH, row_xpath)
        plans = []
        for row in rows:
            try:
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
            except Exception:
                continue
        return plans

    def add_new_plan(self, plan: Dict, xpath_config: Dict) -> bool:
        """新增一条飞行计划"""
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
            date_input.clear()
            date_input.send_keys(plan['exec_date'])
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", date_input)
            time.sleep(0.5)

            # 3. 异地运行 -> 是
            remote_op = self.driver.find_element(By.XPATH, xpath_config['remote_run'])
            remote_op.click()
            is_option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_config['remote_yes_option']))
            )
            is_option.click()

            # 4. 任务性质
            task_type = get_task_type(plan['purpose'])
            task_input = self.driver.find_element(By.XPATH, xpath_config['task_type'])
            task_input.click()
            task_input.send_keys(task_type)
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

            # 尝试关闭成功提示
            try:
                close_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'关闭') or contains(text(),'确定')]")
                close_btn.click()
            except Exception:
                pass
            return True
        except Exception as e:
            st.error(f"计划 {plan['reg']} {plan['exec_date']} 备案失败: {str(e)}")
            return False

# ---------- Streamlit 界面 ----------
st.sidebar.header("🔧 配置面板")

# 浏览器连接设置
use_remote = st.sidebar.checkbox("使用已登录的远程浏览器", value=True, help="需先手动启动Chrome远程调试模式并登录")
remote_addr = st.sidebar.text_input("远程调试地址", value="localhost:9222", disabled=not use_remote)
headless_mode = st.sidebar.checkbox("无头模式", value=False)

# 目标网页URL
page_url = st.sidebar.text_input("计划列表页URL", value="http://your-system.com/plan/list")

# 表格解析配置
st.sidebar.subheader("📋 已有计划表格XPath")
row_xpath = st.sidebar.text_input("表格行XPath", value="//table/tbody/tr")
col_exec_date = st.sidebar.number_input("执行日列号", min_value=1, value=10)
col_reg = st.sidebar.number_input("注册号列号", min_value=1, value=8)
col_dep = st.sidebar.number_input("起飞机场列号", min_value=1, value=11)
col_arr = st.sidebar.number_input("落地机场列号", min_value=1, value=14)
cells_map = {'exec_date': col_exec_date, 'reg': col_reg, 'dep': col_dep, 'arr': col_arr}

# 新增弹窗配置
st.sidebar.subheader("➕ 新增弹窗元素XPath")
add_btn_xpath = st.sidebar.text_input("「新增」按钮", value="//a[contains(@class,'add')]/span[2]")
ac_type_xpath = st.sidebar.text_input("机型输入框", value="//div[@class='modal']//input[@placeholder='机型']")
exec_date_input_xpath = st.sidebar.text_input("执行日期输入框", value="//div[@class='modal']//input[@placeholder='执行日期']")
remote_run_xpath = st.sidebar.text_input("异地运行下拉框", value="//span[contains(text(),'异地运行')]/following::span[1]")
remote_yes_option_xpath = st.sidebar.text_input("异地运行「是」选项", value="//li[text()='是']")
task_type_xpath = st.sidebar.text_input("任务性质输入框", value="//div[@class='modal']//input[@placeholder='任务性质']")
reg_field1_xpath = st.sidebar.text_input("注册号字段1", value="//div[@class='modal']//ul[1]/li[8]/span")
reg_field2_xpath = st.sidebar.text_input("注册号字段2", value="//div[@class='modal']//ul[1]/li[10]/span/span/input")
departure_xpath = st.sidebar.text_input("起飞机场输入框", value="//div[@class='modal']//input[@placeholder='起飞机场']")
arrival_xpath = st.sidebar.text_input("落地机场输入框", value="//div[@class='modal']//input[@placeholder='落地机场']")
save_btn_xpath = st.sidebar.text_input("保存按钮", value="//button[contains(text(),'保存')]")

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

# 全局session_state初始化
if 'browser_ready' not in st.session_state:
    st.session_state.browser_ready = False
if 'driver' not in st.session_state:
    st.session_state.driver = None

# 连接浏览器按钮（独立于主流程）
if not st.session_state.browser_ready:
    if st.button("🌐 1. 连接浏览器"):
        chrome_options = Options()
        if headless_mode:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        if use_remote and remote_addr:
            chrome_options.add_experimental_option("debuggerAddress", remote_addr)
            try:
                driver = webdriver.Chrome(options=chrome_options)
                st.session_state.driver = driver
                st.session_state.browser_ready = True
                st.success(f"已连接到远程浏览器 {remote_addr}")
                st.rerun()
            except Exception as e:
                st.error(f"连接失败: {e}\n请确保已启动Chrome远程调试：\n`chrome.exe --remote-debugging-port={remote_addr.split(':')[1]} --user-data-dir=C:\\selenium_profile`")
        else:
            # 非远程模式：自动启动新浏览器，需手动登录
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            st.session_state.driver = driver
            st.session_state.browser_ready = True
            st.info("新浏览器已启动，请手动登录目标系统。")
            # 提供一个按钮表示登录完成
            if st.button("✅ 我已登录完成"):
                st.session_state.login_done = True
                st.rerun()
else:
    st.success("✅ 浏览器已就绪")
    if not use_remote and not st.session_state.get('login_done', False):
        if st.button("✅ 标记登录完成"):
            st.session_state.login_done = True
            st.rerun()
    if st.session_state.get('login_done', False) or use_remote:
        # 已登录完成或远程已登录，继续后续操作
        if uploaded_file and st.button("🚀 2. 开始匹配与备案"):
            df = pd.read_excel(uploaded_file)
            required_cols = ['出发日期', '飞机注册号', '出发地', '到达地', '用途']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                st.error(f"Excel缺少列: {missing}")
                st.stop()
            excel_plans = []
            for _, row in df.iterrows():
                plan = {
                    'exec_date': str(row['出发日期']).split()[0],
                    'reg': row['飞机注册号'].strip(),
                    'dep': row['出发地'].strip(),
                    'arr': row['到达地'].strip(),
                    'purpose': row['用途'].strip()
                }
                excel_plans.append(plan)
            st.info(f"读取到 {len(excel_plans)} 条计划")

            auto = FlightPlanAutomation(st.session_state.driver)
            try:
                # 抓取现有计划
                with st.spinner("正在抓取网页已有计划..."):
                    existing = auto.get_existing_plans(page_url, row_xpath, cells_map)
                st.info(f"已抓取 {len(existing)} 条已有计划")
                existing_set = set()
                for e in existing:
                    existing_set.add((e[0], e[1], e[2], e[3]))
                unmatched = []
                for plan in excel_plans:
                    comp_date = date_format_for_compare(plan['exec_date'])
                    if (comp_date, plan['reg'], plan['dep'], plan['arr']) not in existing_set:
                        unmatched.append(plan)
                st.success(f"需要备案的计划数: {len(unmatched)}")
                if not unmatched:
                    st.balloons()
                    st.info("所有计划均已备案，无需操作")
                else:
                    progress_bar = st.progress(0)
                    log_area = st.empty()
                    success_count = 0
                    for idx, plan in enumerate(unmatched):
                        log_area.text(f"正在备案: {plan['reg']} - {plan['exec_date']} ({idx+1}/{len(unmatched)})")
                        if auto.add_new_plan(plan, xpath_config):
                            success_count += 1
                        time.sleep(1.5)
                        progress_bar.progress((idx+1)/len(unmatched))
                    st.success(f"✅ 完成！成功 {success_count} 条，失败 {len(unmatched)-success_count} 条")
                    if success_count == len(unmatched):
                        st.balloons()
            except Exception as e:
                st.error(f"自动化错误: {e}")
            finally:
                # 注意：不要关闭driver，因为后续可能还需使用；如需关闭可加按钮
                pass

# 关闭浏览器按钮（独立）
if st.session_state.browser_ready and st.button("🔒 关闭浏览器"):
    try:
        st.session_state.driver.quit()
    except:
        pass
    st.session_state.browser_ready = False
    st.session_state.driver = None
    st.session_state.login_done = False
    st.success("浏览器已关闭")
    st.rerun()

st.caption("💡 使用说明：\n"
           "1. 在侧边栏正确配置所有XPath（需根据实际网页审查元素填写）\n"
           "2. 推荐使用远程调试模式：先手动启动Chrome（带调试端口）并登录系统\n"
           "3. 点击「连接浏览器」→ 若普通模式则手动登录后点击「标记登录完成」→ 上传Excel → 开始备案")
