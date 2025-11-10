import os
from redis import Redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

load_dotenv()

listen = ["default"]
redis_url = os.getenv("REDIS_URL")

if not redis_url:
    raise ValueError("REDIS_URL não configurada no .env")

conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    print("🚀 Worker iniciado, aguardando tarefas...")
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work(with_scheduler=True)
