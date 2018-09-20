import data
from slackclient import SlackClient


class Slack(object):
    """
    Creates a Slack Client with the SLACK_API_KEY configuration from database
    """

    def __init__(self):
        slack_api_key = data.get_configuration('SLACK_API_KEY')
        self.slack_client = None
        if slack_api_key:
            self.slack_client = SlackClient(slack_api_key)

    def check_error(self, response):
        """
        Check if the slack response is having any error.
        If the error is missing scope return information about missing scopes,
        else return the actual error
        """
        error = response.get('error')
        if (error == 'missing_scope'):
            return "Missing Scopes " + response.get('needed')

        if error:
            return error

        return None
