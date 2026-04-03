"""
Plain-text receipt generator. Avoids heavyweight PDF dependency in the prototype.
Production would use WeasyPrint + HTML template for branded PDF receipts.
"""
from datetime import datetime


def generate_receipt(order: dict) -> str:
    lines = [
        "=" * 48,
        "      NORTHSTAR OUTFITTERS",
        f"      Store: {order['store_id']}",
        "=" * 48,
        f"  Order #: {order['id']}",
        f"  Date   : {order.get('paid_at', datetime.utcnow().isoformat())}",
        f"  Cashier: {order['cashier_id']}",
        "-" * 48,
        f"  {'Item':<28} {'Qty':>4} {'Total':>10}",
        "-" * 48,
    ]
    for item in order.get("items", []):
        lines.append(
            f"  {item['product_name'][:28]:<28} {item['quantity']:>4} {float(item['line_total']):>10.2f}"
        )
    lines += [
        "-" * 48,
        f"  {'Subtotal':<34} {float(order['subtotal']):>10.2f}",
        f"  {'Tax':<34} {float(order['tax_amount']):>10.2f}",
        f"  {'TOTAL':<34} {float(order['total']):>10.2f}",
        "=" * 48,
        f"  Payment: {order.get('payment_method', 'N/A').upper()}",
        "=" * 48,
        "     Thank you for shopping with us!",
        "",
    ]
    return "\n".join(lines)
