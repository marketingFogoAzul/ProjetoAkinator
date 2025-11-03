import os
from flask import Flask, render_template, request, jsonify, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from datetime import datetime, timedelta
from thefuzz import process
import pytz
from collections import defaultdict

# --- INICIALIZAÇÃO ---
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Nome da FUNÇÃO login() abaixo
login_manager.login_message = "Por favor, faça login para acessar esta página."

# --- CONVERSOR DE FUSO HORÁRIO ---
@app.template_filter('to_local_time')
def to_local_time(utc_datetime):
    if not utc_datetime:
        return ""
    local_tz = pytz.timezone('America/Sao_Paulo')
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)
    local_dt = utc_datetime.astimezone(local_tz)
    return local_dt.strftime('%d/%m/%Y %H:%M')

# --- MODELOS DO BANCO DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    level = db.Column(db.String(20), default='user', nullable=False)
    blocked_until = db.Column(db.DateTime, nullable=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def is_admin(self): return self.level in ['admin', 'total_admin']

class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('conversations', lazy=True, cascade="all, delete-orphan"))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation = db.relationship('Conversation', backref=db.backref('messages', lazy=True, cascade="all, delete-orphan"))

class TeachingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    question_content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    user = db.relationship('User', backref=db.backref('teaching_requests', cascade="all, delete-orphan"))

class SiteStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='active', nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_site_status():
    status = SiteStatus.query.first()
    if not status:
        status = SiteStatus(status='active')
        db.session.add(status)
        db.session.commit()
    return status.status

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/templates/login.html', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/templates/chat.html')
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user, remember=True)
            if 'promo_notice' in session:
                flash(session.pop('promo_notice'), 'success')
            return redirect('/templates/chat.html')
        flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/templates/register.html', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/templates/chat.html')
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first():
            flash('Este e-mail já está cadastrado.', 'warning')
            return redirect('/templates/register.html')
        
        # -------------------------------------------------------------------
        # AQUI ESTÁ A CORREÇÃO (linha 111 do seu original)
        # Trocado request.form.get('username') por request.form.get('nome')
        # -------------------------------------------------------------------
        new_user = User(username=request.form.get('nome'), email=request.form.get('email'))
        
        new_user.set_password(request.form.get('password'))
        if request.form.get('coupon') == 'maxhome':
            new_user.level = 'total_admin'
            flash('Cupom de Administrador Total validado! Bem-vindo!', 'success')
        elif request.form.get('coupon') == 'Qazxcvbnmlp7@':
             new_user.level = 'admin'
             flash('Cupom de Administrador validado! Bem-vindo!', 'success')
        db.session.add(new_user)
        db.session.commit()
        if new_user.level == 'user':
            flash('Conta criada com sucesso! Faça o login.', 'success')
        return redirect('/templates/login.html')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/templates/login.html')

# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
@app.route('/templates/chat.html')
@login_required
def chat():
    return render_template('chat.html')

def is_user_blocked():
    if current_user.is_authenticated and current_user.is_admin():
        return False
    return current_user.is_authenticated and current_user.blocked_until and current_user.blocked_until > datetime.utcnow()

# --- ROTAS DE ADMIN ---
@app.route('/templates/admin.html')
@login_required
def admin_panel():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect('/templates/chat.html')
    
    knowledge = KnowledgeBase.query.order_by(KnowledgeBase.id.desc()).all()
    users = User.query.order_by(User.username).all()
    pending_requests = TeachingRequest.query.filter_by(status='pending').all()
    closed_requests = TeachingRequest.query.filter(TeachingRequest.status != 'pending').all()
    site_status = get_site_status()
    conversations = db.session.query(Conversation).join(Message).group_by(Conversation.id).order_by(Conversation.last_update.desc()).all()
    
    return render_template('admin.html', knowledge=knowledge, users=users, 
                           pending_requests=pending_requests, closed_requests=closed_requests, 
                           site_status=site_status, conversations=conversations)

@app.route('/templates/assumir_ia.html')
@login_required
def assumir_ia():
    if not current_user.level == 'total_admin':
        return redirect('/templates/chat.html')
    return render_template('assumir_ia.html')

@app.route('/templates/admin/view_conversation/<int:conv_id>')
@login_required
def view_conversation(conv_id):
    if not current_user.is_admin():
        return redirect('/templates/chat.html')
    conv = Conversation.query.get_or_404(conv_id)
    if not current_user.level == 'total_admin' and conv.user_id != current_user.id:
        flash('Acesso negado a esta conversa.', 'danger')
        return redirect('/templates/admin.html')
    return render_template('view_conversation.html', conversation=conv)

