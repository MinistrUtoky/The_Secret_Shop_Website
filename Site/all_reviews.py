import datetime
import sqlalchemy
from sqlalchemy import orm
from Site.db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Reviews(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'reviews'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    review = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    ball = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    review_date = sqlalchemy.Column(sqlalchemy.DateTime,
                                     default=datetime.datetime.now)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    user = orm.relation('User')