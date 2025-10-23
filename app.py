from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from datetime import datetime, timedelta
from thefuzz import process

# --- INICIALIZAÇÃO ---
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # O nome da função continua 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."

# --- MODELOS DO BANCO DE DADOS (Sem alterações) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    blocked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('conversations', lazy=True))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation = db.relationship('Conversation', backref=db.backref('messages', lazy=True, order_by="Message.timestamp"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROTAS DE AUTENTICAÇÃO (Corrigidas) ---
@app.route('/templates/login.html', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/templates/chat.html')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect('/templates/chat.html')
        flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/templates/register.html', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/templates/chat.html')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        coupon = request.form.get('coupon')

        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'warning')
            return redirect('/templates/register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        if coupon == 'Qazxcvbnmlp7@':
            new_user.is_admin = True
            flash('Cupom de administrador validado! Bem-vindo!', 'success')
        
        db.session.add(new_user)
        db.session.commit()
        
        if not new_user.is_admin:
            flash('Conta criada com sucesso! Faça o login.', 'success')
            
        return redirect('/templates/login.html')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/templates/login.html')

# --- ROTAS DA APLICAÇÃO (Corrigidas) ---
@app.route('/')
@app.route('/templates/chat.html')
@login_required
def chat():
    return render_template('chat.html')

def is_user_blocked():
    return current_user.is_authenticated and current_user.blocked_until and current_user.blocked_until > datetime.utcnow()

@app.route('/api/chat', methods=['POST'])
@login_required
def handle_chat():
    if is_user_blocked():
        remaining = current_user.blocked_until - datetime.utcnow()
        return jsonify({
            'is_blocked': True,
            'response': f"Seu acesso está bloqueado. Tente novamente em {str(remaining).split('.')[0]}."
        }), 429

    data = request.json
    message_text = data.get('message', '').strip().lower()
    conversation_id = data.get('conversation_id')

    if not message_text or not conversation_id:
        return jsonify({'error': 'Dados inválidos'}), 400
    
    conv = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({'error': 'Conversa não encontrada'}), 404

    db.session.add(Message(conversation_id=conversation_id, role='user', content=message_text))

    all_knowledge = KnowledgeBase.query.all()
    questions = {k.question: k.id for k in all_knowledge}
    
    found_knowledge = None
    if questions:
        best_match = process.extractOne(message_text, questions.keys())
        if best_match and best_match[1] > 80:
            knowledge_id = questions[best_match[0]]
            found_knowledge = KnowledgeBase.query.get(knowledge_id)

    if found_knowledge:
        response_text = found_knowledge.answer
    else:
        current_user.blocked_until = datetime.utcnow() + timedelta(hours=4)
        response_text = f"Não encontrei uma resposta para isso. Seu acesso foi bloqueado por 4 horas."
    
    db.session.add(Message(conversation_id=conversation_id, role='assistant', content=response_text))
    db.session.commit()

    return jsonify({'response': response_text, 'is_blocked': not found_knowledge})

@app.route('/api/new_conversation', methods=['POST'])
@login_required
def new_conversation():
    if is_user_blocked():
        return jsonify({'error': 'Usuário bloqueado'}), 429
        
    new_conv = Conversation(user_id=current_user.id)
    db.session.add(new_conv)
    db.session.commit()
    return jsonify({'conversation_id': new_conv.id})

@app.route('/api/get_conversations')
@login_required
def get_conversations():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.start_time.desc()).all()
    history = []
    for conv in conversations:
        first_message = Message.query.filter_by(conversation_id=conv.id, role='user').order_by(Message.timestamp.asc()).first()
        if first_message:
            title = first_message.content
            history.append({
                'id': conv.id,
                'title': title[:30] + '...' if len(title) > 30 else title
            })
    return jsonify(history)
    
@app.route('/api/get_messages/<int:conv_id>')
@login_required
def get_messages(conv_id):
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()
    messages = []
    for msg in conv.messages:
        messages.append({'role': msg.role, 'content': msg.content})
    return jsonify(messages)

# --- ROTAS DE ADMIN (Corrigidas) ---
@app.route('/templates/admin.html')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect('/templates/chat.html')
    
    knowledge = KnowledgeBase.query.order_by(KnowledgeBase.id.desc()).all()
    conversations = db.session.query(Conversation).join(Message).group_by(Conversation.id).order_by(Conversation.start_time.desc()).all()
    users = User.query.filter(User.id != current_user.id).all()
    learn_question = request.args.get('learn_question', '')
    
    return render_template('admin.html', knowledge=knowledge, conversations=conversations, users=users, learn_question=learn_question)

@app.route('/admin/teach', methods=['POST'])
@login_required
def teach_bot():
    if not current_user.is_admin:
        return redirect('/templates/chat.html')
    question = request.form.get('question')
    answer = request.form.get('answer')
    if question and answer:
        new_knowledge = KnowledgeBase(question=question, answer=answer)
        db.session.add(new_knowledge)
        db.session.commit()
        flash('Conhecimento adicionado!', 'success')
    return redirect('/templates/admin.html')

@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@login_required
def promote_user(user_id):
    if not current_user.is_admin:
        flash('Ação não permitida.', 'danger')
        return redirect('/templates/chat.html')
    
    user_to_promote = User.query.get(user_id)
    if user_to_promote:
        user_to_promote.is_admin = True
        db.session.commit()
        flash(f'{user_to_promote.username} agora é um administrador!', 'success')
    else:
        flash('Usuário não encontrado.', 'danger')
        
    return redirect('/templates/admin.html')

@app.route('/templates/admin/conversation/<int:conv_id>')
@login_required
def admin_view_conversation(conv_id):
    if not current_user.is_admin:
        return redirect('/templates/chat.html')
    conv = Conversation.query.get_or_404(conv_id)
    return render_template('view_conversation.html', conversation=conv)

# --- INICIALIZAÇÃO DO BANCO ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)