import json
import os
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Optional Kafka import for cases where Kafka is not available
try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: Kafka is not available. Execution service will run in mock mode.")

class KafkaService:
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.producer = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.kafka_available = KAFKA_AVAILABLE
    
    def _get_producer(self):
        """Kafkaプロデューサーを取得（遅延初期化）"""
        if not self.kafka_available:
            print("Kafka is not available, producer request ignored")
            return None
            
        if self.producer is None:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
        return self.producer
    
    async def send_message(self, topic: str, message: Dict[str, Any], key: str = None):
        """Kafkaにメッセージを送信"""
        if not self.kafka_available:
            print(f"Mock Kafka send: topic={topic}, message={message}, key={key}")
            return
            
        def _send():
            producer = self._get_producer()
            if producer:
                future = producer.send(topic, value=message, key=key)
                producer.flush()
                return future.get(timeout=10)
        
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(self.executor, _send)
        except Exception as e:
            print(f"Failed to send message to Kafka: {e}")
            raise
    
    def create_consumer(self, topics: list, group_id: str = None):
        """Kafkaコンシューマーを作成"""
        if not self.kafka_available:
            print(f"Mock Kafka consumer created for topics: {topics}, group_id: {group_id}")
            return None
            
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest'
        )
    
    async def consume_messages(self, topics: list, message_handler, group_id: str = None):
        """Kafkaからメッセージを継続的に消費"""
        if not self.kafka_available:
            print(f"Mock Kafka consume for topics: {topics}, group_id: {group_id}")
            return
            
        def _consume():
            consumer = self.create_consumer(topics, group_id)
            if consumer:
                try:
                    for message in consumer:
                        asyncio.create_task(message_handler(message))
                finally:
                    consumer.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _consume)
    
    def close(self):
        """リソースをクリーンアップ"""
        if self.kafka_available and self.producer:
            self.producer.close()
        self.executor.shutdown(wait=True)