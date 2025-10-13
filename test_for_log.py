import cantools

# 載入 Tesla DBC
db = cantools.database.load_file("Model3CAN.dbc")

# 定義要解析的訊號 - 使用 DBC 中實際存在且在 log 中有資料的訊號名稱
signals_of_interest = [
    "SOCave292", "SOCmax292", "SOCmin292", "SOCUI292",  # BMS SOC 相關 (ID 658 - 0x292)
    "ChargeLinePower264", "ChargeLineVoltage264", "ChargeLineCurrent264",  # 充電資訊 (ID 612 - 0x264)
    "PCS_hvChargeStatus",        # 充電狀態 (ID 516 - 0x204)
    "BMS_maxDischargePower", "BMS_maxRegenPower"  # BMS 功率 (ID 594 - 0x252)
]

log_file = "ColdBattCharge.csv"

for msg in db.messages:
    print(hex(msg.frame_id), msg.name)


with open(log_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            # 解析 timestamp、interface、arbitration_id#data
            timestamp_part, iface, msg_part = line.split()
            
            # 移除括號取得 float timestamp
            timestamp = float(timestamp_part.strip("()"))
            
            # 分離 arbitration_id 與 data bytes
            arb_str, data_str = msg_part.split("#")
            arbitration_id = int(arb_str, 16)
            data = bytes.fromhex(data_str)
            
        except ValueError:
            continue

        # 用 DBC 解碼
        try:
            msg = db.get_message_by_frame_id(arbitration_id)
            decoded = msg.decode(data)
        except (KeyError, Exception):
            continue  # log 中可能有 DBC 沒定義的訊息或資料長度不符

        # 篩選我們要的訊號
        filtered = {sig: decoded.get(sig) for sig in signals_of_interest if sig in decoded}

        # 只輸出包含我們關心訊號的訊息
        if filtered:
            print(f"{timestamp}: {filtered}")
