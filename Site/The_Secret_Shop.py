import datetime
from flask import Flask, render_template, redirect, request, abort, Blueprint, jsonify, make_response
from flask_wtf import FlaskForm
from flask_socketio import SocketIO
from flask_restful import abort, Api
from flask_login import LoginManager, logout_user, login_user, login_required, current_user
from flask_ngrok import run_with_ngrok
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from Site import db_session, all_users, all_lots, lots_res

app = Flask(__name__)
api = Api(app)
socketio = SocketIO(app)
run_with_ngrok(app)
api.add_resource(lots_res.LotsListResource, '/api/v2/lots')
api.add_resource(lots_res.LotsResource, '/api/v2/lots/<int:lots_id>')

app.config['SECRET_KEY'] = 'key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)
db_session.global_init("db/blogs.sqlite")
blueprint = Blueprint('lots_api', __name__, template_folder='templates')


def main():
    app.run()


class RegisterForm(FlaskForm):
    name = StringField('Nickname', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_again = PasswordField('Password again:', validators=[DataRequired()])
    submit = SubmitField('Create account')


class LoginForm(FlaskForm):
    username = StringField('Nickname', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Enter')


class LotsForm(FlaskForm):
    title = StringField('Name of the lot', validators=[DataRequired()])
    content = TextAreaField('Description')
    price = StringField('Price', validators=[DataRequired()])
    submit = SubmitField('Accept')


@blueprint.route('/api/lots')
def get_lots():
    session = db_session.create_session()
    lots = session.query(all_lots.Lots).all()
    return jsonify(
        {
            'lots':
                [item.to_dict(only=('title', 'content', 'price', 'user.name'))
                 for item in lots]
        }
    )


@blueprint.route('/api/lots/<int:lots_id>', methods=['GET'])
def get_one_lots(lots_id):
    session = db_session.create_session()
    lots = session.query(all_lots.Lots).get(lots_id)
    if not lots:
        return jsonify({'error': 'Not found'})
    return jsonify(
        {
            'lots': lots.to_dict(only=('title', 'content', 'user_id'))
        }
    )


@blueprint.route('/api/lots', methods=['POST'])
def create_lots():
    if not request.json:
        return jsonify({'error': 'Empty request'})
    elif not all(key in request.json for key in
                 ['title', 'content', 'user_id', 'price']):
        return jsonify({'error': 'Bad request'})
    session = db_session.create_session()
    lots = all_lots.Lots(
        title=request.json['title'],
        content=request.json['content'],
        user_id=request.json['user_id'],
        price=request.json['price']
    )
    session.add(lots)
    session.commit()
    return jsonify({'success': 'OK'})


@blueprint.route('/api/news/<int:lots_id>', methods=['DELETE'])
def delete_news(lots_id):
    session = db_session.create_session()
    lots = session.query(all_lots.Lots).get(lots_id)
    if not lots:
        return jsonify({'error': 'Not found'})
    session.delete(lots)
    session.commit()
    return jsonify({'success': 'OK'})


app.register_blueprint(blueprint)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(all_users.User).get(user_id)


@app.route('/')
def main():
    return redirect('/index')


@app.route('/index', methods=['GET', 'POST'])
def index():
    session = db_session.create_session()
    lots = session.query(all_lots.Lots)
    return render_template('/index.html', lots=lots)


@app.route('/chat')
@login_required
def chat():
    return render_template('session.html', user=current_user)


def messageReceived(methods=['GET', 'POST']):
    print('received')


@socketio.on('event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received event: ' + str(json))
    socketio.emit('response', json, callback=messageReceived)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Password mismatch")
        session = db_session.create_session()
        if session.query(all_users.User).filter(all_users.User.name == form.name.data).first():
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="There is at least the one user that have such nickname as your")
        user = all_users.User(
            name=form.name.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Registration', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(all_users.User).filter(all_users.User.name == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/index")
        return render_template('login.html',
                               message="Wrong password or nickname",
                               form=form)
    return render_template('login.html', title='Authorize', form=form)


@app.route('/lots', methods=['GET', 'POST'])
@login_required
def make_lots():
    form = LotsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        lot = all_lots.Lots()
        lot.title = form.title.data
        lot.content = form.content.data
        lot.price = form.price.data
        current_user.lots.append(lot)
        session.merge(current_user)
        session.commit()
        return redirect('/')
    return render_template('lot_maker.html', title='Lot add',
                           form=form)


@app.route('/lots/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_lots(id):
    form = LotsForm()
    if request.method == "GET":
        session = db_session.create_session()
        lots = session.query(all_lots.Lots).filter(all_lots.Lots.id == id,
                                                   all_lots.Lots.user == current_user).first()
        if lots:
            form.title.data = lots.title
            form.content.data = lots.content
            form.price.data = lots.price
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        lots = session.query(all_lots.Lots).filter(all_lots.Lots.id == id,
                                                   all_lots.Lots.user == current_user).first()
        if lots:
            lots.title = form.title.data
            lots.content = form.content.data
            lots.price = form.price.data
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('lot_maker.html', title='Lot remake', form=form)


@app.route('/del_lots/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    session = db_session.create_session()
    lots = session.query(all_lots.Lots).filter(all_lots.Lots.id == id,
                                               all_lots.Lots.user == current_user).first()
    if lots:
        session.delete(lots)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run()
