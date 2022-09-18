import logging
import os
import subprocess

from jinja2 import Template


def _quote_string(val):
    return f"\"{val}\""


def _render_provider_tf(rendered_filepath, **kwargs):
    pjinja = Template(open("templates/provider.jinja").read())
    with open(rendered_filepath, "w") as ptf:
        ptf.write(pjinja.render({
            "providers": kwargs["providers"],
            "terraform": kwargs["terraform"]
        }))


def replace_existing_provider_tf(provider_tf_path, tf_s3_backend=None):
    os.rename(provider_tf_path, f"{provider_tf_path}-backup")
    _render_provider_tf(
        rendered_filepath=provider_tf_path,
        providers={
            "aws": {
                "region": _quote_string(os.environ.get("REGION")),
                "source": _quote_string("hashicorp/aws"),
                "version": _quote_string("~> 4.5.0")
            }
        },
        terraform={
            "required_version": _quote_string("~> 1.1.3"),
            "backend": {
                "s3": {
                    "bucket": _quote_string(tf_s3_backend.get("bucket")),
                    "key": _quote_string(tf_s3_backend.get("key")),
                    "region": _quote_string(tf_s3_backend.get("region"))
                }
            }
        }
    )
    logging.info("Successfully generated new provider.tf")


def do_tf13_upgrade(tf_path):
    command = "terraform013 0.13upgrade -yes"
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)


def do_tf013_init(tf_path):
    command = "terraform013 init"
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)


def do_tf013_plan(tf_path):
    command = f"AWS_PROFILE={os.environ.get('AWS_PROFILE')} terraform013 plan"
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)


def do_tf013_refresh(tf_path):
    command = f"AWS_PROFILE={os.environ.get('AWS_PROFILE')} terraform013 refresh"
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)


def do_tf_fmt(tf_path):
    command = "terraform fmt",
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)


def do_tf_init_reconfigure(tf_path):
    command = f"AWS_PROFILE={os.environ.get('AWS_PROFILE')} terraform init -reconfigure"
    logging.info(f"Executing - {command} in {tf_path}")
    return subprocess.call(command, cwd=tf_path, shell=True)
