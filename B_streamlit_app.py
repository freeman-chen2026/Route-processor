# streamlit_app.py
import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# ---------- 内置国家名称列表（用于智能识别境外城市） ----------
COUNTRIES = [
    "香港", "澳门", "台湾", "蒙古", "朝鲜", "韩国", "日本", "菲律宾", "越南", "老挝",
    "柬埔寨", "缅甸", "泰国", "马来西亚", "文莱", "新加坡", "印度尼西亚", "东帝汶",
    "尼泊尔", "不丹", "孟加拉国", "印度", "巴基斯坦", "斯里兰卡", "马尔代夫",
    "哈萨克斯坦", "吉尔吉斯斯坦", "塔吉克斯坦", "乌兹别克斯坦", "土库曼斯坦",
    "阿富汗", "伊拉克", "伊朗", "叙利亚", "约旦", "黎巴嫩", "以色列", "巴勒斯坦",
    "沙特阿拉伯", "巴林", "卡塔尔", "科威特", "阿联酋", "阿曼", "也门", "格鲁吉亚",
    "亚美尼亚", "阿塞拜疆", "土耳其", "塞浦路斯", "芬兰", "瑞典", "挪威", "冰岛",
    "丹麦", "法罗群岛", "爱沙尼亚", "拉脱维亚", "立陶宛", "白俄罗斯", "俄罗斯",
    "乌克兰", "摩尔多瓦", "波兰", "捷克", "斯洛伐克", "匈牙利", "德国", "奥地利",
    "瑞士", "列支敦士登", "英国", "爱尔兰", "荷兰", "比利时", "卢森堡", "法国",
    "摩纳哥", "罗马尼亚", "保加利亚", "塞尔维亚", "马其顿", "阿尔巴尼亚", "希腊",
    "斯洛文尼亚", "克罗地亚", "波斯尼亚和墨塞哥维那", "意大利", "梵蒂冈", "圣马力诺",
    "马耳他", "西班牙", "葡萄牙", "安道尔", "埃及", "利比亚", "苏丹", "突尼斯",
    "阿尔及利亚", "摩洛哥", "毛里塔尼亚", "塞内加尔", "冈比亚", "马里", "布基纳法索",
    "几内亚", "几内亚比绍", "佛得角", "塞拉利昂", "利比里亚", "科特迪瓦", "加纳",
    "多哥", "贝宁", "尼日尔", "尼日利亚", "喀麦隆", "赤道几内亚", "乍得", "中非",
    "苏丹", "埃塞俄比亚", "吉布提", "索马里", "肯尼亚", "乌干达", "坦桑尼亚",
    "卢旺达", "布隆迪", "莫桑比克", "马达加斯加", "科摩罗", "毛里求斯", "塞舌尔",
    "纳米比亚", "博茨瓦纳", "津巴布韦", "赞比亚", "马拉维", "南非", "斯威士兰",
    "莱索托", "澳大利亚", "新西兰", "巴布亚新几内亚", "所罗门群岛", "瓦努阿图",
    "斐济", "萨摩亚", "汤加", "密克罗尼西亚", "马绍尔群岛", "帕劳", "瑙鲁", "基里巴斯",
    "图瓦卢", "美国", "加拿大", "墨西哥", "危地马拉", "伯利兹", "萨尔瓦多", "洪都拉斯",
    "尼加拉瓜", "哥斯达黎加", "巴拿马", "古巴", "牙买加", "海地", "多米尼加",
    "波多黎各", "巴哈马", "特立尼达和多巴哥", "巴巴多斯", "圣卢西亚", "圣文森特和格林纳丁斯",
    "格林纳达", "安提瓜和巴布达", "多米尼克", "圣基茨和尼维斯", "哥伦比亚", "委内瑞拉",
    "圭亚那", "苏里南", "厄瓜多尔", "秘鲁", "巴西", "玻利维亚", "巴拉圭", "智利",
    "阿根廷", "乌拉圭"
]

