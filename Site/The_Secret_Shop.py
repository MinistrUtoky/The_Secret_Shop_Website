import datetime
from flask import Flask, render_template, redirect, request, abort, Blueprint, jsonify, make_response
from flask_wtf import FlaskForm
from flask_socketio import SocketIO
from flask_restful import abort, Api
from flask_login import LoginManager, logout_user, login_user, login_required, current_user
from flask_ngrok import run_with_ngrok
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from Site import db_session, all_users, all_lots, lots_res, all_reviews, all_messages

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


class ReviewForm(FlaskForm):
    review = TextAreaField('Review:', validators=[DataRequired()])
    ball = StringField("Title", validators=[DataRequired()])
    submit = SubmitField('Estimate')


class RegisterForm(FlaskForm):
    name = StringField('Nickname', validators=[DataRequired()])
    contacts = StringField('10 digits phone number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_again = PasswordField('Password again  ', validators=[DataRequired()])
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


class MessageForm(FlaskForm):
    msg = StringField('Message', validators=[DataRequired()])
    send = SubmitField('Send')


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


@app.before_request
def before_request():
    if current_user.is_authenticated:
        session = db_session.create_session()
        current_user.last_seen = datetime.datetime.utcnow()
        session.commit()


@app.route('/chat')
@login_required
def chat():
    return render_template('session.html', user=current_user)


@app.route('/chats')
@login_required
def active_chats():
    session = db_session.create_session()
    users = session.query(all_users.User)
    for user in users:
        x = 0
    return render_template('chat_list.html')


@app.route('/<user_id>/<second_user_id>', methods=['GET', 'POST'])
@login_required
def local_chat(user_id, second_user_id):
    if user_id == second_user_id:
        return redirect('../' + str(user_id))
    if current_user.id != int(second_user_id) and current_user.id != int(user_id):
        return redirect('../' + str(user_id))
    if int(second_user_id) < int(user_id):
        return redirect('../' + second_user_id + '/' + user_id)
    session = db_session.create_session()
    chat = session.query(all_messages.Messages).filter_by(first_user_id=user_id,
                                                          second_user_id=second_user_id)
    if current_user.id == int(second_user_id):
        user = session.query(all_users.User).filter_by(id=user_id).first()
    else:
        user = session.query(all_users.User).filter_by(id=second_user_id).first()
    form = MessageForm()
    if form.validate_on_submit():
        message = all_messages.Messages()
        message.msg = form.msg.data
        message.first_user_id = user_id
        message.second_user_id = second_user_id
        message.author = current_user.id
        user.messages.append(message)
        session.merge(user)
        session.commit()
        return redirect('../' + user_id + '/' + second_user_id)
    if current_user.id == int(second_user_id):
        return render_template('1vs1_session.html', user=user, second_user=current_user,
                               form=form, chat=chat)
    else:
        return render_template('1vs1_session.html', user=current_user, second_user=user,
                               form=form, chat=chat)


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
        try:
            int(form.contacts.data)
        except:
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Incorrect contact number")
        if len(form.contacts.data) != 10:
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="Number is too short or too long")
        session = db_session.create_session()
        if session.query(all_users.User).filter(all_users.User.name == form.name.data).first():
            return render_template('register.html', title='Registration',
                                   form=form,
                                   message="There is at least the one user that have such nickname as your")
        user = all_users.User(
            name=form.name.data,
            contacts=form.contacts.data
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


@app.route('/<user_id>')
@login_required
def profile(user_id):
    session = db_session.create_session()
    user = session.query(all_users.User).filter_by(id=user_id).first()
    users = session.query(all_users.User)
    dialogs = {}
    for u in users:
        for message in u.messages:
            if current_user.id == int(user_id):
                print(int(user_id))
                if message.second_user_id == int(user_id):
                    dialog_with = message.first_user_id
                    name = session.query(all_users.User).filter_by(id=message.first_user_id).first().name
                    dialogs[dialog_with] = name
                elif message.first_user_id == int(user_id):
                    dialog_with = message.second_user_id
                    name = session.query(all_users.User).filter_by(id=message.second_user_id).first().name
                    dialogs[dialog_with] = name
    if user:
        reviews = session.query(all_reviews.Reviews).filter_by(user_id=user_id)
        user_rating = 0
        for i in reviews:
            user_rating += i.rating
        if len(user.reviews) != 0:
            user_rating /= len(user.reviews)
        lots = session.query(all_lots.Lots).filter_by(user_id=user_id)
        return render_template('profile.html', user=user, lenght=str(len(user.reviews)), lots=lots, reviews=reviews,
                               user_rating_float=float(user_rating), user_rating_int=int(user_rating), dias=dialogs)


@app.route('/<user_id>/reviews', methods=['GET', 'POST'])
@login_required
def make_review(user_id):
    form = ReviewForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(all_users.User).filter_by(id=user_id).first()
        if current_user == user:
            return render_template('review_maker.html',
                                   message="You can't review yourself",
                                   form=form)
        for review in user.reviews:
            if current_user.name == review.author:
                return render_template('review_maker.html',
                                       message="You already reviewed this user",
                                       form=form)
        review = all_reviews.Reviews()
        review.review = form.review.data
        review.ball = form.ball.data
        review.author = current_user.name
        review.rating = request.form['rating']
        user.reviews.append(review)
        session.merge(user)
        session.commit()
        return redirect('../' + str(user_id))
    return render_template('review_maker.html', title='Reviewing', form=form)


@app.route('/reviews/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_review(id):
    form = ReviewForm()
    if request.method == "GET":
        session = db_session.create_session()
        reviews = session.query(all_reviews.Reviews).filter(all_reviews.Reviews.id == id,
                                                            all_reviews.Reviews.author == current_user.name).first()
        if reviews:
            form.review.data = reviews.review
            form.ball.data = reviews.ball
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        reviews = session.query(all_reviews.Reviews).filter(all_reviews.Reviews.id == id,
                                                            all_reviews.Reviews.author == current_user.name).first()
        if reviews:
            reviews.review = form.review.data
            reviews.ball = form.ball.data
            reviews.author = current_user.name
            reviews.rating = request.form['rating']
            session.commit()
            return redirect('../' + str(reviews.user_id))
        else:
            abort(404)
    return render_template('review_maker.html', title='Rereviewing', form=form)


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
