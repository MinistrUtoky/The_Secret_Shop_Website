from flask_restful import reqparse, abort, Resource
from flask import jsonify
from Site import db_session, all_lots


def abort_if_lots_not_found(lots_id):
    session = db_session.create_session()
    lots = session.query(all_lots.Lots).get(lots_id)
    if not lots:
        abort(404, message=f"Lot {lots_id} not found")


class LotsResource(Resource):
    def get(self, lots_id):
        abort_if_lots_not_found(lots_id)
        session = db_session.create_session()
        lots = session.query(all_lots.Lots).get(lots_id)
        return jsonify({'lots': lots.to_dict(
            only=('title', 'content', 'user_id', 'price'))})

    def delete(self, lots_id):
        abort_if_lots_not_found(lots_id)
        session = db_session.create_session()
        lots = session.query(all_lots.Lots).get(lots_id)
        session.delete(lots)
        session.commit()
        return jsonify({'success': 'OK'})


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('content', required=True)
parser.add_argument('user_id', required=True, type=int)
parser.add_argument('price', required=True)


class LotsListResource(Resource):
    def get(self):
        session = db_session.create_session()
        lots = session.query(all_lots.Lots).all()
        return jsonify({'lots': [item.to_dict(
            only=('title', 'content', 'user.name')) for item in lots]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        lots = all_lots.Lots(
            title=args['title'],
            content=args['content'],
            user_id=args['user_id'],
            price=args['price']
        )
        session.add(lots)
        session.commit()
        return jsonify({'success': 'OK'})