# 中国境内城市到省份的自动映射表（覆盖所有地级市及常见城市名）
CITY_TO_PROVINCE = {
    # 直辖市
    "北京": "北京", "上海": "上海", "天津": "天津", "重庆": "重庆",
    # 广东
    "广州": "广东", "深圳": "广东", "珠海": "广东", "汕头": "广东", "佛山": "广东", "江门": "广东",
    "湛江": "广东", "茂名": "广东", "肇庆": "广东", "惠州": "广东", "梅州": "广东", "汕尾": "广东",
    "河源": "广东", "阳江": "广东", "清远": "广东", "东莞": "广东", "中山": "广东", "潮州": "广东",
    "揭阳": "广东", "云浮": "广东",
    # 江苏
    "南京": "江苏", "无锡": "江苏", "徐州": "江苏", "常州": "江苏", "苏州": "江苏", "南通": "江苏",
    "连云港": "江苏", "淮安": "江苏", "盐城": "江苏", "扬州": "江苏", "镇江": "江苏", "泰州": "江苏",
    "宿迁": "江苏",
    # 浙江
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江", "嘉兴": "浙江", "湖州": "浙江", "绍兴": "浙江",
    "金华": "浙江", "衢州": "浙江", "舟山": "浙江", "台州": "浙江", "丽水": "浙江",
    # 安徽
    "合肥": "安徽", "芜湖": "安徽", "蚌埠": "安徽", "淮南": "安徽", "马鞍山": "安徽", "淮北": "安徽",
    "铜陵": "安徽", "安庆": "安徽", "黄山": "安徽", "滁州": "安徽", "阜阳": "安徽", "宿州": "安徽",
    "六安": "安徽", "亳州": "安徽", "池州": "安徽", "宣城": "安徽",
    # 福建
    "福州": "福建", "厦门": "福建", "莆田": "福建", "三明": "福建", "泉州": "福建", "漳州": "福建",
    "南平": "福建", "龙岩": "福建", "宁德": "福建",
    # 江西
    "南昌": "江西", "景德镇": "江西", "萍乡": "江西", "九江": "江西", "新余": "江西", "鹰潭": "江西",
    "赣州": "江西", "吉安": "江西", "宜春": "江西", "抚州": "江西", "上饶": "江西",
    # 山东
    "济南": "山东", "青岛": "山东", "淄博": "山东", "枣庄": "山东", "东营": "山东", "烟台": "山东",
    "潍坊": "山东", "济宁": "山东", "泰安": "山东", "威海": "山东", "日照": "山东", "临沂": "山东",
    "德州": "山东", "聊城": "山东", "滨州": "山东", "菏泽": "山东",
    # 河南
    "郑州": "河南", "开封": "河南", "洛阳": "河南", "平顶山": "河南", "安阳": "河南", "鹤壁": "河南",
    "新乡": "河南", "焦作": "河南", "濮阳": "河南", "许昌": "河南", "漯河": "河南", "三门峡": "河南",
    "南阳": "河南", "商丘": "河南", "信阳": "河南", "周口": "河南", "驻马店": "河南",
    # 湖北
    "武汉": "湖北", "黄石": "湖北", "十堰": "湖北", "宜昌": "湖北", "襄阳": "湖北", "鄂州": "湖北",
    "荆门": "湖北", "孝感": "湖北", "荆州": "湖北", "黄冈": "湖北", "咸宁": "湖北", "随州": "湖北",
    # 湖南
    "长沙": "湖南", "株洲": "湖南", "湘潭": "湖南", "衡阳": "湖南", "邵阳": "湖南", "岳阳": "湖南",
    "常德": "湖南", "张家界": "湖南", "益阳": "湖南", "郴州": "湖南", "永州": "湖南", "怀化": "湖南",
    "娄底": "湖南",
    # 四川
    "成都": "四川", "自贡": "四川", "攀枝花": "四川", "泸州": "四川", "德阳": "四川", "绵阳": "四川",
    "广元": "四川", "遂宁": "四川", "内江": "四川", "乐山": "四川", "南充": "四川", "眉山": "四川",
    "宜宾": "四川", "广安": "四川", "达州": "四川", "雅安": "四川", "巴中": "四川", "资阳": "四川",
    # 贵州
    "贵阳": "贵州", "六盘水": "贵州", "遵义": "贵州", "安顺": "贵州", "毕节": "贵州", "铜仁": "贵州",
    # 云南
    "昆明": "云南", "曲靖": "云南", "玉溪": "云南", "保山": "云南", "昭通": "云南", "丽江": "云南",
    "普洱": "云南", "临沧": "云南",
    # 陕西
    "西安": "陕西", "铜川": "陕西", "宝鸡": "陕西", "咸阳": "陕西", "渭南": "陕西", "延安": "陕西",
    "汉中": "陕西", "榆林": "陕西", "安康": "陕西", "商洛": "陕西",
    # 甘肃
    "兰州": "甘肃", "嘉峪关": "甘肃", "金昌": "甘肃", "白银": "甘肃", "天水": "甘肃", "武威": "甘肃",
    "张掖": "甘肃", "平凉": "甘肃", "酒泉": "甘肃", "庆阳": "甘肃", "定西": "甘肃", "陇南": "甘肃",
    # 青海
    "西宁": "青海", "海东": "青海",
    # 宁夏
    "银川": "宁夏", "石嘴山": "宁夏", "吴忠": "宁夏", "固原": "宁夏", "中卫": "宁夏",
    # 新疆
    "乌鲁木齐": "新疆", "克拉玛依": "新疆", "吐鲁番": "新疆", "哈密": "新疆",
    # 西藏
    "拉萨": "西藏", "日喀则": "西藏", "昌都": "西藏", "林芝": "西藏", "山南": "西藏", "那曲": "西藏",
    # 内蒙古
    "呼和浩特": "内蒙古", "包头": "内蒙古", "乌海": "内蒙古", "赤峰": "内蒙古", "通辽": "内蒙古",
    "鄂尔多斯": "内蒙古", "呼伦贝尔": "内蒙古", "巴彦淖尔": "内蒙古", "乌兰察布": "内蒙古",
    # 广西
    "南宁": "广西", "柳州": "广西", "桂林": "广西", "梧州": "广西", "北海": "广西", "防城港": "广西",
    "钦州": "广西", "贵港": "广西", "玉林": "广西", "百色": "广西", "贺州": "广西", "河池": "广西",
    "来宾": "广西", "崇左": "广西",
    # 海南
    "海口": "海南", "三亚": "海南", "三沙": "海南", "儋州": "海南",
    # 河北
    "石家庄": "河北", "唐山": "河北", "秦皇岛": "河北", "邯郸": "河北", "邢台": "河北", "保定": "河北",
    "张家口": "河北", "承德": "河北", "沧州": "河北", "廊坊": "河北", "衡水": "河北",
    # 山西
    "太原": "山西", "大同": "山西", "阳泉": "山西", "长治": "山西", "晋城": "山西", "朔州": "山西",
    "晋中": "山西", "运城": "山西", "忻州": "山西", "临汾": "山西", "吕梁": "山西",
    # 辽宁
    "沈阳": "辽宁", "大连": "辽宁", "鞍山": "辽宁", "抚顺": "辽宁", "本溪": "辽宁", "丹东": "辽宁",
    "锦州": "辽宁", "营口": "辽宁", "阜新": "辽宁", "辽阳": "辽宁", "盘锦": "辽宁", "铁岭": "辽宁",
    "朝阳": "辽宁", "葫芦岛": "辽宁",
    # 吉林
    "长春": "吉林", "吉林": "吉林", "四平": "吉林", "辽源": "吉林", "通化": "吉林", "白山": "吉林",
    "松原": "吉林", "白城": "吉林",
    # 黑龙江
    "哈尔滨": "黑龙江", "齐齐哈尔": "黑龙江", "鸡西": "黑龙江", "鹤岗": "黑龙江", "双鸭山": "黑龙江",
    "大庆": "黑龙江", "伊春": "黑龙江", "佳木斯": "黑龙江", "七台河": "黑龙江", "牡丹江": "黑龙江",
    "黑河": "黑龙江", "绥化": "黑龙江",
}

