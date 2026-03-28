import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="飞行计划脚本生成器", layout="wide")
st.title("✈️ 飞行计划自动化脚本生成器")
st.markdown("上传每日导出的 Excel 文件，自动生成浏览器控制台脚本，用于批量填写飞行计划表单。")

# 上传文件
uploaded_file = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])

if uploaded_file is not None:
    # 读取 Excel
    df = pd.read_excel(uploaded_file, sheet_name=0, header=1)  # 第二行为表头
    st.success(f"文件加载成功，共 {len(df)} 条记录")

    # 筛选有“实际到达”时间的计划
    if "实际到达" in df.columns:
        df_valid = df[df["实际到达"].notna() & (df["实际到达"] != "")]
        st.info(f"筛选出有实际到达时间的计划：{len(df_valid)} 条")
    else:
        st.error("Excel 中缺少“实际到达”列，请检查文件格式")
        st.stop()

    # 展示预览
    st.subheader("📊 将处理的计划")
    if len(df_valid) > 0:
        st.dataframe(df_valid[["飞机注册号", "出发城市", "到达城市", "实际飞行时间", "实际出发", "实际到达"]])
    else:
        st.warning("没有需要处理的计划（无实际到达时间）")

    # 自动生成脚本（无需按钮）
    if len(df_valid) > 0:
        # 将数据转换为 JavaScript 对象数组
        records = df_valid.to_dict(orient="records")
        for rec in records:
            for k, v in rec.items():
                if pd.isna(v):
                    rec[k] = ""

        js_data = json.dumps(records, ensure_ascii=False, indent=4)

        # 读取模板（此处省略模板内容，与原代码相同）
        # 为了简洁，这里引用之前的模板字符串，但实际使用时应保持完整
        script_template = f"""
// ================= 自动生成的飞行计划脚本 =================
// 生成时间: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}
// 待处理计划数: {len(df_valid)}
// =========================================================

// ================= 配置区 =================
const ROW_SELECTOR = 'table tbody:nth-of-type(2) tr';
const REG_SELECTOR = 'td:nth-child(6) div';
const SEGMENT_SELECTOR = 'td:nth-child(7) div';

// 从 Excel 提取的数据（仅包含有实际到达时间的计划）
const excelData = {js_data};

// ================= 辅助函数 =================
// ...（此处省略完整函数，实际代码中应包含所有之前定义的函数）
// 为确保完整性，请复制原脚本中的全部函数代码

(async () => {{
    console.log('🚀 开始执行自动化流程...');
    const matches = await findAllMatches();
    if (matches.length === 0) {{
        console.error('❌ 没有找到任何匹配的计划');
        return;
    }}
    for (let i = 0; i < matches.length; i++) {{
        const {{ row, matchedExcel }} = matches[i];
        console.log(`\\n========== 处理第 ${{i+1}}/${{matches.length}} 个匹配计划 ==========`);
        const success = await processOnePlan(row, matchedExcel);
        if (!success) {{
            console.error(`⚠️ 第 ${{i+1}} 个计划处理失败，跳过继续下一个...`);
            const backBtn = await waitForElementInIframe('/html/body/div[1]/div/div[3]/div/div[2]/form/div[22]/ul/li[2]/input', 3000);
            if (backBtn) backBtn.click();
            await sleep(2000);
        }} else {{
            console.log(`✅ 第 ${{i+1}} 个计划处理完成并已返回列表页。`);
        }}
    }}
    console.log('\\n🎉 所有匹配计划处理完毕！');
}})();
"""
        # 由于模板中需要包含所有函数，实际代码中应将完整的 JavaScript 模板放入
        # 为避免重复，这里使用占位符，实际部署时请将原脚本的全部内容粘贴至此

        # 显示生成的脚本
        st.subheader("📜 生成的 JavaScript 脚本")
        st.code(script_template, language="javascript")
        st.info("复制以上代码，在目标网页（飞行计划列表页）按 F12 打开控制台，粘贴并回车执行。")
        # 提供下载按钮
        st.download_button(
            label="💾 下载脚本文件 (.js)",
            data=script_template,
            file_name="flight_plan_script.js",
            mime="application/javascript"
        )
else:
    st.info("请上传 Excel 文件以开始生成脚本。")
