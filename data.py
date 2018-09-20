import datetime
import time
import uuid
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy import MetaData
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.sql.sqltypes import Boolean, Enum
from sqlalchemy.sql.sqltypes import DateTime, Time

import config

from logsetup import configure_log

logger = configure_log(__name__)

engine = create_engine(config.config.SQLALCHEMY_DATABASE_URI, echo=False)
metadata = MetaData(bind=engine)
session_maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(session_maker)
date_format = lambda d: datetime.datetime.strftime(d, "%y/%m/%d")

Base = declarative_base()
Base.query = db_session.query_property()

config_keys = ('SLACK_API_KEY', 'AWS_ACCESS_ID', 'AWS_ACCESS_KEY')
config_keys_enum = Enum(*config_keys, name="config_key")

meeting_recurrences = ('Daily', 'Weekly', 'Monthly')
meeting_recurrence_enum = Enum(*meeting_recurrences, name="meeting_recurrence")
extension_threshold_time = 15


class Configuration(Base):
    __tablename__ = "configuration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(config_keys_enum, unique=True, nullable=False)
    value = Column(String(255, convert_unicode=True), nullable=False)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String(255, convert_unicode=True), unique=True)
    email = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    first_name = Column(String(255, convert_unicode=True), nullable=False)
    last_name = Column(String(255, convert_unicode=True))
    slack_user_name = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    slack_user_id = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    creation_date = Column(DateTime(timezone=True), default=datetime.datetime.now)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    def __init__(self):
        self.guid = str(uuid.uuid1())
        pass


class Meeting(Base):
    __tablename__ = "meeting"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String(255, convert_unicode=True), unique=True)
    title = Column(String(250, convert_unicode=True), nullable=False)
    description = Column(String(250, convert_unicode=True))
    slack_channel_name = Column(String(22, convert_unicode=True), unique=True, nullable=False)
    creation_date = Column(DateTime(timezone=True), default=datetime.datetime.now)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))
    duration = Column(Integer, primary_key=True, default=30)
    is_active = Column(Boolean, default=True)
    meeting_recurrence = Column(meeting_recurrence_enum, nullable=False)
    slack_channel_id = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    meeting_docs_parent_folder = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    guests = relationship('MeetingGuests', backref='meeting')

    def __init__(self):
        self.guid = str(uuid.uuid1())
        pass

    def add_guests(self, guest_ids):
        for guest_id in guest_ids:
            meeting_guest = MeetingGuests()
            meeting_guest.meeting_id = self.id
            meeting_guest.user_id = guest_id
            db_session.add(meeting_guest)

        db_session.commit()

    def find_meeting_instance(self):
        meeting_instances = db_session.query(MeetingInstance).filter(MeetingInstance.meeting_id == self.id).filter(
            MeetingInstance.end_time == None)
        if meeting_instances.count() > 0:
            return meeting_instances[0]
        else:
            logger.warning("Unable to find Active Meeting Instance for Meeting " + str(self.slack_channel_name))
            return None
        return None


class MeetingGuests(Base):
    __tablename__ = "meeting_guests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey('meeting.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    inclusion_date = Column(DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    exclusion_date = Column(DateTime(timezone=True))
    is_optional = Column(Boolean, default=False)
    user = relationship("User", backref='meeting_guests')


