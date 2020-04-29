import datetime
import sqlalchemy
from sqlalchemy import orm
from Site.db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Messages(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'messages'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    msg = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    first_user_id = sqlalchemy.Column(sqlalchemy.Integer)
    second_user_id = sqlalchemy.Column(sqlalchemy.Integer)
    author = sqlalchemy.Column(sqlalchemy.Integer)
    date = sqlalchemy.Column(sqlalchemy.DateTime,
                                        default=datetime.datetime.now)
    user = orm.relation('User')
