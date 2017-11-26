import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json
import boto3
from functools import partial

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(os.environ.get('LOG_LEVEL','INFO'))
def format_json(data):
  return json.dumps(data, default=lambda d: d.isoformat() if isinstance(d, datetime.datetime) else str(d))

# AWS clients
ecs = boto3.client('ecs')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
CONTAINER_MAX_MEMORY = int(os.environ.get('CONTAINER_MAX_MEMORY',993))
CONTAINER_MAX_CPU = int(os.environ.get('CONTAINER_MAX_CPU',1024))
TCP_PORT_RESOURCES = [p for p in os.environ.get('TCP_PORT_RESOURCES','').split(',') if p]
UDP_PORT_RESOURCES = [p for p in os.environ.get('UDP_PORT_RESOURCES','').split(',') if p]