# 中国境内城市关键词（用于判断境内/境外，自动生成）
DOMESTIC_KEYWORDS = list(CITY_TO_PROVINCE.keys())

# 默认境内机场详细映射（用于需要精确区县的特殊情况，如北京首都需选顺义区）
# 这些会覆盖自动提取的区县，如需自动识别可留空或删除
DEFAULT_DETAIL_MAP = {
    "北京首都": {"province": "北京", "district": "顺义区"},
    "北京大兴": {"province": "北京", "district": "大兴区"},
    "天津滨海": {"province": "天津", "district": "滨海新区"},
    "上海虹桥": {"province": "上海", "district": "闵行区"},
    "上海浦东": {"province": "上海", "district": "浦东新区"},
    "重庆江北": {"province": "重庆", "district": "江北区"},
}

def parse_flight_time(time_str):
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours, minutes
    except:
        return 0, 0

def extract_country(city_name):
    for country in COUNTRIES:
        if country in city_name:
            return country
    parts = re.split(r'[\s\-]', city_name)
    if parts:
        return parts[0]
    return city_name

def get_province_from_city(city):
    for keyword, province in CITY_TO_PROVINCE.items():
        if keyword in city:
            return province
    return city.split()[0] if city.split() else city

def extract_district_from_city(city):
    """从城市名中提取区县名：优先匹配CITY_TO_PROVINCE中的关键词，取第一个匹配的关键词"""
    for keyword in CITY_TO_PROVINCE.keys():
        if keyword in city:
            return keyword
    # 未匹配到，取第一个词并去掉“机场”后缀
    district = city.split()[0] if city.split() else city
    if district.endswith('机场'):
        district = district[:-2]
    return district