class MeetingInstance(Base):
    __tablename__ = "meeting_instance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey('meeting.id'))
    title = Column(String(1024, convert_unicode=True), nullable=False)
    start_time = Column(DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    end_time = Column(DateTime(timezone=True))
    slack_channel_id = Column(String(255, convert_unicode=True), unique=True, nullable=False)
    meeting_docs_folder = Column(String(1024, convert_unicode=True), nullable=False)
    meeting_docs_updated = Column(Boolean, default=False)
    meeting = relationship("Meeting", backref='meeting_instance')

    def add_meeting_attendees(self, guests):
        for guest in guests:
            meeting_attendee = MeetingAttendees()
            meeting_attendee.meeting_instance_id = self.id
            meeting_attendee.user_id = guest.id
            db_session.add(meeting_attendee)
        db_session.commit()


class MeetingAttendees(Base):
    __tablename__ = "meeting_attendees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_instance_id = Column(Integer, ForeignKey('meeting_instance.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    user_presence = Column(String(1024, convert_unicode=True))


class MeetingMessages(Base):
    __tablename__ = "meeting_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_instance_id = Column(Integer, ForeignKey('meeting_instance.id'))
    slack_user_id = Column(String(255, convert_unicode=True), nullable=False)
    slack_team_id = Column(String(255, convert_unicode=True))
    message_time = Column(Integer, nullable=False)
    thread_message_time = Column(Integer)
    slack_parent_user_id = Column(String(255, convert_unicode=True))
    message = Column(String(4096, convert_unicode=True), nullable=False)


def get_configurations():
    configurations = db_session.query(Configuration)
    if configurations.count() > 0:
        return configurations;
    return None


def get_configuration(config_key):
    configurations = db_session.query(Configuration).filter(Configuration.config_key == config_key)
    if configurations.count() > 0:
        return configurations[0].value;
    return None


def create_user(email, first_name, last_name, slack_user_name, slack_user_id):
    user = User()
    user.email = email;
    user.first_name = first_name;
    user.last_name = last_name;
    user.slack_user_name = slack_user_name;
    user.slack_user_id = slack_user_id;
    db_session.add(user)
    db_session.commit()
    return user


def find_user_by_email(email):
    users = db_session.query(User).filter(User.email == email)
    if users.count() > 0:
        return users[0]
    else:
        logger.warning("Unable to find user by email: " + str(email))
        return None
    return None

def get_user_map():
    users = db_session.query(User)
    users_map = {}
    if users.count() > 0:
        for user in users:
            if user.last_name:
                users_map[user.slack_user_id] = user.first_name+" "+str(user.last_name)
            else:
                users_map[user.slack_user_id] = user.first_name
    else:
        logger.warning("No Users Available!")
    return users_map


def find_meetings_to_schedule():
    meetings = db_session.query(Meeting).filter(Meeting.is_active == True)
    current_date_time = datetime.datetime.now()
    meetings_to_schedule = []
    for meeting in meetings:
        if find_active_meeting_instance(meeting):
            logger.info(meeting.slack_channel_name + " meeting is already running.")
            continue
        if can_schedule_meeting(meeting, current_date_time):
            logger.info(meeting.slack_channel_name + " added is it is in schedule")
            meetings_to_schedule.append(meeting)
            create_meeting_instance(meeting)
        else:
            logger.info(meeting.slack_channel_name + " is not added is it is not in schedule")

    if len(meetings_to_schedule) > 0:
        return meetings_to_schedule
    else:
        logger.warning("No Active Meetings available to Schedule: ")
        return None
    return meetings_to_schedule


def find_meetings_to_end():
    meetings = db_session.query(Meeting).filter(Meeting.is_active == True)
    current_date_time = datetime.datetime.now()
    meetings_to_end = []
    for meeting in meetings:
        meeting_instance = find_active_meeting_instance(meeting)
        if meeting_instance:
            if can_end_meeting(meeting, current_date_time):
                logger.info(meeting.slack_channel_name + " added is the meeting is in end schedule")
                meetings_to_end.append(meeting)
                end_meeting_instance(meeting_instance)
            else:
                logger.info(meeting.slack_channel_name + " is not added as the meeting is not in end schedule")
        else:
            logger.info(meeting.slack_channel_name + " is not added as the meeting is not running")

    if len(meetings_to_end) > 0:
        return meetings_to_end
    else:
        logger.warning("No Active Meetings available to End")
        return None
    return meetings_to_end


def can_end_meeting(meeting, current_date_time):
    end = True
    if meeting.meeting_recurrence == 'Monthly':
        end = (meeting.start_date.day == current_date_time.day)
    elif meeting.meeting_recurrence == 'Weekly':
        end = (meeting.start_date.weekday() == current_date_time.weekday())

    if end:
        meeting_end_time = meeting.start_date + datetime.timedelta(minutes=(meeting.duration + extension_threshold_time))
        closing_time = meeting_end_time + datetime.timedelta(minutes=extension_threshold_time)
        meeting_end_time = datetime.time(meeting_end_time.hour, meeting_end_time.minute)
        closing_time = datetime.time(closing_time.hour, closing_time.minute)
        current_time = datetime.time(current_date_time.hour, current_date_time.minute)
        end = time_in_range(meeting_end_time, closing_time, current_time)

    return end


def can_schedule_meeting(meeting, current_date_time):
    schedule = True
    if meeting.meeting_recurrence == 'Monthly':
        schedule = (meeting.start_date.day == current_date_time.day)
    elif meeting.meeting_recurrence == 'Weekly':
        schedule = (meeting.start_date.weekday() == current_date_time.weekday())

    if schedule:
        meeting_start_time = datetime.time(meeting.start_date.hour, meeting.start_date.minute)
        invite_time = meeting.start_date - datetime.timedelta(minutes=extension_threshold_time)
        invite_time = datetime.time(invite_time.hour, invite_time.minute)
        current_time = datetime.time(current_date_time.hour, current_date_time.minute)
        schedule = time_in_range(invite_time, meeting_start_time, current_time)

    return schedule


def find_active_meeting_instance(meeting):
    meeting_instances = db_session.query(MeetingInstance).filter(MeetingInstance.meeting_id == meeting.id).filter(
        MeetingInstance.end_time == None)
    if meeting_instances.count() > 0:
        return meeting_instances[0]
    else:
        return None

def find_meeting_instance_for_docs_update():
    meeting_instances = db_session.query(MeetingInstance).filter(MeetingInstance.meeting_docs_updated == False).filter(
        MeetingInstance.end_time.isnot(None))
    if meeting_instances.count() > 0:
        return meeting_instances
    else:
        return None


def find_meeting_by_channel_name(slack_channel_name):
    meetings = db_session.query(Meeting).filter(Meeting.slack_channel_name == slack_channel_name)
    if meetings.count() > 0:
        return meetings[0]
    else:
        logger.warning("Unable to find Meeting by short name: " + str(slack_channel_name))
        return None
    return None


def create_meeting(meeting_data):
    meeting = Meeting();
    meeting.title = meeting_data.get('title')
    meeting.description = meeting_data.get('description')
    meeting.slack_channel_name = meeting_data.get('slack_channel_name')
    meeting.start_date = meeting_data.get('start_date')
    meeting.end_date = meeting_data.get('end_date')
    meeting.meeting_recurrence = meeting_data.get('meeting_recurrence')
    meeting.slack_channel_id = ''
    meeting.meeting_docs_parent_folder = meeting_data.get('meeting_docs_parent_folder')
    db_session.add(meeting)
    db_session.commit()
    meeting.add_guests(meeting_data.get('meeting_guests'))
    return meeting


def create_meeting_instance(meeting):
    meeting_instances = db_session.query(MeetingInstance).filter(MeetingInstance.meeting_id == meeting.id).filter(
        MeetingInstance.end_time == None)
    if meeting_instances.count() > 0:
        return meeting_instances[0]
    else:
        meeting_instance = MeetingInstance();
        meeting_instance.title = meeting.title
        meeting_instance.slack_channel_id = meeting.slack_channel_id
        meeting_instance.meeting_id = meeting.id
        meeting_instance.meeting_docs_folder = meeting.meeting_docs_parent_folder + date_format(datetime.datetime.now())
        db_session.add(meeting_instance)
        db_session.commit()
        meeting_instance.add_meeting_attendees(meeting.guests)
        return meeting_instance


def end_meeting_instance(meeting_instance):
    meeting_instance.end_time = datetime.datetime.now()
    db_session.merge(meeting_instance)
    db_session.commit()
    return meeting_instance

def update_meeting_instance_docs(meeting_instance):
    meeting_instance.meeting_docs_updated = True
    db_session.merge(meeting_instance)
    db_session.commit()
    return meeting_instance


def update_meeting(meeting, channel_id):
    meeting.slack_channel_id = channel_id
    db_session.merge(meeting)
    db_session.commit()
    return meeting


def time_in_range(start, end, time):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= time <= end
    else:
        return start <= time or time <= end


def maybe_connect_db():
    for x in range(config.config.DB_RECONNECT_ATTEMPTS):
        logger.info("Attempt %d of %d connecting to DB" % (x + 1, config.config.DB_RECONNECT_ATTEMPTS))
        try:
            Base.metadata.create_all(engine)
            logger.info("Connection succeeded")
            return
        except OperationalError as e:
            logger.exception("Error connecting to DB. Sleeping and retrying")
            time.sleep(config.config.DB_RECONNECT_ATTEMPTS_DELAY_SEC)
    # All attempts exhausted
    logger.exception("Connection attempts exhausted", e)
    raise e


maybe_connect_db()
