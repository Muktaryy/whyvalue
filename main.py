import pandas as pd

import whyvalue as why


why.watch()

df = pd.DataFrame(
    {
        "name": ["Ali", "Ahmed", "Sara", "Amina"],
        "age": [25, None, 17, 30],
        "price": [100, 200, 300, 400],
        "quantity": [2, 3, 4, 5],
        "cost": [50, 100, 250, 500],
    }
)

df["age"] = df["age"].fillna(0)

df["revenue"] = df["price"] * df["quantity"]

df["profit"] = df["revenue"] - df["cost"]

df["average_price"] = df["revenue"] / df["quantity"]

df = df[df["age"] >= 18]

print("Final DataFrame:")
print(df)

print()
print("TRACE")
why.trace(df)

print()
print("EXPLAIN PROFIT")
why.explain(df, row=0, column="profit")

print()
print("EXPLAIN AVERAGE PRICE")
why.explain(df, row=0, column="average_price")

print()
print("EXPLAIN REMOVED ROW")
why.explain_removed(df, row=1)

why.stop()
