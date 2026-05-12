import asyncio
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app'
})

async def test_delivery_report():
    current_month = datetime.now().strftime("%Y-%m")
    deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{current_month}').get)
    
    if not deliveries_ref:
        print(f"Ushbu oy ({current_month}) uchun yetkazib berishlar topilmadi.")
        return
        
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    
    if isinstance(deliveries_ref, dict):
        items = list(deliveries_ref.items())
    elif isinstance(deliveries_ref, list):
        items = [(i, v) for i, v in enumerate(deliveries_ref) if v is not None]
    else:
        items = []

    items.reverse()
    
    report_header = f"📊 **{current_month} oyi uchun yetkazib berish hisoboti:**\n\n"
    report_items = []
    
    total_count = 0
    total_items = 0
    total_sum_uzs = 0
    total_sum_usd = 0
    
    import re
    for d_id, d in items:
        if isinstance(d, dict):
            order_id = d.get('order_id', "Noma'lum")
            client = d.get('client', "Noma'lum")
            product = d.get('product_id', "Noma'lum")
            driver = d.get('driver', "Noma'lum")
            delivery_date = d.get('timestamp', "Noma'lum")
            price = str(d.get('price', '0'))
            amount = d.get('amount', '1')
            
            try:
                amount_int = int(amount)
            except:
                amount_int = 1
            
            order_date = "Noma'lum"
            if orders_ref and isinstance(orders_ref, dict) and order_id in orders_ref:
                order_date = orders_ref[order_id].get('created_at', "Noma'lum")
            
            item_text = f"🆔 ID: `{order_id}`\n"
            item_text += f"🧑 Mijoz: {client}\n"
            item_text += f"📦 Mebel: {product} ({amount} ta)\n"
            item_text += f"📅 Buyurtma: {order_date}\n"
            item_text += f"🚚 Yetkazilgan: {delivery_date}\n"
            item_text += f"👨‍✈️ Haydovchi: {driver} ({price})\n"
            item_text += "------------------------"
            report_items.append(item_text)
            
            total_count += 1
            total_items += amount_int
            
            nums = re.findall(r'\d+', price.replace(" ", ""))
            if nums:
                val = int(nums[0])
                if '$' in price:
                    total_sum_usd += val
                else:
                    total_sum_uzs += val
    
    summary = f"\n📈 **JAMI STATISTIKA ({current_month}):**\n"
    summary += f"✅ Yetkazib berishlar: {total_count} ta\n"
    summary += f"📦 Jami mebellar: {total_items} ta\n"
    
    sums = []
    if total_sum_usd > 0:
        sums.append(f"{total_sum_usd}$")
    if total_sum_uzs > 0:
        sums.append(f"{total_sum_uzs:,} so'm".replace(",", " "))
    if sums:
        summary += f"💰 Jami tushum: {' + '.join(sums)}"
    else:
        summary += "💰 Jami tushum: 0"
    
    full_report = [report_header] + report_items + [summary]
    
    current_msg = ""
    for part in full_report:
        if len(current_msg) + len(part) > 3900:
            print(current_msg)
            current_msg = part + "\n\n"
        else:
            current_msg += part + "\n\n"
    
    if current_msg:
        print(current_msg)

asyncio.run(test_delivery_report())
