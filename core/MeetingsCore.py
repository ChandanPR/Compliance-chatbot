import json

import data
from core.SlackAPIClient import Slack
from logsetup import configure_log

logger = configure_log(__name__)
slack = Slack()


class MeetingsCore(object):
    """
    Handles the creation of Meetings, Users, Corresponding Slack Channel
    """

    def create_meetings_from_file(self):
        meetings_file = open("./../meetings.json")
        meetings = json.load(meetings_file).get("meetings")
        meetings_file.close()
        for meeting in meetings:
            self.create_meeting(meeting)

    def create_meeting(self, meeting_data):
        # Verify if all input parameters are present for creating the meeting
        if not self.__verify_meeting_data__(meeting_data):
            logger.error("Missing Input Parameters!!!")
            return None

        # Update the Meeting Guests information
        meeting_guests = self.__add_guest_users__(meeting_data)

        # Log Error if any of the Meeting Guests information is not available
        if not meeting_guests:
            logger.error(
                "Could not create meeting " + meeting_data.get(
                    'title') + " as guest information could not be retrieved.")
            return None

        # Create Meeting
        meeting_data['meeting_guests'] = meeting_guests
        meeting = data.create_meeting(meeting_data)

        # Create Slack Channel for the meeting
        meeting = self.__create_slack_channel__(meeting, meeting_guests)

        return meeting

    def __verify_meeting_data__(self, meeting_data):
        valid = True
        if not meeting_data.get("title"):
            logger.error("Missing title")
            valid = False

        if not meeting_data.get("description"):
            logger.error("Missing description")
            valid = False

        #TODO: slack_channel_name validation - Apply validations for channel name
        if not meeting_data.get("slack_channel_name"):
            logger.error("Missing slack_channel_name")
            valid = False

        if not meeting_data.get("user_emails"):
            logger.error("Missing user_emails")
            valid = False

        if not meeting_data.get("start_date"):
            logger.error("Missing start_date")
            valid = False

        if not meeting_data.get("meeting_docs_parent_folder"):
            logger.error("Missing meeting_docs_parent_folder")
            valid = False

        return valid

    def __create_slack_channel__(self, meeting, meeting_guests):
        logger.info(
            "Creating Slack Channel " + meeting.slack_channel_name + " for the meeting " + meeting.title)
        channel = slack.slack_client.api_call(
            "conversations.create",
            name=meeting.slack_channel_name,
            is_private=True,
            user_ids=meeting_guests
        )

        error = slack.check_error(channel)
        if error:
            logger.error("Failed to create Channel " + meeting.slack_channel_name + ". Error " + str(error))
            return None

        meeting = data.update_meeting(meeting, channel.get('channel').get('id'))
        self.__update_channel_details__(meeting)
        return meeting

    def __add_guest_users__(self, meeting_data):
        meeting_guests = []
        user_emails = meeting_data.get('user_emails')
        for email in user_emails:
            user = self.__check_add_user__(email)
            if user:
                logger.info(
                    "User with email " + str(email) + " available.")
                meeting_guests.append(user.id)
            else:
                logger.error(
                    "User with email " + str(email) + " not available.")
                return None
        return meeting_guests

    def __update_channel_details__(self, meeting):
        purpose = slack.slack_client.api_call(
            "conversations.setPurpose",
            channel=meeting.slack_channel_id,
            purpose=meeting.description
        )
        error = slack.check_error(purpose)
        if error:
            logger.warning \
                ("Failed to Set Purpose to Channel " + meeting.slack_channel_name + ". Error " + str(error))
        topic = slack.slack_client.api_call(
            "conversations.setTopic",
            channel=meeting.slack_channel_id,
            topic=meeting.title
        )
        error = slack.check_error(topic)
        if error:
            logger.warning \
                ("Failed to Set Topic to Channel " + meeting.slack_channel_name + ". Error " + str(error))

    def __check_add_user__(self, email):
        user = data.find_user_by_email(email)
        if user:
            return user
        slack_user = slack.slack_client.api_call(
            "users.lookupByEmail",
            email=email
        )
        error = slack.check_error(slack_user)
        if error:
            logger.error("Unable to find user by email: " + str(email) + ". Error : " + error)
            return None

        slack_user_id = slack_user.get('user').get('id')
        slack_user_name = slack_user.get('user').get('name')
        slack_user_profile = slack_user.get('user').get('profile')
        first_name = slack_user_profile.get('first_name')
        last_name = slack_user_profile.get('last_name')
        if not first_name:
            first_name = slack_user_profile.get('real_name')

        user = data.create_user(email, first_name, last_name,
                                slack_user_name, slack_user_id)
        return user

# Create Meeting from meetings.json file
MeetingsCore().create_meetings_from_file()