from slack_sdk.web import WebClient


def new_slack_client(token):
    return Slack(WebClient(token))


class Slack:
    def __init__(self, client):
        self.client = client

    def publish_image_with_message(self, channel_id, message, image_path):
        try:
            image = self.client.files_upload(
                channels = channel_id,
                initial_comment = message,
                file = image_path
            )
        except Exception as e:
            print(e)
            return False
        return True
