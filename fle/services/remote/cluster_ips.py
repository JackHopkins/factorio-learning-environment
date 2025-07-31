import os

import boto3
import sys

from dotenv import load_dotenv


def get_public_ips(cluster_name):
    ecs_client = boto3.client("ecs")
    ec2_client = boto3.client("ec2")

    # Get all running tasks in the cluster
    tasks = []
    paginator = ecs_client.get_paginator("list_tasks")
    for page in paginator.paginate(cluster=cluster_name, desiredStatus="RUNNING"):
        tasks.extend(page["taskArns"])

    if not tasks:
        print(f"No running tasks found in cluster {cluster_name}")
        return []

    public_ips = []
    # Process tasks in batches of 100
    for i in range(0, len(tasks), 100):
        batch = tasks[i : i + 100]

        # Describe the tasks to get their details
        task_details = ecs_client.describe_tasks(cluster=cluster_name, tasks=batch)

        for task in task_details["tasks"]:
            # Get the ENI ID for the task
            eni_id = None
            for attachment in task["attachments"]:
                for detail in attachment["details"]:
                    if detail["name"] == "networkInterfaceId":
                        eni_id = detail["value"]
                        break
                if eni_id:
                    break

            if not eni_id:
                print(f"Warning: No ENI found for task {task['taskArn']}")
                continue

            # Describe the network interface to get its public IP
            try:
                eni_details = ec2_client.describe_network_interfaces(
                    NetworkInterfaceIds=[eni_id]
                )
                if "Association" in eni_details["NetworkInterfaces"][0]:
                    public_ip = eni_details["NetworkInterfaces"][0]["Association"][
                        "PublicIp"
                    ]
                    public_ips.append(public_ip)
            except Exception as e:
                print(f"Error getting public IP for ENI {eni_id}: {str(e)}")

    return public_ips


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get cluster name from .env file or command line argument
    default_cluster_name = os.getenv("CLUSTER_NAME")

    if len(sys.argv) == 2:
        cluster_name = sys.argv[1]
    elif default_cluster_name:
        cluster_name = default_cluster_name
    else:
        print("Error: CLUSTER_NAME not set in .env file and not provided as argument")
        print("Usage: python cluster_ip.py [cluster_name]")
        sys.exit(1)

    public_ips = get_public_ips(cluster_name)
    if public_ips:
        print("Public IP addresses of running containers:")
        for ip in public_ips:
            print(ip)
    else:
        print("No public IP addresses found for running containers.")
