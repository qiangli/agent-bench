from app.models import load_orders, total

orders = load_orders()
print("orders=%d total=%.2f" % (len(orders), total(orders)))
