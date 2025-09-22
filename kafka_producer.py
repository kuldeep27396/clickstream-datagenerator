import asyncio
import json
from typing import Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from kafka.admin import KafkaAdminClient, NewTopic
import logging
from models import User, Product, Interaction, Session
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaProducerManager:
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.admin_client: Optional[KafkaAdminClient] = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topics = {
            'users': settings.kafka_topic_users,
            'products': settings.kafka_topic_products,
            'interactions': settings.kafka_topic_interactions,
            'sessions': settings.kafka_topic_sessions
        }

    async def start(self):
        try:
            # Railway Kafka configuration
            security_protocol = os.getenv('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT')
            sasl_mechanism = os.getenv('KAFKA_SASL_MECHANISM', None)
            sasl_username = os.getenv('KAFKA_SASL_USERNAME', None)
            sasl_password = os.getenv('KAFKA_SASL_PASSWORD', None)

            config = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
                'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
                'acks': 'all',
                'retries': 3,
                'max_in_flight_requests_per_connection': 5,
                'request_timeout_ms': 30000,
                'retry_backoff_ms': 100,
                'compression_type': 'gzip',
                'batch_size': 16384,
                'linger_ms': 5,
                'buffer_memory': 33554432,
                'max_block_ms': 60000
            }

            # Add security configuration for Railway
            if security_protocol and security_protocol != 'PLAINTEXT':
                config.update({
                    'security_protocol': security_protocol,
                    'sasl_mechanism': sasl_mechanism,
                    'sasl_plain_username': sasl_username,
                    'sasl_plain_password': sasl_password,
                })

            self.producer = KafkaProducer(**config)

            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='clickstream-generator-admin'
            )

            await self._create_topics()
            logger.info("Kafka producer and admin client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    async def stop(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()
            self.producer = None

        if self.admin_client:
            self.admin_client.close()
            self.admin_client = None

        logger.info("Kafka producer stopped")

    async def _create_topics(self):
        try:
            existing_topics = self.admin_client.list_topics()
            topic_names = set(existing_topics.keys())

            topics_to_create = []
            for topic_key, topic_name in self.topics.items():
                if topic_name not in topic_names:
                    topics_to_create.append(
                        NewTopic(
                            name=topic_name,
                            num_partitions=3,
                            replication_factor=1
                        )
                    )

            if topics_to_create:
                self.admin_client.create_topics(topics_to_create)
                logger.info(f"Created topics: {[t.name for t in topics_to_create]}")
            else:
                logger.info("All required topics already exist")

        except Exception as e:
            logger.error(f"Failed to create topics: {e}")
            raise

    async def send_user(self, user: User):
        try:
            future = self.producer.send(
                self.topics['users'],
                key=user.user_id,
                value=user.dict()
            )
            future.get(timeout=10)
            logger.debug(f"Sent user {user.user_id} to Kafka")
        except Exception as e:
            logger.error(f"Failed to send user {user.user_id}: {e}")
            raise

    async def send_product(self, product: Product):
        try:
            future = self.producer.send(
                self.topics['products'],
                key=product.product_id,
                value=product.dict()
            )
            future.get(timeout=10)
            logger.debug(f"Sent product {product.product_id} to Kafka")
        except Exception as e:
            logger.error(f"Failed to send product {product.product_id}: {e}")
            raise

    async def send_interaction(self, interaction: Interaction):
        try:
            future = self.producer.send(
                self.topics['interactions'],
                key=interaction.interaction_id,
                value=interaction.dict()
            )
            future.get(timeout=10)
            logger.debug(f"Sent interaction {interaction.interaction_id} to Kafka")
        except Exception as e:
            logger.error(f"Failed to send interaction {interaction.interaction_id}: {e}")
            raise

    async def send_session(self, session: Session):
        try:
            future = self.producer.send(
                self.topics['sessions'],
                key=session.session_id,
                value=session.dict()
            )
            future.get(timeout=10)
            logger.debug(f"Sent session {session.session_id} to Kafka")
        except Exception as e:
            logger.error(f"Failed to send session {session.session_id}: {e}")
            raise

    async def send_batch(self, data_type: str, data_list: list):
        if data_type not in self.topics:
            raise ValueError(f"Invalid data type: {data_type}")

        topic = self.topics[data_type]
        futures = []

        for data in data_list:
            try:
                if data_type == 'users':
                    key = data.user_id
                    value = data.dict()
                elif data_type == 'products':
                    key = data.product_id
                    value = data.dict()
                elif data_type == 'interactions':
                    key = data.interaction_id
                    value = data.dict()
                elif data_type == 'sessions':
                    key = data.session_id
                    value = data.dict()
                else:
                    continue

                future = self.producer.send(topic, key=key, value=value)
                futures.append(future)

            except Exception as e:
                logger.error(f"Failed to prepare {data_type} data: {e}")
                continue

        if futures:
            for future in futures:
                try:
                    future.get(timeout=10)
                except Exception as e:
                    logger.error(f"Failed to send batch item: {e}")

            logger.info(f"Sent batch of {len(futures)} {data_type} to Kafka")

    async def is_connected(self) -> bool:
        if not self.producer:
            return False

        try:
            metadata = self.producer.metrics()
            return bool(metadata)
        except Exception:
            return False

    def get_producer_stats(self) -> dict:
        if not self.producer:
            return {}

        try:
            metrics = self.producer.metrics()
            return {
                'metrics_available': bool(metrics),
                'bootstrap_servers': self.bootstrap_servers,
                'topics_configured': list(self.topics.values())
            }
        except Exception as e:
            return {'error': str(e)}

kafka_producer_manager = KafkaProducerManager()