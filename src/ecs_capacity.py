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

# Handler
def handler(event, context):
  '''
  {
    "detail": {
      "status": "ACTIVE",
      "registeredAt": "2017-08-19T10:34:21.75Z",
      "remainingResources": [
        {"name": "CPU","type": "INTEGER","integerValue": 224},
        {"name": "MEMORY","type": "INTEGER","integerValue": 213},
        {
          "name": "PORTS",
          "type": "STRINGSET",
          "stringSetValue": ["22","8002","8000","8001","2376","2375","51678","15704","51679","15703","15702","15701"]
        },
        {"name": "PORTS_UDP","type": "STRINGSET","stringSetValue": []}
      ],
      "registeredResources": [
        {"name": "CPU","type": "INTEGER","integerValue": 1024},
        {"name": "MEMORY","type": "INTEGER","integerValue": 993},
        {"name": "PORTS","type": "STRINGSET","stringSetValue": ["22","2376","2375","51678","51679"]},
        {"name": "PORTS_UDP","type": "STRINGSET","stringSetValue": []}
      ],
      "clusterArn": "arn:aws:ecs:us-west-2:543279062384:cluster/microtrader-development-ApplicationCluster-C13GN9F65SNK",
    }
  }
  '''
  log.info("Received event: %s" % format_json(event))