# --- ROTAS DE API (INTERNAS) ---
@app.route('/api/chat', methods=['POST'])
@login_required
def handle_chat():
    site_status = get_site_status()
    if not current_user.is_admin() and site_status != 'active':
        message = "O chat está temporariamente desativado." if site_status == 'disabled' else "O site está em manutenção. Tente novamente mais tarde."
        return jsonify({'response': message, 'is_blocked': True, 'site_down': True}), 403

    if is_user_blocked():
        remaining = current_user.blocked_until - datetime.utcnow()
        return jsonify({'is_blocked': True, 'response': f"Seu acesso está bloqueado. Tente novamente em {str(remaining).split('.')[0]}."}), 429

    data = request.json
    message_text = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not message_text or not conversation_id: return jsonify({'error': 'Dados inválidos'}), 400
    
    conv = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first()
    if not conv: return jsonify({'error': 'Conversa não encontrada'}), 404
    
    conv.last_update = datetime.utcnow()
    db.session.add(Message(conversation_id=conversation_id, role='user', content=message_text))

    response_text = None
    is_blocked = False

    all_knowledge = KnowledgeBase.query.all()
    question_map = {}
    for k in all_knowledge:
        triggers = [q.strip().lower() for q in k.questions.split(';')]
        for trigger in triggers:
            if trigger: question_map[trigger] = k.answer
    
    if question_map:
        best_match = process.extractOne(message_text.lower(), question_map.keys())
        if best_match and best_match[1] > 85:
            response_text = question_map[best_match[0]]

    if not response_text:
        if not current_user.is_admin():
            current_user.blocked_until = datetime.utcnow() + timedelta(hours=4)
            is_blocked = True
        response_text = "Desculpe, não encontrei uma resposta para isso. Se desejar, pode sugerir que eu aprenda sobre este tópico."
    
    db.session.add(Message(conversation_id=conversation_id, role='assistant', content=response_text))
    db.session.commit()

    return jsonify({'response': response_text, 'is_blocked': is_blocked, 'original_question': message_text})

@app.route('/api/new_conversation', methods=['POST'])
@login_required
def new_conversation():
    site_status = get_site_status()
    if not current_user.is_admin() and site_status != 'active':
        return jsonify({'error': "Não é possível iniciar um novo chat. O site está em manutenção ou desativado."}), 403

    if is_user_blocked(): return jsonify({'error': 'Usuário bloqueado'}), 429
        
    new_conv = Conversation(user_id=current_user.id)
    db.session.add(new_conv)
    db.session.commit()
    return jsonify({'conversation_id': new_conv.id})

@app.route('/api/request_teaching', methods=['POST'])
@login_required
def request_teaching():
    data = request.json
    question_content = data.get('question')
    if not question_content: return jsonify({'error': 'Conteúdo da pergunta ausente'}), 400
    
    new_request = TeachingRequest(user_id=current_user.id, question_content=question_content)
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'success': 'Sugestão enviada ao administrador!'})

@app.route('/api/get_conversations')
@login_required
def get_conversations():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.last_update.desc()).all()
    history = []
    for conv in conversations:
        first_message = Message.query.filter_by(conversation_id=conv.id, role='user').order_by(Message.timestamp.asc()).first()
        if first_message:
            title = first_message.content
            history.append({'id': conv.id, 'title': title[:30] + '...' if len(title) > 30 else title})
    return jsonify(history)
    
@app.route('/api/get_messages/<int:conv_id>')
@login_required
def get_messages(conv_id):
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()
    messages = [{'role': msg.role, 'content': msg.content} for msg in conv.messages]
    return jsonify(messages)

@app.route('/api/get_all_conversations')
@login_required
def get_all_conversations():
    if not current_user.level == 'total_admin': 
        return jsonify({"error": "Acesso negado"}), 403
    
    users_with_convs = User.query.join(User.conversations).distinct().order_by(User.email).all()
    
    grouped_conversations = defaultdict(lambda: {"username": "", "conversations": []})
    for user in users_with_convs:
        grouped_conversations[user.email]["username"] = user.username
        
        convs = Conversation.query.filter_by(user_id=user.id).order_by(Conversation.last_update.desc()).all()
        for conv in convs:
            first_message = Message.query.filter_by(conversation_id=conv.id, role='user').order_by(Message.timestamp.asc()).first()
            if first_message:
                title = first_message.content
                grouped_conversations[user.email]["conversations"].append({
                    'id': conv.id,
                    'title': title[:40] + '...' if len(title) > 40 else title
                })
            
    return jsonify(dict(grouped_conversations))

@app.route('/api/admin_get_messages/<int:conv_id>')
@login_required
def admin_get_messages(conv_id):
    if not current_user.level == 'total_admin': return jsonify({'error': 'Acesso negado'}), 403
    conv = Conversation.query.get_or_404(conv_id)
    messages = [{'role': msg.role, 'content': msg.content} for msg in conv.messages]
    return jsonify(messages)

@app.route('/api/admin_send_message', methods=['POST'])
@login_required
def admin_send_message():
    if not current_user.level == 'total_admin': return jsonify({'error': 'Acesso negado'}), 403
    data = request.json
    conversation_id = data.get('conversation_id')
    content = data.get('content')
    conv = Conversation.query.get(conversation_id)
    if conv and content:
        new_message = Message(conversation_id=conversation_id, role='assistant', content=content)
        conv.last_update = datetime.utcnow()
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Falha ao enviar mensagem'}), 400

