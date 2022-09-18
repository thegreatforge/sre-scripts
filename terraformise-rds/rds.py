import csv
import logging
import os
import subprocess
from math import fabs

import boto3

from upgrade_terraform import (do_tf013_init, do_tf013_plan, do_tf013_refresh,
                               do_tf13_upgrade, do_tf_fmt,
                               do_tf_init_reconfigure,
                               replace_existing_provider_tf)

logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO
)


REGION = os.environ.get("REGION")
AWS_PROFILE = os.environ.get("AWS_PROFILE")
RDS_CLIENT = boto3.Session(region_name=REGION, profile_name=AWS_PROFILE).client("rds")
REPORTS_DIR = "./reports"


def _get_rds_instances():
    return RDS_CLIENT.describe_db_instances()["DBInstances"]


def _make_terraformer_rds_import_command(**kwargs):
    db_instances_filter = f" --filter db_instance={kwargs['db_instances']}"
    db_parameter_group_filter = f" --filter db_parameter_group={kwargs['db_parameter_groups']}"
    db_subnet_group_filter = " --filter db_subnet_group=exclude"
    db_option_group_filter = f" --filter db_option_group={kwargs['db_option_group']}"
    path_pattern = f" --path-output rds --path-pattern {kwargs['path_pattern']}"
    return f"/usr/local/bin/terraformer import aws --resources=rds {db_instances_filter} {db_parameter_group_filter}"\
        f"{db_subnet_group_filter} {db_option_group_filter} --filter db_event_subscription=exclude {path_pattern}"\
        f" --regions={REGION} --profile={AWS_PROFILE}"


def _create_pg_rds_csv():
    csv_file = csv.writer(open(f"{REPORTS_DIR}/{AWS_PROFILE}-{REGION}.pg-rds.csv", "w"))
    pgroup_rds_dict = dict()
    for rds in _get_rds_instances():
        if rds["Engine"] == "mysql" or rds["Engine"] == "postgres":
            pgroup = rds["DBParameterGroups"][0]["DBParameterGroupName"]
            pgroup_rds_dict[pgroup] = pgroup_rds_dict.get(pgroup, [])
            pgroup_rds_dict[pgroup].append(rds["DBInstanceIdentifier"])

    for pg in pgroup_rds_dict.keys():
        csv_file.writerow([pg, len(pgroup_rds_dict[pg]), ": ".join(pgroup_rds_dict[pg])])
    logging.info("Successfully created the csv file")


def group_rds_resources():
    rds_resources_group = dict()
    for rds in _get_rds_instances():
        if rds["Engine"] == "mysql" or rds["Engine"] == "postgres":
            pgroup = rds["DBParameterGroups"][0]["DBParameterGroupName"]
            ogroup = rds["OptionGroupMemberships"][0]["OptionGroupName"]
            if rds.get('ReadReplicaSourceDBInstanceIdentifier'):
                # replica
                if rds_resources_group.get(rds["ReadReplicaSourceDBInstanceIdentifier"]):
                    replicas = rds_resources_group[rds["ReadReplicaSourceDBInstanceIdentifier"]]["replicas"]
                    pgs = rds_resources_group[rds["ReadReplicaSourceDBInstanceIdentifier"]].get("pgs", [])
                    ogs = rds_resources_group[rds["ReadReplicaSourceDBInstanceIdentifier"]].get("ogs", [])
                    pgs.append(pgroup) if pgroup not in pgs else None
                    ogs.append(ogroup) if ogroup not in ogs else None
                    rds_resources_group[rds["ReadReplicaSourceDBInstanceIdentifier"]] = {
                        "replicas": replicas,
                        "pgs": pgs,
                        "ogs": ogs
                    }
                else:
                    rds_resources_group[rds["ReadReplicaSourceDBInstanceIdentifier"]] = {
                        "replicas": [rds["DBInstanceIdentifier"]],
                        "pgs": [pgroup],
                        "ogs": [ogroup]
                    }
            else:
                # primary
                if rds_resources_group.get(rds["DBInstanceIdentifier"]):
                    pgs = rds_resources_group[rds["DBInstanceIdentifier"]].get("pgs", [])
                    ogs = rds_resources_group[rds["DBInstanceIdentifier"]].get("ogs", [])
                    pgs.append(pgroup) if pgroup not in pgs else None
                    ogs.append(ogroup) if ogroup not in ogs else None
                    rds_resources_group[rds["DBInstanceIdentifier"]] = {
                        "replicas": rds["ReadReplicaDBInstanceIdentifiers"],
                        "pgs": pgs,
                        "ogs": ogs
                    }
                else:
                    rds_resources_group[rds["DBInstanceIdentifier"]] = {
                        "replicas": rds["ReadReplicaDBInstanceIdentifiers"],
                        "pgs": [pgroup],
                        "ogs": [ogroup]
                    }
    return rds_resources_group


