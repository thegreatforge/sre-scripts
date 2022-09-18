import os
from datetime import date, timedelta

import boto3
import yaml

from parsers import postgres
from pkg import chart, rds, slack

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH) as c:
    config = yaml.safe_load(c)

fetch_date_obj = date.today() - timedelta(days = 1)
fetch_date = fetch_date_obj.strftime('%Y-%m-%d')

session = boto3.Session(region_name=config["aws"]["region"], profile_name=config["aws"]["profile"])
rds_client = rds.new_rds_client(session)
slack_client = slack.new_slack_client(config["slack"]["token"])


instance_engine_dict = rds_client.get_instance_engine_dict(config["rds"])
for identifier, engine in instance_engine_dict.items():
    local_log_files = []    
    rds_log_file_names = rds_client.get_log_file_names(identifier, fetch_date)
    
    for rds_log_file_name in rds_log_file_names:
        local_log_file_path = f"{config['datadir']}/{identifier}/{fetch_date}/{rds_log_file_name}"

        if os.path.exists(local_log_file_path):
            print(f"{local_log_file_path} already exists")
            local_log_files.append(local_log_file_path)
            continue
        if not os.path.exists(os.path.dirname(local_log_file_path)):
            os.makedirs(os.path.dirname(local_log_file_path))

        if rds_client.download_log_file(rds_log_file_name, identifier, local_log_file_path, config["aws"]["region"]):
            local_log_files.append(local_log_file_path)
        else:
            print(f"failed to download log file {rds_log_file_name} of {identifier}") 
    
    duration_bucket = {
        "30ms": 0, "40ms": 0, "50ms": 0, "100ms": 0
    }
    
    for local_log_file in local_log_files:
        with open(local_log_file) as fp:
            for line in fp:
                if engine == "postgres" or engine == "aurora-postgresql":
                    pdata = postgres.parse_log_line(fetch_date, line)
                if pdata != None:
                    d = pdata.get_duration()
                    if d > 100.00:
                        duration_bucket["100ms"] += 1
                    elif d > 50.00:
                        duration_bucket["50ms"] += 1
                    elif d > 40.00:
                        duration_bucket["40ms"] += 1
                    elif d > 30.00:
                        duration_bucket["30ms"] += 1
                    else:
                        pass
    print(f"{identifier} buckets -  {duration_bucket}")

    chart_output_image = f"{config['datadir']}/{identifier}/{fetch_date}/chart.png"
    chart.plot_bar_chart(
        title=f"{identifier} queries analysis",
        yaxis_label="queries count",
        xaxis_label="queries duration",
        yaxis=duration_bucket.values(),
        xaxis=[ f"> {k}" for k in duration_bucket.keys()],
        colors=["teal", "orange", "brown", "red"],
        output_file=chart_output_image
    )

    message = f"[[ *{identifier}* ]] *{fetch_date}* queries analysis:\n"\
                f"*queries taken time more than 100ms: {duration_bucket['100ms']}*\n"\
                f"*queries taken time more than 50ms:  {duration_bucket['50ms']}*\n"\
                f"queries taken time more than 40ms:   {duration_bucket['40ms']}\n"\
                f"queries taken time more than 30ms:   {duration_bucket['30ms']}\n"
    if slack_client.publish_image_with_message(config["slack"]["channel_id"], message, chart_output_image):
        print(f"successfully sent slack message for {identifier} to {config['slack']['channel_id']}")
    else:
        print(f"failed to send slack message for {identifier} to {config['slack']['channel_id']}")
