import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from ml_model.preprocess import load_dataset
from database.db_connection import get_db_connection


def train_model():
    df = load_dataset()

    if df.empty:
        print("❌ No data available for ML training")
        return

    X = df[['cpu_usage', 'memory_usage', 'burst_time', 'priority']]
    y = df['waiting_time']

    X = X.apply(pd.to_numeric, errors='coerce')
    y = pd.to_numeric(y, errors='coerce')

    df = df.loc[~(X.isnull().any(axis=1) | y.isnull())]
    X = X.loc[df.index]
    y = y.loc[df.index]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        min_samples_leaf=3
    )

    model.fit(X, y)

    df['ml_waiting_time'] = model.predict(X)

    # ✅ SAVE USING PRIMARY KEY
    conn = get_db_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            UPDATE process_data
            SET ml_waiting_time = %s
            WHERE id = %s
        """, (float(row['ml_waiting_time']), int(row['id'])))

    conn.commit()
    cursor.close()
    conn.close()

    mae = mean_absolute_error(y, df['ml_waiting_time'])

    print("✅ ML Model Trained Successfully")
    print(f"📉 MAE: {mae:.4f}")
    print("💾 ML waiting time saved to MySQL")


if __name__ == "__main__":
    train_model()