def build_city_mappings(df, custom_detail_map):
    cities = set()
    for _, row in df.iterrows():
        dep = str(row["出发城市"]).strip()
        arr = str(row["到达城市"]).strip()
        cities.add(dep)
        cities.add(arr)

    detail_map = {**DEFAULT_DETAIL_MAP, **custom_detail_map}
    city_map = {}

    for city in cities:
        # 如果已存在详细映射，直接使用
        if city in detail_map:
            province = detail_map[city]["province"]
            district = detail_map[city]["district"]
            city_map[city] = province
            continue

        # 判断境内
        is_domestic = any(kw in city for kw in DOMESTIC_KEYWORDS)
        if is_domestic:
            province = get_province_from_city(city)
            district = extract_district_from_city(city)
            detail_map[city] = {"province": province, "district": district}
            city_map[city] = province
        else:
            country = extract_country(city)
            city_map[city] = country
            # 境外城市不加入 detail_map

    return city_map, detail_map

def generate_flight_records(df):
    records = []
    for _, row in df.iterrows():
        purpose_raw = row.get("用途", "")
        # 如果用途包含“维修”或“调机”，则选择“调机”，否则“自用飞行”
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
        records.append(record)
    return json.dumps(records, ensure_ascii=False, indent=4)

def generate_js_script(flight_records_json, city_map_json, city_detail_map_json):
    template = """
// ==================== 自动生成的飞行计划填报脚本 ====================
// 生成时间: __DATETIME__
// 总计 __COUNT__ 条计划

// ==================== 获取最新 iframe 文档 ====================
async function getCurrentDoc() {
    const iframe = document.querySelector('#main');
    if (!iframe) throw new Error('未找到 iframe');
    let doc = iframe.contentDocument;
    while (!doc || !doc.querySelector('body')) {
        await sleep(200);
        doc = iframe.contentDocument;
    }
    return doc;
}

// ==================== 等待元素出现 ====================
async function waitForElement(selector, timeout = 15000, isXPath = false) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const doc = await getCurrentDoc();
        let el;
        if (isXPath) {
            el = doc.evaluate(selector, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        } else {
            el = doc.querySelector(selector);
        }
        if (el) return el;
        await sleep(500);
    }
    return null;
}

// ==================== 弹窗确定按钮搜索 ====================
async function waitForDialogConfirmButton(timeout = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        let btn = document.evaluate('//a[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!btn) btn = document.evaluate('//button[contains(text(), "确定")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (btn) return btn;
        try {
            const doc = await getCurrentDoc();
            btn = doc.evaluate('//a[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (!btn) btn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (btn) return btn;
        } catch(e) {}
        await sleep(300);
    }
    return null;
}

// ==================== 确保当前在列表页 ====================
async function ensureListPage() {
    const btn = await waitForElement('input.query.yuanjiao', 15000);
    if (btn) return true;
    console.log('当前不在列表页，尝试关闭可能遗留的对话框...');
    const doc = await getCurrentDoc();
    let closeBtn = doc.evaluate('//button[contains(text(), "取消")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) closeBtn = doc.evaluate('//button[contains(text(), "返回")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (closeBtn) {
        closeBtn.click();
        console.log('已点击关闭按钮，等待返回列表页');
        await sleep(1000);
        const backBtn = await waitForElement('input.query.yuanjiao', 10000);
        return backBtn !== null;
    } else {
        console.warn('未找到返回按钮，请手动关闭对话框后继续（脚本将等待5秒）');
        await sleep(5000);
        const backBtn = await waitForElement('input.query.yuanjiao', 5000);
        return backBtn !== null;
    }
}

// ==================== 城市到地区/国家的映射 ====================
const CITY_MAP = __CITY_MAP__;

// 境内机场到（省份，区县）的详细映射
const CITY_DETAIL_MAP = __CITY_DETAIL_MAP__;

function getLocationInfo(city) {
    const domesticKeywords = __DOMESTIC_KEYWORDS__;
    const isDomestic = domesticKeywords.some(keyword => city.includes(keyword));
    
    if (isDomestic) {
        let region = CITY_MAP[city];
        if (!region) {
            const match = city.match(/^([^\\s\\-]+)/);
            region = match ? match[1] : city;
        }
        return { zone: "境内", region: region, needThirdSelect: true };
    } else {
        let country = CITY_MAP[city];
        if (!country) {
            const parts = city.split(/[\\s\\-]/);
            country = parts[0];
        }
        return { zone: "境外", region: country, needThirdSelect: false };
    }
}

// ==================== 选择器 ====================
const SELECTORS = {
    addBtnCSS: 'input.query.yuanjiao',
    aircraftSelect: '//*[@id="ele7"]',
    specialSelect: '#specialf',
    certSelect: '#operationCertificate',
    operateSelect: '#businessOperation',
    // 非经营活动项目下拉框（用途）— 使用用户提供的最新 XPath
    purposeSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[13]/div/select[1]',
    startDate: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[9]/div/input',
    endDate: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[10]/div/input',
    firstFlightHour: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[1]',
    firstFlightMinute: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[2]/div/input[2]',
    firstFlights: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[3]/div/input',
    addSegmentBtn: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div/button',
    secondFlightHour: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[1]',
    secondFlightMinute: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[2]/div/input[2]',
    secondFlights: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[3]/div/input',
    detailArea: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[25]/div/input',
    customer: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[27]/div/input',
    base: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[28]/div/input',
    operator: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[29]/div/input',
    phone: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[30]/div/input',
    contractSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[36]/div/select',
    insuranceSelect: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[37]/div/select',
    submitBtn: '/html/body/div[1]/div/div[3]/div/div[2]/form/div[40]/ul/li[2]/input',
};

// ==================== 辅助函数 ====================
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function setSelectValue(selectElement, valueText) {
    for (let i = 0; i < selectElement.options.length; i++) {
        const opt = selectElement.options[i];
        if (opt.text === valueText || opt.text.includes(valueText)) {
            selectElement.selectedIndex = i;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            await sleep(300);
            return true;
        }
    }
    console.warn(`未找到选项: ${valueText}，可用选项：`, Array.from(selectElement.options).map(o => o.text));
    return false;
}

function setDateInput(inputEl, dateStr) {
    if (!inputEl) return false;
    inputEl.value = dateStr;
    inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    inputEl.blur();
    sleep(200);
    return true;
}

// 通用航段填充函数（改进版，不再自动选择第二个选项）
async function fillSegmentSelects(container, city) {
    const selects = container.querySelectorAll('select');
    if (selects.length < 2) {
        console.warn('航段容器内 select 数量不足');
        return false;
    }
    
    const info = getLocationInfo(city);
    if (info.zone === "境外") {
        await setSelectValue(selects[0], info.zone);
        await setSelectValue(selects[1], info.region);
        return true;
    }
    
    // 境内
    const detail = CITY_DETAIL_MAP[city];
    if (!detail) {
        console.warn(`未找到城市 ${city} 的详细映射，将使用降级处理`);
        await setSelectValue(selects[0], "境内");
        await setSelectValue(selects[1], info.region);
        if (selects.length >= 3) {
            const thirdSelect = selects[2];
            // 点击“请选择”按钮
            let chooseBtn = null;
            const possibleButtons = container.querySelectorAll('button, div, span');
            for (let el of possibleButtons) {
                if (el.innerText && el.innerText.includes('请选择')) {
                    chooseBtn = el;
                    break;
                }
            }
            if (chooseBtn) {
                chooseBtn.click();
                await sleep(1000);
            }
            // 等待选项加载
            await sleep(1000);
            // 不再自动选择第二个选项，仅输出警告
            if (thirdSelect.options.length > 1) {
                console.warn(`未找到区县选项，第三个下拉框将保持当前选择（默认为第一个选项）`);
            } else {
                console.warn('第三个下拉框选项不足');
            }
        }
        return true;
    }
    
    // 设置境内和省份
    await setSelectValue(selects[0], "境内");
    await setSelectValue(selects[1], detail.province);
    
    // 等待1.5秒，让第三个下拉框的选项加载
    console.log(`等待第三个下拉框选项加载 (${detail.district})...`);
    await sleep(1500);
    
    // 重新获取第三个下拉框元素
    const newSelects = container.querySelectorAll('select');
    if (newSelects.length < 3) {
        console.warn('重新获取后第三个下拉框不存在');
        return false;
    }
    const thirdSelect = newSelects[2];
    
    // 打印选项列表
    console.log('第三个下拉框当前选项:', Array.from(thirdSelect.options).map(o => o.text));
    
    // 尝试匹配目标区县
    let targetIndex = -1;
    for (let i = 0; i < thirdSelect.options.length; i++) {
        if (thirdSelect.options[i].text.includes(detail.district)) {
            targetIndex = i;
            break;
        }
    }
    
    if (targetIndex !== -1) {
        thirdSelect.selectedIndex = targetIndex;
        thirdSelect.dispatchEvent(new Event('change', { bubbles: true }));
        console.log(`已选择第三个下拉框: ${thirdSelect.options[targetIndex].text}`);
    } else {
        console.warn(`未找到区县选项: ${detail.district}，请手动选择或补充映射。`);
        // 不再自动选择
    }
    await sleep(500);
    return true;
}

async function fillFirstSegmentSelects(city) {
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[1]/div[1]/div/div', 5000, true);
    if (!container) {
        console.warn('未找到第一个航段容器');
        return false;
    }
    return fillSegmentSelects(container, city);
}

async function fillFirstSegmentTime(record) {
    const hourInput = await waitForElement(SELECTORS.firstFlightHour, 5000, true);
    const minuteInput = await waitForElement(SELECTORS.firstFlightMinute, 5000, true);
    const flightsInput = await waitForElement(SELECTORS.firstFlights, 5000, true);
    if (hourInput && minuteInput && flightsInput) {
        hourInput.value = record.flight_hours.toString().padStart(2, '0');
        minuteInput.value = record.flight_minutes.toString().padStart(2, '0');
        flightsInput.value = 1;
        hourInput.dispatchEvent(new Event('input', { bubbles: true }));
        minuteInput.dispatchEvent(new Event('input', { bubbles: true }));
        flightsInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log(`已填入第一个航段时间: ${record.flight_hours}:${record.flight_minutes}, 架次: 1`);
        return true;
    }
    console.warn('无法填入第一个航段时间和架次');
    return false;
}

async function fillSecondSegmentSelects(city) {
    const container = await waitForElement('/html/body/div[1]/div/div[3]/div/div[2]/form/div[23]/div[2]/div[1]/div/div', 5000, true);
    if (!container) {
        console.warn('未找到第二个航段容器');
        return false;
    }
    return fillSegmentSelects(container, city);
}

async function fillSecondSegmentTime() {
    const hourInput = await waitForElement(SELECTORS.secondFlightHour, 5000, true);
    const minuteInput = await waitForElement(SELECTORS.secondFlightMinute, 5000, true);
    const flightsInput = await waitForElement(SELECTORS.secondFlights, 5000, true);
    if (hourInput && minuteInput && flightsInput) {
        hourInput.value = '00';
        minuteInput.value = '00';
        flightsInput.value = 0;
        hourInput.dispatchEvent(new Event('input', { bubbles: true }));
        minuteInput.dispatchEvent(new Event('input', { bubbles: true }));
        flightsInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入第二个航段时间: 00:00, 架次: 0');
        return true;
    }
    console.warn('无法填入第二个航段时间和架次');
    return false;
}

function formatRegNumber(reg) {
    if (reg.includes('-')) return reg;
    const match = reg.match(/^([A-Z]+)(\\d+[A-Z]*)$/);
    if (match) return `${match[1]}-${match[2]}`;
    return reg;
}

async function selectAircraft(reg) {
    const regForSelect = formatRegNumber(reg);
    console.log(`尝试选择飞机: ${regForSelect}`);
    
    const airbox = await waitForElement('//*[@id="airbox"]', 10000, true);
    if (!airbox) {
        console.warn('未找到飞机选择对话框');
        return false;
    }
    const doc = await getCurrentDoc();
    
    let span = doc.evaluate(`//span[text()='${regForSelect}']`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!span) {
        span = doc.evaluate(`//span[contains(text(), '${regForSelect}')]`, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (!span) {
        console.warn(`未找到包含注册号 ${regForSelect} 的 span 元素`);
        return false;
    }
    const li = span.closest('li');
    if (!li) {
        console.warn(`未找到注册号 ${regForSelect} 对应的 li`);
        return false;
    }
    const checkbox = li.querySelector('input[type="checkbox"]');
    if (!checkbox) {
        console.warn(`未找到注册号 ${regForSelect} 的复选框`);
        return false;
    }
    checkbox.click();
    console.log('已勾选飞机复选框');
    await sleep(300);
    
    let closeBtn = doc.evaluate('//*[@id="close7"]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!closeBtn) {
        closeBtn = doc.evaluate('//button[contains(text(), "关闭")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (!closeBtn) {
        closeBtn = doc.evaluate('//button[contains(text(), "确定")]', doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    }
    if (closeBtn) {
        closeBtn.click();
        console.log('已关闭选择对话框');
        await sleep(500);
        return true;
    } else {
        console.warn('未找到关闭按钮，尝试按 ESC 关闭');
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        await sleep(500);
        return false;
    }
}

async function processRecord(record) {
    console.log(`\\n开始处理：${record.reg} - ${record.dep_city} -> ${record.arr_city}`);

    if (!(await ensureListPage())) {
        console.error('无法返回列表页，终止流程');
        return false;
    }

    const addBtn = await waitForElement(SELECTORS.addBtnCSS);
    if (!addBtn) {
        console.error('未找到添加按钮，终止流程');
        return false;
    }
    addBtn.click();
    console.log('已点击添加按钮，等待表单加载...');

    const aircraftSelectBtn = await waitForElement(SELECTORS.aircraftSelect, 15000, true);
    if (!aircraftSelectBtn) {
        console.error('未找到飞机机号选择按钮，终止流程');
        return false;
    }
    console.log('表单加载完成，找到飞机机号选择按钮');

    aircraftSelectBtn.click();
    if (!(await selectAircraft(record.reg))) {
        console.error('选择飞机失败，终止流程');
        return false;
    }

    const doc = await getCurrentDoc();
    const specialSelect = doc.querySelector(SELECTORS.specialSelect);
    if (specialSelect) await setSelectValue(specialSelect, "否");
    else console.warn('未找到是否特殊任务飞行 select');

    const certSelect = doc.querySelector(SELECTORS.certSelect);
    if (certSelect) await setSelectValue(certSelect, "是");
    else console.warn('未找到是否有运行合格证 select');

    const operateSelect = doc.querySelector(SELECTORS.operateSelect);
    if (operateSelect) await setSelectValue(operateSelect, "否");
    else console.warn('未找到是否经营性作业 select');

    // 用途下拉框
    const purposeSelect = await waitForElement(SELECTORS.purposeSelect, 10000, true);
    if (purposeSelect) await setSelectValue(purposeSelect, record.purpose);
    else console.warn('未找到用途下拉框');

    const startDateInput = await waitForElement(SELECTORS.startDate, 5000, true);
    const endDateInput = await waitForElement(SELECTORS.endDate, 5000, true);
    if (startDateInput) setDateInput(startDateInput, record.start_date);
    else console.warn('未找到服务开始日期输入框');
    if (endDateInput) setDateInput(endDateInput, record.end_date);
    else console.warn('未找到服务结束日期输入框');

    await fillFirstSegmentSelects(record.dep_city);
    await fillFirstSegmentTime(record);

    const addSegmentBtn = await waitForElement(SELECTORS.addSegmentBtn, 5000, true);
    if (addSegmentBtn) {
        addSegmentBtn.click();
        console.log('已点击添加航段按钮，等待新航段加载...');
        await sleep(1000);
        await fillSecondSegmentSelects(record.arr_city);
        await fillSecondSegmentTime();
    } else {
        console.warn('未找到添加航段按钮');
    }

    const detailAreaInput = await waitForElement(SELECTORS.detailArea, 5000, true);
    if (detailAreaInput) {
        detailAreaInput.value = `${record.dep_city}-${record.arr_city}`;
        detailAreaInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入详细作业地区');
    } else console.warn('未找到详细作业地区输入框');

    const customerInput = await waitForElement(SELECTORS.customer, 5000, true);
    if (customerInput) {
        customerInput.value = "天成商务航空有限公司";
        customerInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入服务客户名称');
    } else console.warn('未找到服务客户名称输入框');

    const baseInput = await waitForElement(SELECTORS.base, 5000, true);
    if (baseInput) {
        baseInput.value = `${record.dep_city}机场-${record.arr_city}机场`;
        baseInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入作业基地名称');
    } else console.warn('未找到作业基地名称输入框');

    const operatorInput = await waitForElement(SELECTORS.operator, 5000, true);
    if (operatorInput) {
        operatorInput.value = "张永一";
        operatorInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入作业负责人姓名');
    } else console.warn('未找到作业负责人姓名输入框');

    const phoneInput = await waitForElement(SELECTORS.phone, 5000, true);
    if (phoneInput) {
        phoneInput.value = "18566725728";
        phoneInput.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('已填入负责人联系电话');
    } else console.warn('未找到负责人联系电话输入框');

    const contractSelect = await waitForElement(SELECTORS.contractSelect, 5000, true);
    if (contractSelect) await setSelectValue(contractSelect, "已签订");
    else console.warn('未找到合同订立情况下拉框');

    const insuranceSelect = await waitForElement(SELECTORS.insuranceSelect, 5000, true);
    if (insuranceSelect) await setSelectValue(insuranceSelect, "已参保");
    else console.warn('未找到保险情况下拉框');

    const submitBtn = await waitForElement(SELECTORS.submitBtn, 5000, true);
    if (submitBtn) {
        submitBtn.click();
        console.log('已提交，等待弹窗...');
        let confirmBtn = null;
        for (let attempt = 0; attempt < 8; attempt++) {
            confirmBtn = await waitForDialogConfirmButton(2000);
            if (confirmBtn) break;
            console.log(`等待确定按钮... 第${attempt+1}次尝试`);
        }
        if (confirmBtn) {
            confirmBtn.click();
            console.log('已点击确定按钮');
        } else {
            console.warn('未找到确定按钮，请手动点击');
        }
        console.log('等待返回列表页...');
        await waitForElement(SELECTORS.addBtnCSS, 15000);
        console.log(`处理完成：${record.reg}`);
    } else {
        console.warn('未找到提交按钮');
    }
    await sleep(2000);
    return true;
}

// ==================== 执行 ====================
(async () => {
    const flightRecords = __FLIGHT_RECORDS__;
    for (let i = 0; i < flightRecords.length; i++) {
        const success = await processRecord(flightRecords[i]);
        if (!success) {
            console.error(`第 ${i+1} 条处理失败，终止后续执行。`);
            break;
        }
    }
    console.log("所有计划处理完毕");
})();
"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = len(json.loads(flight_records_json))
    final_script = template.replace("__DATETIME__", now)
    final_script = final_script.replace("__COUNT__", str(count))
    final_script = final_script.replace("__CITY_MAP__", city_map_json)
    final_script = final_script.replace("__CITY_DETAIL_MAP__", city_detail_map_json)
    final_script = final_script.replace("__DOMESTIC_KEYWORDS__", json.dumps(DOMESTIC_KEYWORDS))
    final_script = final_script.replace("__FLIGHT_RECORDS__", flight_records_json)
    return final_script

# ---------- Streamlit UI ----------
st.set_page_config(page_title="飞行计划自动填报代码生成器", layout="wide")
st.title("✈️ 飞行计划自动填报代码生成器")
st.markdown("上传 Excel 文件，自动生成可直接在浏览器控制台运行的 JavaScript 代码（**智能识别所有境内城市省份，自动匹配区县，无需手动补充映射**）")

st.sidebar.header("文件读取配置")
header_row = st.sidebar.number_input("标题行行号（从0开始）", min_value=0, max_value=10, value=1, step=1,
                                     help="Excel 中实际列名所在的行索引（第一行为0）。通常您的文件第二行是列名，因此输入 1。")

uploaded_file = st.file_uploader("📂 上传 Excel 文件（航段数据）", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=header_row)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        st.success("文件上传成功！")
        st.subheader("📊 数据预览（前5行）")
        st.dataframe(df.head())

        required_cols = ["飞机注册号", "出发日期", "到达日期", "用途", "出发城市", "到达城市", "预计飞行时间"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ 缺少必要列: {missing}")
            st.info(f"实际列名: {list(df.columns)}")
        else:
            st.info(f"✅ 共读取 {len(df)} 条飞行计划")

            if st.button("🚀 生成 JavaScript 脚本"):
                with st.spinner("正在构建城市映射并生成脚本..."):
                    custom_detail_map = {}
                    city_map, detail_map = build_city_mappings(df, custom_detail_map)
                    city_map_json = json.dumps(city_map, ensure_ascii=False, indent=4)
                    detail_map_json = json.dumps(detail_map, ensure_ascii=False, indent=4)
                    flight_records_json = generate_flight_records(df)
                    st.subheader("🔍 城市映射预览（前10个）")
                    preview_map = {k: v for k, v in list(city_map.items())[:10]}
                    st.json(preview_map)
                    final_script = generate_js_script(flight_records_json, city_map_json, detail_map_json)
                    st.success("脚本生成成功！")
                    st.subheader("📋 复制以下代码到浏览器控制台（F12）运行")
                    st.code(final_script, language="javascript")
                    st.info("💡 提示：请确保已登录系统并停留在「经营活动信息管理」列表页")
    except Exception as e:
        st.error(f"处理文件时出错: {e}")
else:
    st.info("请上传 Excel 文件开始")

st.markdown("---")
st.caption("本工具内置完整中国城市-省份映射表，自动识别境内城市省份，并从城市名中提取关键词作为区县名，无需手动补充映射。")
