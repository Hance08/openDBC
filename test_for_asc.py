import cantools
import datetime
import re

# 載入 Tesla DBC
db = cantools.database.load_file("Model3CAN.dbc")

# 定義要解析的訊號
signals_of_interest = [
    "SOCave292", "SOCmax292", "SOCmin292", "SOCUI292",  # BMS SOC 相關
    "ChargeLinePower264", "ChargeLineVoltage264", "ChargeLineCurrent264",  # 充電資訊
    "PCS_hvChargeStatus",        # 充電狀態
    "BMS_maxDischargePower", "BMS_maxRegenPower"  # BMS 功率
]

# ASC 檔案路徑
asc_file = "Model3Log2019-01-19superchargeend.asc"

print("=== 開始解析 ASC 檔案 ===")
print(f"目標訊號: {signals_of_interest}")
print()

# 存儲解析後的數據
parsed_data = []

# ASC 格式範例：
# 0.01007 1  154             Rx   d 8 00 32 10 00 00 00 E0 77
# timestamp channel can_id direction type length data_bytes

try:
    with open(asc_file, "r", encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # 跳過空行和註釋行
            if not line or line.startswith("date") or line.startswith("base") or line.startswith("internal") or line.startswith("//"):
                continue
            
            # 使用正則表達式解析 ASC 格式
            # 格式: timestamp channel can_id direction type length data_bytes
            match = re.match(r'^\s*(\d+\.\d+)\s+(\d+)\s+([A-Fa-f0-9]+)\s+(\w+)\s+(\w+)\s+(\d+)\s+([A-Fa-f0-9\s]+)', line)
            
            if not match:
                continue
                
            try:
                timestamp = float(match.group(1))
                channel = int(match.group(2))
                can_id_hex = match.group(3)
                direction = match.group(4)  # Rx or Tx
                msg_type = match.group(5)   # d (data frame)
                length = int(match.group(6))
                data_hex = match.group(7).replace(' ', '')  # 移除空格
                
                # 只處理接收的數據幀
                if direction != "Rx" or msg_type != "d":
                    continue
                
                # 解析 CAN ID
                can_id = int(can_id_hex, 16)
                
                # 解析數據
                if len(data_hex) % 2 != 0:
                    continue  # 資料長度必須是偶數
                
                data = bytes.fromhex(data_hex)
                
                # 驗證數據長度
                if len(data) != length:
                    continue
                
                # 用 DBC 解碼
                try:
                    msg = db.get_message_by_frame_id(can_id)
                    decoded = msg.decode(data)
                    
                    # 篩選我們要的訊號
                    filtered = {sig: decoded.get(sig) for sig in signals_of_interest if sig in decoded}
                    
                    # 只輸出包含我們關心訊號的訊息
                    if filtered:
                        parsed_data.append({
                            'timestamp': timestamp,
                            'can_id': hex(can_id),
                            'message_name': msg.name,
                            'signals': filtered
                        })
                        print(f"{timestamp:.3f}s: {filtered}")
                
                except (KeyError, Exception) as e:
                    # 跳過無法解碼的訊息
                    continue
            
            except (ValueError, Exception) as e:
                print(f"解析第 {line_num} 行時發生錯誤: {e}")
                continue

except FileNotFoundError:
    print(f"找不到檔案: {asc_file}")
except Exception as e:
    print(f"讀取檔案時發生錯誤: {e}")

# 顯示統計資訊
if parsed_data:
    print(f"\n=== 解析統計 ===")
    print(f"成功解析的訊息數量: {len(parsed_data)}")
    
    # 時間範圍
    start_time = parsed_data[0]['timestamp']
    end_time = parsed_data[-1]['timestamp']
    duration = end_time - start_time
    
    print(f"時間範圍: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")
    print(f"開始時間戳: {start_time:.3f}s")
    print(f"結束時間戳: {end_time:.3f}s")
    
    # SOCave292 變化分析
    soc_ave_data = []
    for entry in parsed_data:
        if 'SOCave292' in entry['signals']:
            soc_ave_data.append({
                'timestamp': entry['timestamp'],
                'soc_value': entry['signals']['SOCave292']
            })
    
    if soc_ave_data:
        print(f"\n=== SOCave292 變化分析 ===")
        start_soc = soc_ave_data[0]['soc_value']
        end_soc = soc_ave_data[-1]['soc_value']
        soc_change = end_soc - start_soc
        
        print(f"起始 SOCave292: {start_soc:.2f}%")
        print(f"結束 SOCave292: {end_soc:.2f}%")
        print(f"SOC 變化: {soc_change:+.2f}%")
        
        if duration > 0:
            soc_rate_per_hour = soc_change / (duration / 3600)
            print(f"變化率: {soc_rate_per_hour:+.3f}% per hour")
        
        print(f"SOCave292 資料點數量: {len(soc_ave_data)}")
    
    # 訊號統計
    signal_counts = {}
    for entry in parsed_data:
        for signal_name in entry['signals'].keys():
            signal_counts[signal_name] = signal_counts.get(signal_name, 0) + 1
    
    print(f"\n=== 訊號統計 ===")
    for signal_name, count in signal_counts.items():
        print(f"{signal_name}: {count} 個資料點")

else:
    print("沒有找到相符的訊號資料")
