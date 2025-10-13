import cantools
import datetime

import cantools
import datetime

# 載入 Tesla DBC
db = cantools.database.load_file("Model3CAN.dbc")

# 定義要解析的訊號
signals_of_interest = [
    "SOCave292", "SOCmax292", "SOCmin292", "SOCUI292",  # BMS SOC 相關 (ID 658 - 0x292)
    "ChargeLinePower264", "ChargeLineVoltage264", "ChargeLineCurrent264",  # 充電資訊 (ID 612 - 0x264)
    "PCS_hvChargeStatus",        # 充電狀態 (ID 516 - 0x204)
    "BMS_maxDischargePower", "BMS_maxRegenPower"  # BMS 功率 (ID 594 - 0x252)
]

# TXT 檔案路径
txt_file = "model3_big.txt"

print("=== 開始解析 TXT 檔案 ===")
print(f"檔案: {txt_file}")
print(f"目標訊號: {signals_of_interest}")
print()

# 存儲解析後的數據
parsed_data = []

def parse_hex_line(hex_string):
    """
    解析十六進制字符串，嘗試提取 CAN ID 和數據
    假設格式可能是: [timestamp][can_id][data] 或其他格式
    """
    hex_string = hex_string.strip()
    if len(hex_string) < 6:  # 最少需要 CAN ID (3 bytes) 
        return None, None
    
    # 嘗試不同的解析方式
    # 方式1: 假設前3個字符是 CAN ID，其餘是數據
    if len(hex_string) >= 6:
        try:
            can_id = int(hex_string[:3], 16)
            data_hex = hex_string[3:]
            if len(data_hex) % 2 == 0 and len(data_hex) <= 16:  # 最多8字節數據
                data = bytes.fromhex(data_hex)
                return can_id, data
        except ValueError:
            pass
    
    # 方式2: 假設前4個字符是 CAN ID
    if len(hex_string) >= 8:
        try:
            can_id = int(hex_string[:4], 16)  
            data_hex = hex_string[4:]
            if len(data_hex) % 2 == 0 and len(data_hex) <= 16:
                data = bytes.fromhex(data_hex)
                return can_id, data
        except ValueError:
            pass
    
    return None, None

try:
    with open(txt_file, "r", encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # 跳過空行和註釋
                continue
                
            can_id, data = parse_hex_line(line)
            if can_id is None or data is None:
                continue
                
            try:
                # 用 DBC 解碼
                msg = db.get_message_by_frame_id(can_id)
                decoded = msg.decode(data)
                
                # 篩選我們要的訊號
                filtered = {sig: decoded.get(sig) for sig in signals_of_interest if sig in decoded}
                
                if filtered:
                    parsed_data.append({
                        'line_num': line_num,
                        'can_id': hex(can_id),
                        'message_name': msg.name,
                        'signals': filtered
                    })
                    print(f"Line {line_num}: CAN ID {hex(can_id)} - {filtered}")
                    
            except (KeyError, Exception) as e:
                # 跳過無法解碼的訊息
                continue
            line = line.strip()
            
            # 跳過空行、註釋行和標頭行
            if not line or line.startswith("//") or line.startswith("date") or line.startswith("base"):
                continue
            
            # 跳過 internal events logged 等標頭
            if "internal events" in line or "version" in line:
                continue
            
            try:
                # ASC 格式: timestamp channel ID direction type dlc data_bytes
                # 例如: 0.01007 1  154             Rx   d 8 00 32 10 00 00 00 E0 77
                parts = line.split()
                
                if len(parts) < 8:  # 至少需要 timestamp, channel, ID, Rx, d, dlc, data...
                    continue
                
                # 解析各部分
                timestamp = float(parts[0])
                channel = parts[1]
                can_id_hex = parts[2]
                direction = parts[3]  # Rx 或 Tx
                msg_type = parts[4]   # 'd' for data frame
                dlc = int(parts[5])   # data length code
                
                # 只處理接收到的數據幀
                if direction != "Rx" or msg_type != "d":
                    continue
                
                # 解析 CAN ID
                can_id = int(can_id_hex, 16)
                
                # 提取數據字節 (從第6個元素開始)
                data_hex_parts = parts[6:6+dlc]
                if len(data_hex_parts) != dlc:
                    continue
                
                # 組合數據字節
                data_hex_str = "".join(data_hex_parts)
                data = bytes.fromhex(data_hex_str)
                
                # 用 DBC 解碼
                try:
                    msg = db.get_message_by_frame_id(can_id)
                    decoded = msg.decode(data)
                    
                    # 篩選我們要的訊號
                    filtered = {sig: decoded.get(sig) for sig in signals_of_interest if sig in decoded}
                    
                    # 只處理包含我們關心訊號的訊息
                    if filtered:
                        parsed_data.append({
                            'timestamp': timestamp,
                            'can_id': hex(can_id),
                            'message_name': msg.name,
                            'signals': filtered
                        })
                        print(f"{timestamp:.3f}s: {filtered}")
                
                except (KeyError, Exception):
                    # 跳過無法解碼的訊息
                    continue
                    
            except (ValueError, IndexError) as e:
                # 跳過解析錯誤的行
                continue

except FileNotFoundError:
    print(f"找不到檔案: {txt_file}")
    print("請確認檔案名稱是否正確")
except Exception as e:
    print(f"讀取檔案時發生錯誤: {e}")

# 顯示統計資訊
if parsed_data:
    print(f"\n=== 解析統計 ===")
    print(f"成功解析的訊息數量: {len(parsed_data)}")
    
    # 行數範圍
    start_line = parsed_data[0]['line_num']
    end_line = parsed_data[-1]['line_num']
    
    print(f"行數範圍: {start_line} - {end_line}")
    
    # SOCave292 變化分析
    soc_ave_data = []
    for entry in parsed_data:
        if 'SOCave292' in entry['signals']:
            soc_ave_data.append({
                'line_num': entry['line_num'],
                'soc_value': entry['signals']['SOCave292']
            })
    
    if soc_ave_data:
        print(f"\n=== SOCave292 變化分析 ===")
        start_soc = soc_ave_data[0]['soc_value']
        end_soc = soc_ave_data[-1]['soc_value']
        soc_change = end_soc - start_soc
        
        print(f"起始 SOCave292 (行 {soc_ave_data[0]['line_num']}): {start_soc:.2f}%")
        print(f"結束 SOCave292 (行 {soc_ave_data[-1]['line_num']}): {end_soc:.2f}%")
        print(f"SOC 變化: {soc_change:+.2f}%")
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