def _create_rds_with_replica_pgs_csv():
    csv_file = csv.writer(open(f"{REPORTS_DIR}/{AWS_PROFILE}_{REGION}_rds_with_replicas_pgs.csv", "w"))
    csv_file.writerow(["Primary", "Replicas", "Parameter Groups", "Option Groups"])
    rds_resources_group = group_rds_resources()
    for r in rds_resources_group.keys():
        csv_file.writerow([
            r,
            ":".join(rds_resources_group[r]["replicas"]),
            ":".join(rds_resources_group[r]["pgs"]),
            ":".join(rds_resources_group[r]["ogs"])
        ])


def _add_text_in_tf(tf_filepath, resource_type, text):
    with open(tf_filepath, "r") as rtf, open(f"{tf_filepath}-new", "w") as wtf:
        for line in rtf:
            wtf.write(line)
            if f"resource \"{resource_type}\"" in line:
                logging.info(f"adding {text} in {tf_filepath}")
                wtf.write(text+"\n")
    os.remove(tf_filepath)
    os.rename(f"{tf_filepath}-new", tf_filepath)


def _remove_text_from_tf(tf_filepath, text):
    with open(tf_filepath, "r") as rtf, open(f"{tf_filepath}-new", "w") as wtf:
        for line in rtf:
            without_space_line = line.replace(" ", "")
            without_space_text = text.replace(" ", "")
            if without_space_line.startswith(without_space_text):
                logging.info(f"removing line {line} from {tf_filepath}")
                continue
            wtf.write(line)
    os.remove(tf_filepath)
    os.rename(f"{tf_filepath}-new", tf_filepath)


def _fix_replica_tf(tf_filepath):
    replicate_optional_lines = []
    is_replica = False
    with open(tf_filepath, "r") as rtf, open(f"{tf_filepath}-new", "w") as wtf:
        for line in rtf:
            if "resource \"aws_db_instance\"" in line:
                replicate_optional_lines = []
                is_replica = False

            without_space_line = line.replace(" ", "")
            if without_space_line.startswith("replicate_source_db="):
                is_replica = True

            if without_space_line.startswith("engine=") or without_space_line.startswith("engine_version=") or without_space_line.startswith("username=") or without_space_line.startswith("db_name="):
                replicate_optional_lines.append(line)
            elif is_replica and without_space_line.startswith("vpc_security_group_ids="):
                wtf.write(line)
                replicate_optional_lines = []
            elif not is_replica and without_space_line.startswith("vpc_security_group_ids="):
                wtf.write(line)
                for op_line in replicate_optional_lines:
                    wtf.write(op_line)
            else:
                wtf.write(line)
    os.remove(tf_filepath)
    os.rename(f"{tf_filepath}-new", tf_filepath)


def generate_terraform():
    rds_resources_group = group_rds_resources()
    for r, v in rds_resources_group.items():
        db_instances = ":".join(v["replicas"])+f":{r}" if len(v["replicas"]) else r
        db_parameter_groups = ":".join(v["pgs"])
        filtered_ogs = list(filter(lambda og: "default" not in og, v["ogs"]))
        db_option_group = ":".join(filtered_ogs) if len(filtered_ogs) else "exclude"
        path_pattern = f"rds/{AWS_PROFILE}/{REGION}/{r}"
        terraformer_command = _make_terraformer_rds_import_command(
            db_instances=db_instances,
            db_parameter_groups=db_parameter_groups,
            db_option_group=db_option_group,
            path_pattern=path_pattern
        )
        logging.info(f"Executing {terraformer_command}")
        exit_code = subprocess.call(terraformer_command, shell=True)
        if exit_code:
            logging.error(f"Failed with exit code {exit_code}")
            break
        _fix_replica_tf(f"{path_pattern}/db_instance.tf")
        _add_text_in_tf(f"{path_pattern}/db_instance.tf", "aws_db_instance", "apply_immediately = false")
        _remove_text_from_tf(f"{path_pattern}/db_instance.tf", "name=")
        do_tf13_upgrade(path_pattern)
        do_tf_fmt(path_pattern)
        do_tf013_init(path_pattern)
        do_tf013_plan(path_pattern)
        do_tf013_refresh(path_pattern)
        replace_existing_provider_tf(f"{path_pattern}/provider.tf", tf_s3_backend={
            "bucket": "stage-mybuket" if AWS_PROFILE == "stage" else "prod-mybucket",
            "key": f"{path_pattern}-tfstate",
            "region": "ap-southeast-1"
        })
        do_tf_init_reconfigure(path_pattern)
        os.remove(f"{path_pattern}/terraform.tfstate")
        os.remove(f"{path_pattern}/terraform.tfstate.backup")
        os.remove(f"{path_pattern}/variables.tf")
        os.remove(f"{path_pattern}/versions.tf")
        do_tf_init_reconfigure(path_pattern)
        os.remove(f"{path_pattern}/provider.tf-backup")


def generate_atlantis_config():
    rds_resources_group = group_rds_resources()
    for k in rds_resources_group.keys():
        print(f"- name: rds-prod-{REGION}-{k}")
        print(f"  dir: rds/prod/{REGION}/{k}")
        print("  workspace: default")
        print("  terraform_version: v1.1.3")
        print("  workflow: prod-flow")


def create_reports():
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
    _create_pg_rds_csv()
    _create_rds_with_replica_pgs_csv()


if __name__ == "__main__":
    create_reports()
    generate_terraform()
    generate_atlantis_config()
