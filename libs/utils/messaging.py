
import pika
import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MessageQueue:
    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = os.getenv("RABBITMQ_USER", "admin")
        self.password = os.getenv("RABBITMQ_PASSWORD", "secret")
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queues
            self.channel.queue_declare(queue='document_processing', durable=True)
            self.channel.queue_declare(queue='classification_results', durable=True)
            self.channel.queue_declare(queue='routing_decisions', durable=True)
            self.channel.queue_declare(queue='notifications', durable=True)
            self.channel.queue_declare(queue='web_scraping', durable=True)
            
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def publish_message(self, queue: str, message: Dict[Any, Any]):
        """Publish a message to a queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
                
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            logger.info(f"Published message to queue {queue}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise
    
    def consume_messages(self, queue: str, callback):
        """Consume messages from a queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
                
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=callback,
                auto_ack=True
            )
            logger.info(f"Started consuming from queue {queue}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise
    
    def close(self):
        """Close connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Global message queue instance
mq = MessageQueue()
