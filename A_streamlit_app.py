import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="飞行计划脚本生成器", layout="wide")
st.title("✈️ 飞行计划自动化脚本生成器")
st.markdown("上传每日导出的 Excel 文件，自动生成浏览器控制台脚本，用于批量填写飞行计划表单。")

# 完整的 JavaScript 模板（所有函数已包含）
JS_TEMPLATE = """
// ================= 自动生成的飞行计划脚本 =================
// 生成时间: {timestamp}
// 待处理计划数: {count}
// =========================================================

// ================= 配置区 =================
const ROW_SELECTOR = 'table tbody:nth-of-type(2) tr';
const REG_SELECTOR = 'td:nth-child(6) div';
const SEGMENT_SELECTOR = 'td:nth-child(7) div';

// 从 Excel 提取的数据（仅包含有实际到达时间的计划）
const excelData = {excel_data};

// ================= 辅助函数 =================
function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

function normalizeReg(reg) {{
    return reg.replace(/[-\\s]/g, '').trim();
}}

function getRegFromRow(row) {{
    const regElement = row.querySelector(REG_SELECTOR);
    if (!regElement) return null;
    return normalizeReg(regElement.innerText.trim());
}}

function extractKeywordsFromPart(part) {{
    let afterPrefix = part.replace(/^(境内|境外)-/, '');
    const segments = afterPrefix.split('-');
    const keywords = [];
    for (let seg of segments) {{
        const words = seg.split(/\\s+/);
        for (let w of words) if (w) keywords.push(w);
    }}
    return keywords;
}}

function getSegmentKeywords(row) {{
    const segElement = row.querySelector(SEGMENT_SELECTOR);
    if (!segElement) return null;
    const text = segElement.innerText.trim();
    if (!text) return null;
    const parts = text.split(',');
    if (parts.length < 2) return null;
    const depPart = parts[0].trim();
    const arrPart = parts[1].trim();
    const depKeywords = extractKeywordsFromPart(depPart);
    const arrKeywords = extractKeywordsFromPart(arrPart);
    return {{ depKeywords, arrKeywords }};
}}

function isMatchSegment(rowData, depKeywords, arrKeywords) {{
    const depCity = rowData["出发城市"] || "";
    const arrCity = rowData["到达城市"] || "";
    const depMatch = depKeywords.some(kw => depCity.includes(kw));
    const arrMatch = arrKeywords.some(kw => arrCity.includes(kw));
    return depMatch && arrMatch;
}}

async function getMainDoc() {{
    const iframe = document.querySelector('#main');
    if (!iframe) {{ console.error('未找到 #main iframe'); return null; }}
    let doc = iframe.contentDocument;
    while (!doc || !doc.querySelector('body')) {{
        await sleep(200);
        doc = iframe.contentDocument;
    }}
    return doc;
}}

async function waitForTable() {{
    const start = Date.now();
    while (Date.now() - start < 10000) {{
        const doc = await getMainDoc();
        if (!doc) return null;
        const rows = doc.querySelectorAll(ROW_SELECTOR);
        if (rows.length > 0) return rows;
        await sleep(300);
    }}
    return null;
}}

async function findAllMatches() {{
    const rows = await waitForTable();
    if (!rows) {{
        console.error('❌ 未找到表格行');
        return [];
    }}
    console.log(`📋 找到 ${{rows.length}} 个计划行，开始匹配...`);
    const matches = [];
    for (let i = 0; i < rows.length; i++) {{
        const row = rows[i];
        const regNo = getRegFromRow(row);
        if (!regNo) continue;
        const keywords = getSegmentKeywords(row);
        if (!keywords) continue;
        const {{ depKeywords, arrKeywords }} = keywords;
        console.log(`🔍 第 ${{i+1}} 行：机号 ${{regNo}}，出发关键词: [${{depKeywords.join(", ")}}]，到达关键词: [${{arrKeywords.join(", ")}}]`);
        const matched = excelData.find(r => normalizeReg(r["飞机注册号"]) === regNo && isMatchSegment(r, depKeywords, arrKeywords));
        if (matched) {{
            console.log(`✅ 匹配成功：第 ${{i+1}} 行，机号 ${{regNo}}`);
            matches.push({{ row, matchedExcel: matched }});
        }}
    }}
    console.log(`📊 共匹配到 ${{matches.length}} 条计划`);
    return matches;
}}

async function waitForElementInIframe(xpath, timeout = 15000) {{
    const start = Date.now();
    while (Date.now() - start < timeout) {{
        const doc = await getMainDoc();
        if (!doc) return null;
        const el = doc.evaluate(xpath, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (el) return el;
        await sleep(300);
    }}
    return null;
}}

function setDateInput(inputEl, dateStr) {{
    if (!inputEl) return false;
    inputEl.value = dateStr;
    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
    inputEl.blur();
    return true;
}}

async function setSelectValue(selectEl, valueText) {{
    if (!selectEl) return false;
    for (let i = 0; i < selectEl.options.length; i++) {{
        const opt = selectEl.options[i];
        if (opt.text === valueText || opt.text.includes(valueText)) {{
            selectEl.selectedIndex = i;
            selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await sleep(300);
            console.log(`✅ 已选择 "${{valueText}}"`);
            return true;
        }}
    }}
    console.warn(`⚠️ 未找到选项 "${{valueText}}"`);
    return false;
}}

function getAirportNameFromCity(city) {{
    const firstPart = city.split(/\\s+/)[0];
    return firstPart + "机场";
}}

function setNumberInput(inputEl, value) {{
    if (!inputEl) return false;
    inputEl.value = value;
    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
    inputEl.blur();
    return true;
}}

const CITY_MAP = {{
    "上海虹桥": "上海", "成都双流": "四川", "哈萨克斯坦阿拉木图": "哈萨克斯坦", "香港": "香港", "贵阳龙洞堡": "贵州"
}};

const CITY_DETAIL_MAP = {{
    "北京首都": {{ "province": "北京", "district": "顺义区" }}, "北京大兴": {{ "province": "北京", "district": "大兴区" }},
    "天津滨海": {{ "province": "天津", "district": "滨海新区" }}, "上海虹桥": {{ "province": "上海", "district": "闵行区" }},
    "上海浦东": {{ "province": "上海", "district": "浦东新区" }}, "重庆江北": {{ "province": "重庆", "district": "江北区" }},
    "成都双流": {{ "province": "四川", "district": "成都" }}, "贵阳龙洞堡": {{ "province": "贵州", "district": "贵阳" }}
}};

function getLocationInfo(city) {{
    const domesticKeywords = ["北京","上海","天津","重庆","广州","深圳","珠海","汕头","佛山","江门","湛江","茂名","肇庆","惠州","梅州","汕尾","河源","阳江","清远","东莞","中山","潮州","揭阳","云浮","南京","无锡","徐州","常州","苏州","南通","连云港","淮安","盐城","扬州","镇江","泰州","宿迁","杭州","宁波","温州","嘉兴","湖州","绍兴","金华","衢州","舟山","台州","丽水","合肥","芜湖","蚌埠","淮南","马鞍山","淮北","铜陵","安庆","黄山","滁州","阜阳","宿州","六安","亳州","池州","宣城","福州","厦门","莆田","三明","泉州","漳州","南平","龙岩","宁德","南昌","景德镇","萍乡","九江","新余","鹰潭","赣州","吉安","宜春","抚州","上饶","济南","青岛","淄博","枣庄","东营","烟台","潍坊","济宁","泰安","威海","日照","临沂","德州","聊城","滨州","菏泽","郑州","开封","洛阳","平顶山","安阳","鹤壁","新乡","焦作","濮阳","许昌","漯河","三门峡","南阳","商丘","信阳","周口","驻马店","武汉","黄石","十堰","宜昌","襄阳","鄂州","荆门","孝感","荆州","黄冈","咸宁","随州","长沙","株洲","湘潭","衡阳","邵阳","岳阳","常德","张家界","益阳","郴州","永州","怀化","娄底","成都","自贡","攀枝花","泸州","德阳","绵阳","广元","遂宁","内江","乐山","南充","眉山","宜宾","广安","达州","雅安","巴中","资阳","贵阳","六盘水","遵义","安顺","毕节","铜仁","昆明","曲靖","玉溪","保山","昭通","丽江","普洱","临沧","西安","铜川","宝鸡","咸阳","渭南","延安","汉中","榆林","安康","商洛","兰州","嘉峪关","金昌","白银","天水","武威","张掖","平凉","酒泉","庆阳","定西","陇南","西宁","海东","银川","石嘴山","吴忠","固原","中卫","乌鲁木齐","克拉玛依","吐鲁番","哈密","昌吉","博尔塔拉","巴音郭楞","阿克苏","克孜勒苏","喀什","和田","伊犁","塔城","阿勒泰","呼和浩特","包头","乌海","赤峰","通辽","鄂尔多斯","呼伦贝尔","巴彦淖尔","乌兰察布","南宁","柳州","桂林","梧州","北海","防城港","钦州","贵港","玉林","百色","贺州","河池","来宾","崇左","海口","三亚","三沙","儋州","石家庄","唐山","秦皇岛","邯郸","邢台","保定","张家口","承德","沧州","廊坊","衡水","太原","大同","阳泉","长治","晋城","朔州","晋中","运城","忻州","临汾","吕梁","沈阳","大连","鞍山","抚顺","本溪","丹东","锦州","营口","阜新","辽阳","盘锦","铁岭","朝阳","葫芦岛","长春","吉林","四平","辽源","通化","白山","松原","白城","哈尔滨","齐齐哈尔","鸡西","鹤岗","双鸭山","大庆","伊春","佳木斯","七台河","牡丹江","黑河","绥化"];
    const isDomestic = domesticKeywords.some(keyword => city.includes(keyword));
    if (isDomestic) {{
        let region = CITY_MAP[city];
        if (!region) {{
            const match = city.match(/^([^\\s\\-]+)/);
            region = match ? match[1] : city;
        }}
        return {{ zone: "境内", region: region, needThirdSelect: true }};
    }} else {{
        let country = CITY_MAP[city];
        if (!country) {{
            const parts = city.split(/[\\s\\-]/);
            country = parts[0];
        }}
        return {{ zone: "境外", region: country, needThirdSelect: false }};
    }}
}}

async function fillSegmentSelects(container, city) {{
    const selects = container.querySelectorAll('select');
    if (selects.length < 2) {{
        console.warn('航段容器内 select 数量不足');
        return false;
    }}
    const info = getLocationInfo(city);
    if (info.zone === "境外") {{
        await setSelectValue(selects[0], info.zone);
        await setSelectValue(selects[1], info.region);
        return true;
    }}
    const detail = CITY_DETAIL_MAP[city];
    if (!detail) {{
        console.warn(`未找到城市 ${{city}} 的详细映射，使用降级处理`);
        await setSelectValue(selects[0], "境内");
        await setSelectValue(selects[1], info.region);
        return true;
    }}
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], detail.province);
    await sleep(1500);
    const newSelects = container.querySelectorAll('select');
    if (newSelects.length < 3) {{
        console.warn('重新获取后第三个下拉框不存在');
        return false;
    }}
    const thirdSelect = newSelects[2];
    let targetIndex = -1;
    for (let i = 0; i < thirdSelect.options.length; i++) {{
        if (thirdSelect.options[i].text.includes(detail.district)) {{
            targetIndex = i;
            break;
        }}
    }}
    if (targetIndex !== -1) {{
        thirdSelect.selectedIndex = targetIndex;
        thirdSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        console.log(`已选择第三个下拉框: ${{thirdSelect.options[targetIndex].text}}`);
    }} else {{
        console.warn(`未找到区县选项: ${{detail.district}}`);
    }}
    await sleep(500);
    return true;
}}

async function handleAirportBlock(blockIndex, city, label) {{
    const firstSelectXPath = `/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div${{blockIndex}}/div[2]/div/div[1]/div/select[1]`;
    const secondSelectXPath = `/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div${{blockIndex}}/div[2]/div/div[1]/div/select[2]`;
    console.log(`⏳ 处理 ${{label}} 区块...`);
    const firstSelect = await waitForElementInIframe(firstSelectXPath, 10000);
    if (!firstSelect) {{
        console.error(`❌ 未找到 ${{label}} 第一个选择框`);
        return false;
    }}
    const targetValue = blockIndex === 1 ? '起飞机场' : '降落机场';
    await setSelectValue(firstSelect, targetValue);
    const secondSelect = await waitForElementInIframe(secondSelectXPath, 10000);
    if (!secondSelect) {{
        console.error(`❌ 未找到 ${{label}} 第二个选择框`);
        return false;
    }}
    const info = getLocationInfo(city);
    if (info.zone === "境内") {{
        console.log(`🛬 ${{label}} 境内机场: ${{city}}，尝试选择匹配的机场...`);
        const selected = await setSelectValue(secondSelect, city);
        if (!selected) {{
            console.error(`❌ 未找到匹配的机场选项（包含“${{city}}”），跳过 ${{label}} 处理`);
            return false;
        }}
        await sleep(800);
        const container = secondSelect.closest('div');
        if (!container) {{
            console.error(`❌ 未找到容器，无法填充 ${{label}} 境内机场详细信息`);
            return false;
        }}
        await fillSegmentSelects(container, city);
    }} else {{
        console.log(`🛫 ${{label}} 境外机场: ${{city}}，选择“其它”...`);
        const otherSelected = await setSelectValue(secondSelect, '其它');
        if (!otherSelected) {{
            console.error(`❌ 无法选择“其它”，跳过 ${{label}} 处理`);
            return false;
        }}
        await sleep(800);
        let zoneSelectXPath, zoneSelect2XPath, airportNameInputXPath;
        if (blockIndex === 2) {{
            zoneSelectXPath = '/html/body/div/div[1]/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[2]/div/select[1]';
            zoneSelect2XPath = '/html/body/div/div[1]/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[2]/div/select[2]';
            airportNameInputXPath = '/html/body/div/div[1]/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[2]/div/input';
        }} else {{
            zoneSelectXPath = `/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div${{blockIndex}}/div[2]/div/div[2]/div/select[1]`;
            zoneSelect2XPath = `/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div${{blockIndex}}/div[2]/div/div[2]/div/select[2]`;
            airportNameInputXPath = `/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div${{blockIndex}}/div[2]/div/div[2]/div/input`;
        }}
        const zoneSelect = await waitForElementInIframe(zoneSelectXPath, 10000);
        if (zoneSelect) await setSelectValue(zoneSelect, '境外');
        const zoneSelect2 = await waitForElementInIframe(zoneSelect2XPath, 10000);
        if (zoneSelect2) await setSelectValue(zoneSelect2, '境外');
        const airportNameInput = await waitForElementInIframe(airportNameInputXPath, 10000);
        if (airportNameInput) {{
            const airportName = getAirportNameFromCity(city);
            console.log(`📝 填入 ${{label}} 机场名称: ${{airportName}}`);
            setNumberInput(airportNameInput, airportName);
        }}
    }}
    return true;
}}

async function handleSecondFlightTime() {{
    const hourXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[5]/div/input[1]';
    const minuteXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[5]/div/input[2]';
    const countXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[2]/div[2]/div/div[6]/div/input';
    const hourInput = await waitForElementInIframe(hourXPath, 10000);
    const minuteInput = await waitForElementInIframe(minuteXPath, 10000);
    const countInput = await waitForElementInIframe(countXPath, 10000);
    if (hourInput && minuteInput && countInput) {{
        console.log('⏱️ 填入第二个飞行时间: 00:00，飞行架次数: 0');
        setNumberInput(hourInput, '0');
        setNumberInput(minuteInput, '0');
        setNumberInput(countInput, '0');
        return true;
    }} else {{
        console.warn('⚠️ 未找到第二个飞行时间输入框');
        return false;
    }}
}}

async function handleDetailArea(depCity, arrCity) {{
    const detailXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[16]/div/input';
    const detailInput = await waitForElementInIframe(detailXPath, 10000);
    if (!detailInput) {{
        console.error('❌ 未找到详细作业区输入框');
        return false;
    }}
    const depAirport = depCity + "机场";
    const arrAirport = arrCity + "机场";
    const detailText = `${{depAirport}}-${{arrAirport}}`;
    console.log(`📝 填入详细作业区: ${{detailText}}`);
    setNumberInput(detailInput, detailText);
    return true;
}}

async function waitForReturnToList(timeout = 300000) {{
    const start = Date.now();
    console.log('⏳ 等待您手动点击“提交”后返回列表页...');
    while (Date.now() - start < timeout) {{
        const doc = await getMainDoc();
        if (!doc) return false;
        const rows = doc.querySelectorAll(ROW_SELECTOR);
        if (rows.length > 0) {{
            console.log('✅ 已返回列表页');
            return true;
        }}
        await sleep(2000);
    }}
    console.error('❌ 等待超时，未返回列表页');
    return false;
}}

async function processOnePlan(planRow, matchedExcel) {{
    console.log(`\\n🔧 开始处理计划：机号 ${{matchedExcel["飞机注册号"]}}`);
    const execBtn = planRow.querySelector('.icon-qidong, [class*="icon-qidong"]');
    if (!execBtn) {{
        console.error('❌ 未找到“执行”按钮，跳过');
        return false;
    }}
    console.log('🔘 点击“执行”按钮...');
    execBtn.click();
    await sleep(2000);
    const startDateXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[9]/div/input';
    const endDateXPath   = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[10]/div/input';
    const startInput = await waitForElementInIframe(startDateXPath);
    const endInput   = await waitForElementInIframe(endDateXPath);
    if (!startInput || !endInput) {{
        console.error('❌ 未找到日期输入框');
        return false;
    }}
    const startDate = matchedExcel["出发日期"];
    const endDate   = matchedExcel["到达日期"];
    console.log(`📅 填入作业开始日期: ${{startDate}}`);
    console.log(`📅 填入作业结束日期: ${{endDate}}`);
    setDateInput(startInput, startDate);
    setDateInput(endInput, endDate);
    const depCity = matchedExcel["出发城市"];
    if (!(await handleAirportBlock(1, depCity, "起飞"))) return false;
    const arrCity = matchedExcel["到达城市"];
    if (!(await handleAirportBlock(2, arrCity, "降落"))) return false;
    const actualFlightTime = matchedExcel["实际飞行时间"];
    if (actualFlightTime && actualFlightTime.includes(':')) {{
        const flightHourXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[1]/div[2]/div/div[5]/div/input[1]';
        const flightMinuteXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[1]/div[2]/div/div[5]/div/input[2]';
        const flightCountXPath = '/html/body/div[1]/div/div[3]/div/div[2]/form/div[11]/div[1]/div[2]/div/div[6]/div/input';
        const hourInput = await waitForElementInIframe(flightHourXPath, 10000);
        const minuteInput = await waitForElementInIframe(flightMinuteXPath, 10000);
        const countInput = await waitForElementInIframe(flightCountXPath, 10000);
        if (hourInput && minuteInput && countInput) {{
            const [hour, minute] = actualFlightTime.split(':');
            console.log(`⏱️ 填入第一个飞行时间: ${{hour}}:${{minute}}，飞行架次数: 1`);
            setNumberInput(hourInput, hour);
            setNumberInput(minuteInput, minute);
            setNumberInput(countInput, '1');
        }} else {{
            console.warn('⚠️ 未找到第一个飞行时间输入框');
        }}
    }} else {{
        console.warn(`⚠️ 实际飞行时间 "${{actualFlightTime}}" 格式不正确`);
    }}
    await handleSecondFlightTime();
    await handleDetailArea(depCity, arrCity);
    console.log('✅ 所有字段填写完成，请手动点击“提交”按钮。');
    const returned = await waitForReturnToList();
    if (!returned) {{
        console.error('❌ 未能检测到返回列表页，请手动返回后继续运行脚本。');
        return false;
    }}
    return true;
}}

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

    # 自动生成脚本
    if len(df_valid) > 0:
        # 转换数据
        records = df_valid.to_dict(orient="records")
        for rec in records:
            for k, v in rec.items():
                if pd.isna(v):
                    rec[k] = ""
        js_data = json.dumps(records, ensure_ascii=False, indent=4)

        # 填充模板
        script = JS_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            count=len(df_valid),
            excel_data=js_data
        )

        # 显示脚本
        st.subheader("📜 生成的 JavaScript 脚本")
        st.code(script, language="javascript")
        st.info("复制以上代码，在目标网页（飞行计划列表页）按 F12 打开控制台，粘贴并回车执行。")
        # 下载按钮
        st.download_button(
            label="💾 下载脚本文件 (.js)",
            data=script,
            file_name="flight_plan_script.js",
            mime="application/javascript"
        )
else:
    st.info("请上传 Excel 文件以开始生成脚本。")
