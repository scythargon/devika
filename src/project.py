from typing_extensions import Unpack

from typing import Type, TypeVar
from typing import Literal

import os
import json
import zipfile
from datetime import datetime
from typing import Optional
from src.socket_instance import emit_agent
from sqlmodel import Field, Session, SQLModel, create_engine
from src.config import Config


class Projects(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project: str
    message_stack_json: str


from enum import Enum
from typing import Literal
from dataclasses import dataclass


class MessageSources(Enum):
    DEVIKA = "Devika"  # Capital letter is because of fucking frontend, will refactor later
    USER = "user"
    SYSTEM = "system"


# Using Literal with unpacked enum values
T_MessageSources = Literal[MessageSources.DEVIKA, MessageSources.USER, MessageSources.SYSTEM]


@dataclass
class Message:
    source: T_MessageSources
    message: str
    timestamp: str

    def to_dict(self):
        return {
            "source": self.source.value,
            "from_devika": self.source == MessageSources.DEVIKA,
            "message": self.message,
            "timestamp": self.timestamp
        }


class ProjectManager:
    def __init__(self):
        config = Config()
        sqlite_path = config.get_sqlite_db()
        self.projects_root_dir = config.get_projects_dir()
        self.engine = create_engine(f"sqlite:///{sqlite_path}")
        SQLModel.metadata.create_all(self.engine)

    def new_message(self, source: T_MessageSources, message: str) -> Message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return Message(
            source=source,
            timestamp=timestamp,
            message=message,
        )

        # return {
        #     # "from_devika": True,
        #     "source":
        #     "message": None,
        #     "timestamp": timestamp
        # }

    def create_project(self, project: str):
        with Session(self.engine) as session:
            project_state = Projects(project=project, message_stack_json=json.dumps([]))
            session.add(project_state)
            session.commit()

    def delete_project(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                session.delete(project_state)
                session.commit()

    def delete_all_projects(self):
        with Session(self.engine) as session:
            session.query(Projects).delete()
            session.commit()

    def add_message_to_project(self, project: str, message: Message):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                message_stack.append(message.to_dict())
                project_state.message_stack_json = json.dumps(message_stack)
                session.commit()
            else:
                message_stack = [message.to_dict()]
                project_state = Projects(project=project, message_stack_json=json.dumps(message_stack))
                session.add(project_state)
                session.commit()

    def add_message_from_devika(self, project: str, message: str):
        new_message = self.new_message(MessageSources.DEVIKA, message)
        emit_agent("server-message", {"messages": new_message.to_dict()})
        self.add_message_to_project(project, new_message)

    def add_message_from_user(self, project: str, message: str):
        new_message = self.new_message(MessageSources.USER, message)
        emit_agent("server-message", {"messages": new_message.to_dict()})
        self.add_message_to_project(project, new_message)

    def add_system_message(self, project: str, message: str):
        new_message = self.new_message(MessageSources.SYSTEM, message)
        emit_agent("server-message", {"messages": new_message.to_dict()})
        self.add_message_to_project(project, new_message)

    def get_messages(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                return json.loads(project_state.message_stack_json)
            return None

    def get_latest_message_from_user(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in reversed(message_stack):
                    if not message["from_devika"]:
                        return message
            return None

    def validate_last_message_is_from_user(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                if message_stack:
                    return not message_stack[-1]["from_devika"]
            return False

    def get_latest_message_from_devika(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in reversed(message_stack):
                    if message["from_devika"]:
                        return message
            return None

    def get_project_list(self):
        with Session(self.engine) as session:
            projects = session.query(Projects).all()
            return [project.project for project in projects]

    def get_all_messages_formatted(self, project: str):
        formatted_messages = []

        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in message_stack:
                    formatted_messages.append(f"{message['source']}: {message['message']}")

            return formatted_messages

    def get_project_path(self, project: str):
        return os.path.join(self.projects_root_dir, project.lower().replace(" ", "-"))

    def project_to_zip(self, project: str):
        project_path = self.get_project_path(project)
        zip_path = f"{project_path}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), os.path.join(project_path, '..'))
                    zipf.write(os.path.join(root, file), arcname=relative_path)

        return zip_path

    def get_zip_path(self, project: str):
        return f"{self.get_project_path(project)}.zip"