# --- ROTAS DE AÇÕES DE ADMIN (INTERNAS) ---
@app.route('/admin/teach', methods=['POST'])
@login_required
def teach_bot():
    if not current_user.is_admin(): return redirect('/templates/chat.html')
    questions = request.form.get('questions')
    answer = request.form.get('answer')
    request_id = request.form.get('request_id')

    if questions and answer:
        new_triggers = {q.strip().lower() for q in questions.split(';') if q.strip()}
        
        all_knowledge = KnowledgeBase.query.all()
        existing_triggers = set()
        for item in all_knowledge:
            triggers = {q.strip().lower() for q in item.questions.split(';') if q.strip()}
            existing_triggers.update(triggers)

        duplicates = new_triggers.intersection(existing_triggers)
        
        if duplicates:
            flash(f"Erro: O(s) gatilho(s) '{', '.join(duplicates)}' já existe(m) na base de conhecimento.", 'danger')
            return redirect('/templates/admin.html')

        new_knowledge = KnowledgeBase(questions=questions, answer=answer)
        db.session.add(new_knowledge)
        if request_id:
            req = TeachingRequest.query.get(request_id)
            if req: req.status = 'accepted'
        db.session.commit()
        flash('Conhecimento adicionado!', 'success')
    return redirect('/templates/admin.html')

@app.route('/admin/handle_request/<int:request_id>/<action>', methods=['POST'])
@login_required
def handle_request(request_id, action):
    if not current_user.is_admin(): return redirect('/templates/chat.html')
    req = TeachingRequest.query.get(request_id)
    if req:
        if action == 'discard':
            req.status = 'discarded'
            flash('Solicitação descartada.', 'warning')
        elif action == 'revert' and current_user.level == 'total_admin':
             req.status = 'pending'
             flash('Solicitação reaberta.', 'success')
        db.session.commit()
    return redirect('/templates/admin.html')

@app.route('/admin/delete_teaching/<int:kid>', methods=['POST'])
@login_required
def delete_teaching(kid):
    if not current_user.level == 'total_admin': return redirect('/templates/chat.html')
    knowledge_to_delete = KnowledgeBase.query.get(kid)
    if knowledge_to_delete:
        db.session.delete(knowledge_to_delete)
        db.session.commit()
        flash('Ensinamento apagado.', 'success')
    return redirect('/templates/admin.html')

@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
@login_required
def delete_user(uid):
    if not current_user.level == 'total_admin': return redirect('/templates/chat.html')
    user_to_delete = User.query.get(uid)
    if user_to_delete and user_to_delete.level != 'total_admin':
        TeachingRequest.query.filter_by(user_id=uid).delete()
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'Usuário {user_to_delete.username} apagado.', 'success')
    return redirect('/templates/admin.html')

@app.route('/admin/toggle_admin/<int:uid>', methods=['POST'])
@login_required
def toggle_admin(uid):
    if not current_user.is_admin(): return redirect('/templates/chat.html')
    user_to_toggle = User.query.get(uid)
    if not user_to_toggle or user_to_toggle.level == 'total_admin':
        flash('Ação não permitida.', 'danger')
        return redirect('/templates/admin.html')

    if user_to_toggle.level == 'admin':
        if current_user.level == 'total_admin':
            user_to_toggle.level = 'user'
            flash(f'{user_to_toggle.username} não é mais admin.', 'warning')
        else:
            flash('Apenas o Administrador Total pode revogar o acesso de outros admins.', 'danger')
    elif user_to_toggle.level == 'user':
        user_to_toggle.level = 'admin'
        session['promo_notice'] = 'Você foi promovido a Administrador!'
        flash(f'{user_to_toggle.username} agora é um admin.', 'success')
    
    db.session.commit()
    return redirect('/templates/admin.html')

@app.route('/admin/delete_conversation/<int:cid>', methods=['POST'])
@login_required
def delete_conversation(cid):
    if not current_user.level == 'total_admin': return redirect('/templates/chat.html')
    conv_to_delete = Conversation.query.get(cid)
    if conv_to_delete:
        db.session.delete(conv_to_delete)
        db.session.commit()
        flash('Conversa apagada.', 'success')
    return redirect('/templates/admin.html')

@app.route('/admin/set_status/<new_status>', methods=['POST'])
@login_required
def set_status(new_status):
    if not current_user.level == 'total_admin': return redirect('/templates/chat.html')
    if new_status in ['active', 'disabled', 'maintenance']:
        status = SiteStatus.query.first()
        status.status = new_status
        db.session.commit()
        flash(f'Status do site alterado para: {new_status.capitalize()}', 'success')
    return redirect('/templates/admin.html')

# --- INICIALIZAÇÃO DO BANCO ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)