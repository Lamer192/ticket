from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neoline-tech-2026-secure'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tickets.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), default='user')

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Gözləmədə')
    file_path = db.Column(db.String(200), nullable=True)
    assigned_to = db.Column(db.String(50), default='Təyin edilməyib')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    users_list = User.query.all()
    if current_user.role == 'admin':
        tickets = Ticket.query.order_by(Ticket.date_created.desc()).all()
        stats = {'total': Ticket.query.count(), 'waiting': Ticket.query.filter_by(status='Gözləmədə').count(), 'process': Ticket.query.filter_by(status='İcrada').count(), 'closed': Ticket.query.filter_by(status='Tamamlandı').count()}
        return render_template('admin.html', tickets=tickets, stats=stats, users=users_list)
    else:
        query = Ticket.query.filter((Ticket.user_id == current_user.id) | (Ticket.assigned_to == current_user.username))
        tickets = query.order_by(Ticket.date_created.desc()).all()
        stats = {'total': query.count(), 'waiting': query.filter_by(status='Gözləmədə').count(), 'process': query.filter_by(status='İcrada').count(), 'closed': query.filter_by(status='Tamamlandı').count()}
        return render_template('user.html', tickets=tickets, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('İstifadəçi adı və ya şifrə yanlışdır!', 'danger')
    return render_template('login.html')

@app.route('/create_ticket', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        file = request.files.get('file')
        fname = secure_filename(file.filename) if file and file.filename != '' else None
        if fname: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        t = Ticket(title=request.form.get('title'), description=request.form.get('description'), file_path=fname, user_id=current_user.id)
        db.session.add(t)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create_ticket.html')

@app.route('/edit_ticket/<int:id>', methods=['POST'])
@login_required
def edit_ticket(id):
    t = Ticket.query.get(id)
    if t and (current_user.role == 'admin' or t.user_id == current_user.id):
        t.title = request.form.get('title')
        t.description = request.form.get('description')
        file = request.files.get('file')
        if file and file.filename != '':
            fname = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            t.file_path = fname
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_status/<int:id>', methods=['POST'])
@login_required
def update_status(id):
    t = Ticket.query.get(id)
    if t and (current_user.role == 'admin' or t.user_id == current_user.id or t.assigned_to == current_user.username):
        t.status = request.form.get('status')
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/assign_ticket/<int:id>', methods=['POST'])
@login_required
def assign_ticket(id):
    if current_user.role == 'admin':
        t = Ticket.query.get(id)
        if t:
            t.assigned_to = request.form.get('assign_to')
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/admin_update_user/<int:id>', methods=['POST'])
@login_required
def admin_update_user(id):
    if current_user.role == 'admin':
        user = User.query.get(id)
        if user:
            user.username, user.password, user.role = request.form.get('u'), request.form.get('p'), request.form.get('r')
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/admin_create_user', methods=['POST'])
@login_required
def admin_create_user():
    if current_user.role == 'admin':
        u, p, r = request.form.get('u'), request.form.get('p'), request.form.get('r')
        if u and p:
            db.session.add(User(username=u, password=p, role=r))
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='123', role='admin'))
            db.session.commit()
    app.run(debug=True)