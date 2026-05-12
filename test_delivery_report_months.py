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

async def test_delivery_report_for_month(selected_month):
    print(f"Testing delivery report for month: {selected_month}")
    deliveries_ref = await asyncio.to_thread(db.reference(f'deliveries/{selected_month}').get)

    # Also get completed orders for this month
    orders_ref = await asyncio.to_thread(db.reference('orders').get)
    completed_orders = []
    if orders_ref:
        for o_id, o in orders_ref.items():
            if isinstance(o, dict):
                order_month = o.get('month', '')
                order_status = o.get('status', '')
                if order_month == selected_month and order_status in ["Biz yetkazib berdik", "Mijozni o'zi olib ketdi"]:
                    completed_orders.append((o_id, o))

    # Combine deliveries and completed orders
    all_deliveries = []

    # Add deliveries from deliveries table
    if deliveries_ref:
        if isinstance(deliveries_ref, dict):
            for d_id, d in deliveries_ref.items():
                if isinstance(d, dict):
                    all_deliveries.append(('delivery', d_id, d))
        elif isinstance(deliveries_ref, list):
            for i, d in enumerate(deliveries_ref):
                if d is not None and isinstance(d, dict):
                    all_deliveries.append(('delivery', i, d))

    # Add completed orders that don't have delivery records
    for o_id, o in completed_orders:
        # Check if this order already has a delivery record
        has_delivery = False
        for delivery_type, d_id, d in all_deliveries:
            if delivery_type == 'delivery' and d.get('order_id') == o_id:
                has_delivery = True
                break

        if not has_delivery:
            # Create a pseudo-delivery record from the order
            pseudo_delivery = {
                'order_id': o_id,
                'client': o.get('client_name', 'Noma\'lum'),
                'product_id': o.get('product_id', 'Noma\'lum'),
                'amount': o.get('amount', '1'),
                'driver': o.get('driver', 'O\'zi olib ketdi'),
                'price': o.get('delivery_price', '0') if o.get('status') == "Biz yetkazib berdik" else o.get('pickup_discount', '0'),
                'timestamp': o.get('created_at', 'Noma\'lum')
            }
            all_deliveries.append(('order', o_id, pseudo_delivery))

    if not all_deliveries:
        print(f"{selected_month} oyida hech qanday yetkazib berishlar topilmadi.")
        return

    # Sort by timestamp (most recent first)
    def get_timestamp(item):
        delivery_type, d_id, d = item
        timestamp_str = d.get('timestamp', 'Noma\'lum')
        try:
            if timestamp_str != 'Noma\'lum':
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.min
        except:
            return datetime.min

    all_deliveries.sort(key=get_timestamp, reverse=True)

    report_header = f"📊 **{selected_month} oyi uchun yetkazib berish hisoboti:**\n\n"
    report_items = []

    total_count = 0
    total_items = 0
    total_sum_uzs = 0
    total_sum_usd = 0

    import re
    for delivery_type, d_id, d in all_deliveries:
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

        # Buyurtma sanasini olish
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

        # Stats
        total_count += 1
        total_items += amount_int

        # Parse price for totals
        nums = re.findall(r'\d+', price.replace(" ", ""))
        if nums:
            val = int(nums[0])
            if '$' in price:
                total_sum_usd += val
            else:
                total_sum_uzs += val

    # Summary
    summary = f"\n📈 **JAMI STATISTIKA ({selected_month}):**\n"
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

    for part in full_report:
        print(part)

# Test different months
async def main():
    months_to_test = ['2026-05', '2026-04', '2026-03', '2025-12']
    for month in months_to_test:
        await test_delivery_report_for_month(month)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())