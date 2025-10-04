import cantools

# 讀取你的 DBC
dbc_file = "Model3CAN.dbc"
db = cantools.database.load_file(dbc_file)

# 定義充電相關關鍵字
charge_keywords = ["SOC", "Charge", "Battery", "Charging"]

found = False

for msg in db.messages:
    for sig in msg.signals:
        for keyword in charge_keywords:
            if keyword.lower() in sig.name.lower():
                print(f"Message: {msg.name} ({hex(msg.frame_id)}), Signal: {sig.name}")
                found = True

if not found:
    print("DBC 中沒有找到明顯的充電相關訊號")
