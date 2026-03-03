import streamlit as st
import sys
import os
import traceback

# 把当前目录加入 Python 路径，以便导入你的代码
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入你原来的代码（假设文件名为 route_app.py）
from route_app import step1_extract, step2_reduce, step3_add_hash

# ===================== Streamlit 网页界面 =====================
st.title("✈️ 航路文本处理工具")

# 输入框（添加 key）
input_text = st.text_area("请输入待处理的航路文本：", height=200, key="route_input")

# 处理按钮（添加 key）
if st.button("开始处理", key="process_button"):
    if input_text.strip():
        with st.spinner("正在处理..."):
            try:
                seq, fmt = step1_extract(input_text)
                if fmt == 'table':
                    seq = step2_reduce(seq)
                    seq = step3_add_hash(seq)
                result = ' '.join(seq)
                
                # 显示结果（添加 key）
                st.success("处理完成！")
                st.code(result, language="text", key="result_code")
                
                # 一键复制按钮（添加 key）
                st.markdown(f"""
                <button onclick="navigator.clipboard.writeText(`{result}`)">一键复制结果</button>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"处理失败：{str(e)}")
                st.code(traceback.format_exc())  # 显示完整的错误堆栈
    else:
        st.warning("请输入需要处理的文本！")
