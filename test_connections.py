import os
import sys
import time

import psycopg2
import redis
from dotenv import load_dotenv


load_dotenv(override=True)


def exit_with(message: str, code: int) -> None:
    print(message)
    sys.exit(code)


def get_env_or_default() -> tuple[str, str]:
    db_url = "postgresql://postgres:postgres@localhost:5433/testdb"
    redis_url = "redis://127.0.0.1:6379/0"
    return db_url, redis_url


def test_postgres_connection(database_url: str) -> None:
    print(f"Testing Postgres: {database_url}")
    # Retry a few times to allow container startup
    last_err: Exception | None = None
    for attempt in range(1, 3):
        try:
            conn = psycopg2.connect(database_url)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                cur.execute("SELECT 1;")
                one = cur.fetchone()[0]
            conn.close()
            print(f"Postgres OK: version={version}, select1={one}")
            return
        except Exception as e:
            last_err = e
            print(f"Postgres attempt {attempt}/10 failed: {e}")
            time.sleep(1.5)
    raise RuntimeError(f"Postgres connection failed after retries: {last_err}")


def test_redis_connection(redis_url: str) -> None:
    print(f"Testing Redis: {redis_url}")
    client = redis.from_url(redis_url, decode_responses=True)
    # Retry a few times
    last_err: Exception | None = None
    for attempt in range(1, 11):
        try:
            pong = client.ping()
            client.set("vpb:test:key", "ok", ex=30)
            val = client.get("vpb:test:key")
            print(f"Redis OK: ping={pong}, test_key={val}")
            return
        except Exception as e:
            last_err = e
            print(f"Redis attempt {attempt}/10 failed: {e}")
            time.sleep(1.0)
    raise RuntimeError(f"Redis connection failed after retries: {last_err}")


def main() -> None:
    db_url, redis_url = get_env_or_default()
    try:
        test_postgres_connection(db_url)
    except Exception as e:
        exit_with(f"Postgres test FAILED: {e}", 2)
    try:
        test_redis_connection(redis_url)
    except Exception as e:
        exit_with(f"Redis test FAILED: {e}", 3)
    print("All connection tests PASSED")


if __name__ == "__main__":
    main()
