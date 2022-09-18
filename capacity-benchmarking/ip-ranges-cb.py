import os

import boto3

PROFILE = os.environ.get("PROFILE")
REGION = os.environ.get("REGION")
ec2 = boto3.Session(region_name=REGION, profile_name=PROFILE).resource("ec2")

subnets = ec2.subnets.all()
subnet_details = dict()

for subnet in list(subnets):
    free_ips = subnet.available_ip_address_count
    n = int(subnet.cidr_block.split("/")[1])
    cidr_ips = 2 ** (32 - n)
    used_ips = cidr_ips - free_ips
    subnet_details[subnet.id] = {
        "az": subnet.meta.data["AvailabilityZone"],
        "total_ips": cidr_ips,
        "aws_used": 5,
        "used_ips": used_ips,
        "free_ips": free_ips,
    }

sorted_by_used_ips = sorted(
    subnet_details, key=lambda x: (subnet_details[x]["used_ips"]), reverse=True
)
for id in sorted_by_used_ips:
    print(f"{id}: {subnet_details[id]}")
