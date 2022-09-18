from __future__ import print_function

import csv
import datetime
import os

import boto3
import six
from dateutil.tz import tzutc

REGION = os.environ.get("REGION")
PROFILE = os.environ.get("PROFILE")
ROOT_PROFILE = os.environ.get("ROOT_PROFILE")

rds_client = boto3.Session(region_name=REGION, profile_name=PROFILE).client("rds")
ri_rds_client = boto3.Session(region_name=REGION, profile_name=ROOT_PROFILE).client("rds")
instances = rds_client.describe_db_instances()["DBInstances"]


def normalized_engine(name):
    engine = {}
    engine["postgres"] = "postgresql"
    return engine.get(name, name)


def instance_header():
    return "\t(%s)\t%12s\t%s\t%s" % ("Count", "Engine", "Instance", "Multi-AZ")


running_instances = {}
instance_class_type_factor_dict = {
    "nano": 0.25,
    "micro": 0.5,
    "small": 1,
    "medium": 2,
    "large": 4,
    "xlarge": 8,
    "2xlarge": 16,
    "4xlarge": 32,
    "8xlarge": 64,
    "10xlarge": 80,
    "16xlarge": 128,
    "32xlarge": 256,
}
for i in instances:
    if i["DBInstanceStatus"] != "available":
        continue
    if not i["AvailabilityZone"].startswith(REGION):
        continue
    # import ipdb; ipdb.set_trace()
    a_zone = REGION
    db_engine = normalized_engine(i["Engine"])
    db_instance_class = i["DBInstanceClass"]
    db_multi_az = i["MultiAZ"]

    multi_az_factor = 1.0
    if db_multi_az:
        multi_az_factor = 2.0
        db_multi_az = False

    splitted_db_instance_class = db_instance_class.split(".")
    if splitted_db_instance_class[1] == "serverless":
        continue
    db_instance_class_factor = (
        instance_class_type_factor_dict[splitted_db_instance_class[2]] / 4.0
    )
    splitted_db_instance_class[2] = "large"
    normalized_db_instance_class = ".".join(splitted_db_instance_class)

    key = (db_engine, normalized_db_instance_class, a_zone, db_multi_az)
    running_instances[key] = running_instances.get(key, 0.0) + (
        multi_az_factor * db_instance_class_factor
    )

reserved_instances = {}
soon_expire_ri = {}

reserved_rds_instances = ri_rds_client.describe_reserved_db_instances()
reservations = reserved_rds_instances["ReservedDBInstances"]  # noqa
now = datetime.datetime.utcnow().replace(tzinfo=tzutc())
for ri in reservations:
    if ri["State"] == "retired":
        continue
    ri_id = ri["ReservedDBInstanceId"]
    ri_type = ri["DBInstanceClass"]
    ri_count = ri["DBInstanceCount"]
    ri_engine = ri["ProductDescription"]
    ri_multiaz = ri["MultiAZ"]
    if ri_multiaz:
        ri_multiaz = False
        ri_count = ri_count * 2.0
    key = (ri_engine, ri_type, REGION, ri_multiaz)
    reserved_instances[key] = reserved_instances.get(key, 0.0) + ri_count
    ri_start_time = ri["StartTime"]
    expire_time = ri_start_time + datetime.timedelta(seconds=ri["Duration"])
    if (expire_time - now) < datetime.timedelta(days=15):
        soon_expire_ri[ri_id] = (ri_type, ri_engine, REGION, expire_time)

diff = dict(
    [
        (x, reserved_instances[x] - running_instances.get(x, 0.0))
        for x in reserved_instances
    ]
)

for pkey in running_instances:
    if pkey not in reserved_instances:
        diff[pkey] = -running_instances[pkey]

unused_ri = {}
unreserved_instances = {}
for k, v in six.iteritems(diff):
    if v > 0:
        unused_ri[k] = v
    elif v < 0:
        unreserved_instances[k] = -v

# Report
print("Reserved RDS instances:")
print(instance_header())
for k, v in sorted(six.iteritems(reserved_instances), key=lambda x: x[0]):
    print("\t(%s)\t%12s\t%s\t%s" % (v, k[0], k[1], k[3]))
if not reserved_instances:
    print("\tNone")
print("")

print("Unused reserved RDS instances:")
print(instance_header())
for k, v in sorted(six.iteritems(unused_ri), key=lambda x: x[0]):
    print("\t(%s)\t%12s\t%s\t%s" % (v, k[0], k[1], k[3]))
if not unused_ri:
    print("\tNone")
print("")

print("Expiring soon (less than %sd) reserved RDS instances:" % 15)
for k, v in sorted(six.iteritems(soon_expire_ri), key=lambda x: x[1][:2]):
    print("\t%s\t%12s\t%s\t%s\t%s" % (k, v[0], v[1], v[2], v[3].strftime("%Y-%m-%d")))
if not soon_expire_ri:
    print("\tNone")
print("")


print("On-demand RDS instances, which haven't got a reserved RDS instance:")
print(instance_header())
for k, v in sorted(six.iteritems(unreserved_instances), key=lambda x: x[0]):
    print("\t(%s)\t%12s\t%s\t%s" % (v, k[0], k[1], k[3]))
if not unreserved_instances:
    print("\tNone")
print("")


print("Total Running RDS instances:")
print(instance_header())
for k, v in sorted(six.iteritems(running_instances), key=lambda x: x[0]):
    print("\t(%s)\t%12s\t%s\t%s" % (v, k[0], k[1], k[3]))
if not running_instances:
    print("\tNone")
print("")

print("Running on-demand RDS instances: %s" % sum(running_instances.values()))
print("Reserved RDS instances:          %s" % sum(reserved_instances.values()))
print("")

csv_file = csv.writer(open(f"{REGION}-rds-list.csv", "w"))
csv_file.writerow(
    [
        "Name",
        "Status",
        "Engine",
        "Version",
        "MultiAZ",
        "Class",
        "ClassType"
    ]
)
for rds in instances:
    csv_file.writerow(
        [
            rds["DBInstanceIdentifier"],
            rds["DBInstanceStatus"],
            rds["Engine"],
            rds["EngineVersion"],
            rds["MultiAZ"],
            rds["DBInstanceClass"],
            rds["DBInstanceClass"].split(".")[1],
        ]
    )
