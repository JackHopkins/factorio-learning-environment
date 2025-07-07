# Remote Factorio Cluster

This directory contains infrastructure-as-code and management scripts for deploying and managing a scalable Factorio server cluster on AWS using ECS Fargate.

## Architecture Overview

The system deploys a fully managed Factorio server cluster with the following components:

- ECS Fargate cluster for running Factorio servers
- EFS for shared scenario storage
- VPC with public subnets across two availability zones
- Route53 DNS management for server discovery
- AWS EventBridge for container lifecycle management
- Step Functions for DNS record management

**NOTE:** EFS syncing from S3 is still manual. You need to setup Datasync to ensure that your scenario / config data (in an S3 bucket) is loaded into the game servers.

## Files

- `cluster.cloudformation.yaml` - CloudFormation template defining the AWS infrastructure
- `cluster_ips.py` - Utility for retrieving public IPs of running Factorio containers
- `factorio_server_login.py` - Script for automated server initialization

## Infrastructure Components

### Networking
- VPC with CIDR block 10.0.0.0/16
- Two public subnets across different availability zones
- Internet Gateway for public access
- Security groups for Factorio and EFS traffic

### Compute
- ECS Fargate cluster
- Task Definition:
  - 1 vCPU, 2GB memory
  - Factorio container image from public ECR
  - EFS mount for scenarios
  - UDP port 34197 for game traffic
  - TCP port 27015 for RCON

### Storage
- EFS filesystem for shared scenario storage
- EFS access points with appropriate permissions
- Mount targets in both availability zones

### DNS Management
- Automated Route53 record management
- State machine for DNS updates
- Event-driven updates based on container lifecycle

## Setup and Usage

### Prerequisites
1. AWS CLI configured with appropriate credentials
2. Python 3.x with required packages:
   - boto3
   - pyautogui
   - dotenv

### Deployment

1. Deploy the CloudFormation stack:
```bash
aws cloudformation deploy \
  --template-file cluster.cloudformation.yaml \
  --stack-name factorio-cluster \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND
```

2. Create a `.env` file with:
```
CLUSTER_NAME=FactorioCluster
```

### Server Management

To get IPs of running servers:
```bash
python cluster_ips.py
```

To initialize all servers:
```bash
python factorio_server_login.py
```

## Configuration Parameters

The CloudFormation template accepts the following parameters:

- `VpcCIDR`: VPC CIDR block (default: 10.0.0.0/16)
- `PublicSubnet1CIDR`: First public subnet CIDR (default: 10.0.1.0/24)
- `PublicSubnet2CIDR`: Second public subnet CIDR (default: 10.0.2.0/24)
- `FactorioServerCount`: Number of server instances (default: 8)
- `FactorioHostedZoneName`: Route53 hosted zone name
- `FactorioHostedZoneID`: Route53 hosted zone ID

## Security

The infrastructure includes:
- IAM roles with least privilege access
- Security groups limiting inbound traffic to required ports
- VPC with public subnets for server access
- EFS access limited to Factorio containers

## Advanced Features

### Container Access
To SSH into a running container:
```bash
aws ecs execute-command --task <task-id> --cluster FactorioCluster --interactive --command /bin/bash
```

### Data Migration
Use AWS DataSync to move scenario files from S3 to EFS:
```
s3://factorio-scenarios → EFS filesystem
```

## Monitoring and Logging

- CloudWatch Logs for container output
- State Machine execution logs
- ECS task status events
- Route53 DNS update tracking

## Troubleshooting

1. Check ECS task status:
```bash
aws ecs list-tasks --cluster FactorioCluster
```

2. View container logs:
```bash
aws logs get-log-events --log-group factorio-ecs
```

3. Verify DNS records:
```bash
aws route53 list-resource-record-sets --hosted-zone-id <zone-id>
```

4. Use `factorio_server_login.py` to login to each of the remote servers automatically. For initialization issues, check screen coordinates to ensure they map to your own resolution.