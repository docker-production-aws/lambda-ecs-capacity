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

# Returns fully paginated response
def paginated_response(func, result_key, next_token=None):
  args=dict()
  if next_token:
    args['NextToken'] = next_token
  response = func(**args)
  result = response.get(result_key)
  next_token = response.get('NextToken')
  if not next_token:
    return result
  return result + self.paginated_response(func, result_key, next_token)
  
def describe_ecs_instances(cluster):
  func = partial(ecs.list_container_instances, cluster=cluster)
  ecs_instance_arns = paginated_response(func, 'containerInstanceArns')
  ecs_instances = ecs.describe_container_instances(
      cluster=cluster,
      containerInstances=ecs_instance_arns
    )['containerInstances']
  return [instance for instance in ecs_instances if instance['status'] == 'ACTIVE']

# Get current CPU and memory
def check_cpu(instance):
  return sum(
    resource['integerValue']
    for resource in instance['remainingResources']
    if resource['name'] == 'CPU')

def check_memory(instance):
  return sum(
    resource['integerValue']
    for resource in instance['remainingResources']
    if resource['name'] == 'MEMORY')

# Get current network port usage
def check_tcp_port(ecs_instances, port):
  return len([
    port
    for instance in ecs_instances
    for resource in instance['remainingResources']
    if resource['name'] == 'PORTS' and port in resource.get('stringSetValue',[])
  ])

def check_udp_port(ecs_instances, port):
  return len([
    port
    for instance in ecs_instances
    for resource in instance['remainingResources']
    if resource['name'] == 'PORTS_UDP' and port in resource.get('stringSetValue',[])
  ])

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

  # STEP 1 - COLLECT RESOURCE DATA
  ecs_cluster = event['detail']['clusterArn']
  # The maximum CPU availble for an idle ECS instance
  ecs_instance_max_cpu = next(
    resource['integerValue']
    for resource in event['detail']['registeredResources']
    if resource['name'] == 'CPU')
  # The maximum memory availble for an idle ECS instance
  ecs_instance_max_memory = next(
    resource['integerValue']
    for resource in event['detail']['registeredResources']
    if resource['name'] == 'MEMORY')

  # Get current container capacity based upon CPU and memory
  ecs_instances = describe_ecs_instances(ecs_cluster)
  cpu_capacity = 0
  memory_capacity = 0
  for instance in ecs_instances:
    cpu_capacity += check_cpu(instance)/CONTAINER_MAX_CPU
    memory_capacity += check_memory(instance)/CONTAINER_MAX_MEMORY
  log.info("Current container cpu capacity of %s" % cpu_capacity)
  log.info("Current container memory capacity of %s" % memory_capacity)

  # Get current container capacity based upon static TCP and UDP ports
  tcp_port_capacity = [len(ecs_instances)]
  udp_port_capacity = [len(ecs_instances)]
  for port in TCP_PORT_RESOURCES:
    tcp_port_capacity.append(len(ecs_instances) - check_tcp_port(ecs_instances, port))
  for port in UDP_PORT_RESOURCES:
    udp_port_capacity.append(len(ecs_instances) - check_udp_port(ecs_instances, port))
  log.info("Current container tcp port capacity of %s" % min(tcp_port_capacity))
  log.info("Current container udp port capacity of %s" % min(udp_port_capacity))

  # STEP 2 - CALCULATE OVERALL CONTAINER CAPACITY
  # This is the minimum container capacity count (integer) for CPU, memory and TCP/UDP port resources
  # This metric is used to scale out and typically is triggered with capacity < 1
  container_capacity = min(
    cpu_capacity,
    memory_capacity,
    min(tcp_port_capacity),
    min(udp_port_capacity)
  )
  log.info("Overall container capacity of %s" % container_capacity)

  # STEP 3 - CALCULATE IDLE HOST COUNT
  # This is the minimum idle host count (float) for CPU, memory and TCP/UDP port resources
  # This metric is used to scale in and typically is triggered with idle host count > 1.0
  idle_hosts = min(
    float(cpu_capacity) / float(ecs_instance_max_cpu / CONTAINER_MAX_CPU),
    float(memory_capacity) / float(ecs_instance_max_memory / CONTAINER_MAX_MEMORY),
    float(min(tcp_port_capacity)),
    float(min(udp_port_capacity))
  )
  log.info("Overall idle host capacity of %s" % idle_hosts)

  # STEP 4 - PUBLISH METRICS
  # Publish container capacity
  cloudwatch.put_metric_data(
    Namespace='AWS/ECS',
    MetricData=[{
      'MetricName': 'ContainerCapacity',
      'Dimensions': [{
        'Name': 'ClusterName',
        'Value': ecs_cluster.split('/')[-1]
      }],
      'Timestamp': datetime.datetime.utcnow(),
      'Value': container_capacity
    }])
  # Publish idle host capacity
  cloudwatch.put_metric_data(
    Namespace='AWS/ECS',
    MetricData=[{
      'MetricName': 'IdleHostCapacity',
      'Dimensions': [{
        'Name': 'ClusterName',
        'Value': ecs_cluster.split('/')[-1]
      }],
      'Timestamp': datetime.datetime.utcnow(),
      'Value': idle_hosts
    }])