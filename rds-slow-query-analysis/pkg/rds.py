import datetime
import hashlib
import hmac
import os
import urllib

import requests


def new_rds_client(boto_session):
    rds_client = boto_session.client("rds")
    print("successfully initialised rds client")
    return RDS(rds_client, boto_session)


class RDS:
    def __init__(self, rds_client, boto_session):
        self.rds_client = rds_client
        self.boto_session = boto_session
    
    def get_instance_engine_dict(self, rds_config):
        instances = self.rds_client.describe_db_instances()["DBInstances"]
        instance_engine_dict = {}
        for i in instances:
            if i["DBInstanceStatus"] != "available":
                continue

            if rds_config.get("enableFilter", None) != None:
                if i["DBInstanceIdentifier"] in rds_config["filter"]["identifier"]:
                    instance_engine_dict[i["DBInstanceIdentifier"]] = i["Engine"]
            else:
                    instance_engine_dict[i["DBInstanceIdentifier"]] = i["Engine"]
        return instance_engine_dict

    def get_log_file_names(self, db_instance_identifier, sub_string):
        selected_files = []
        files = self.rds_client.describe_db_log_files(DBInstanceIdentifier = db_instance_identifier)
        for file in files["DescribeDBLogFiles"]:
            file_name = file["LogFileName"]
            if not file_name.startswith("error/"):
                continue
            if sub_string is None:
                selected_files.append(file_name)
                continue
            if sub_string in file_name:
                selected_files.append(file_name)
        return selected_files

    def download_log_file(self, filename, db_instance_identifier, output_file, region):
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        # http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
        def getSignatureKey(key, dateStamp, regionName, serviceName):
            kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
            kRegion = sign(kDate, regionName)
            kService = sign(kRegion, serviceName)
            kSigning = sign(kService, 'aws4_request')
            return kSigning

        method = 'GET'
        service = 'rds'
        region = region
        host = 'rds.'+ region +'.amazonaws.com'
        endpoint = 'https://' + host

        # creating new session for every file download
        credentials = self.boto_session.get_credentials()
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        session_token = credentials.token
        if access_key is None or secret_key is None:
            print('No access key is available in current environment. Exiting ..')
            return False

        t = datetime.datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ') # Format date as YYYYMMDD'T'HHMMSS'Z'
        datestamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope

        # sample usage : '/v13/downloadCompleteLogFile/DBInstanceIdentifier/error/postgresql.log.2022-08-09-04'
        canonical_uri = '/v13/downloadCompleteLogFile/'+ db_instance_identifier + '/' + filename

        canonical_headers = 'host:' + host + '\n'
        signed_headers = 'host'

        # hashing algorithm in use, either SHA-1 or
        # SHA-256 (recommended)
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = datestamp + '/' + region + '/' + service + '/' + 'aws4_request'

        canonical_querystring = ''
        canonical_querystring += 'X-Amz-Algorithm=AWS4-HMAC-SHA256'
        canonical_querystring += '&X-Amz-Credential=' + urllib.parse.quote_plus(access_key + '/' + credential_scope)
        canonical_querystring += '&X-Amz-Date=' + amz_date
        canonical_querystring += '&X-Amz-Expires=30'
        if session_token is not None :
            canonical_querystring += '&X-Amz-Security-Token=' + urllib.parse.quote_plus(session_token)
        canonical_querystring += '&X-Amz-SignedHeaders=' + signed_headers

        payload_hash = hashlib.sha256(''.encode("utf-8")).hexdigest()

        canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash

        string_to_sign = algorithm + '\n' +  amz_date + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()

        signing_key = getSignatureKey(secret_key, datestamp, region, service)

        signature = hmac.new(signing_key, (string_to_sign).encode("utf-8"), hashlib.sha256).hexdigest()

        canonical_querystring += '&X-Amz-Signature=' + signature

        request_url = endpoint + canonical_uri + "?" + canonical_querystring

        print(f"initiating download of {db_instance_identifier} {filename} to {output_file}")
        r = requests.get(request_url, stream=True, allow_redirects=True)
        if r.status_code != 200:
            print(f"something went wrong, request status code {r.status_code}")
            return False

        error = False
        with open(output_file, "wb") as f:
            for chunk in r.iter_content(100000):
                if r.status_code !=200:
                    error = True
                    break
                if chunk:
                    f.write(chunk)
        if error:
            os.remove(output_file)
            print(f"failed to download file {output_file}, request status code {r.status_code}")
            return False
        print(f"successfully downloaded {db_instance_identifier} {filename} to {output_file}") 
        return True
