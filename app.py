import os
import re
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# ==================== Models ====================

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='editor')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tool(db.Model):
    __tablename__ = 'tools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default='🔧')
    description = db.Column(db.Text, default='')
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.String(200), default='')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, default='')
    excerpt = db.Column(db.Text, default='')
    cover = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='published')
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, default='')

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# ==================== Context Processor ====================

@app.context_processor
def inject_globals():
    return {
        'site_name': Setting.query.filter_by(key='site_name').first().value if Setting.query.filter_by(key='site_name').first() else 'AI工具导航',
        'site_desc': Setting.query.filter_by(key='site_desc').first().value if Setting.query.filter_by(key='site_desc').first() else '2026最全AI工具合集'
    }

# ==================== Frontend Routes ====================

@app.route('/')
def index():
    tools = Tool.query.filter_by(is_active=1).order_by(Tool.sort_order.desc()).all()
    posts = Post.query.filter_by(status='published').order_by(Post.created_at.desc()).limit(10).all()
    categories = {}
    for t in tools:
        cat = t.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    return render_template('frontend/index.html',
                         tools=tools,
                         posts=posts,
                         categories=categories,
                         all_tags=sorted(set(t.tag for t in tools for tag in t.tags.split(','))))

# ==================== Admin Auth Routes ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('用户名或密码错误', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ==================== Admin Dashboard ====================

@app.route('/admin')
@login_required
def admin_dashboard():
    tool_count = Tool.query.count()
    post_count = Post.query.count()
    active_tools = Tool.query.filter_by(is_active=1).count()
    return render_template('admin/dashboard.html',
                         tool_count=tool_count,
                         post_count=post_count,
                         active_tools=active_tools)

# ==================== Admin Tools CRUD ====================

@app.route('/admin/tools')
@login_required
def admin_tools_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    query = Tool.query
    if search:
        query = query.filter(Tool.name.contains(search) | Tool.description.contains(search))
    if category:
        query = query.filter_by(category=category)
    tools = query.order_by(Tool.sort_order.desc()).paginate(page=page, per_page=20, error_out=False)
    categories = db.session.query(Tool.category).distinct().all()
    return render_template('admin/tools_list.html',
                         tools=tools,
                         categories=[c[0] for c in categories],
                         search=search,
                         current_category=category)

@app.route('/admin/tools/add', methods=['GET', 'POST'])
@login_required
def admin_tools_add():
    if request.method == 'POST':
        tool = Tool(
            name=request.form['name'],
            icon=request.form.get('icon', '🔧'),
            description=request.form.get('description', ''),
            url=request.form['url'],
            category=request.form['category'],
            tags=request.form.get('tags', ''),
            sort_order=request.form.get('sort_order', 0, type=int)
        )
        db.session.add(tool)
        db.session.commit()
        flash('工具添加成功', 'success')
        return redirect(url_for('admin_tools_list'))
    return render_template('admin/tools_form.html', tool=None)

@app.route('/admin/tools/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_tools_edit(id):
    tool = Tool.query.get_or_404(id)
    if request.method == 'POST':
        tool.name = request.form['name']
        tool.icon = request.form.get('icon', '🔧')
        tool.description = request.form.get('description', '')
        tool.url = request.form['url']
        tool.category = request.form['category']
        tool.tags = request.form.get('tags', '')
        tool.sort_order = request.form.get('sort_order', 0, type=int)
        db.session.commit()
        flash('工具更新成功', 'success')
        return redirect(url_for('admin_tools_list'))
    return render_template('admin/tools_form.html', tool=tool)

@app.route('/admin/tools/delete/<int:id>')
@login_required
def admin_tools_delete(id):
    tool = Tool.query.get_or_404(id)
    tool.is_active = 0
    db.session.commit()
    flash('工具已删除（软删除）', 'success')
    return redirect(url_for('admin_tools_list'))

# ==================== Batch operations ====================

@app.route('/admin/tools/batch', methods=['POST'])
@login_required
def admin_tools_batch():
    action = request.form.get('action')
    ids = request.form.getlist('ids')
    if not ids:
        flash('请选择工具', 'error')
        return redirect(url_for('admin_tools_list'))

    if action == 'delete':
        Tool.query.filter(Tool.id.in_(ids)).update({'is_active': 0}, synchronize_session=False)
    elif action == 'activate':
        Tool.query.filter(Tool.id.in_(ids)).update({'is_active': 1}, synchronize_session=False)
    db.session.commit()
    flash(f'批量操作完成: {len(ids)} 条', 'success')
    return redirect(url_for('admin_tools_list'))

# ==================== Admin Posts CRUD ====================

@app.route('/admin/posts')
@login_required
def admin_posts_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Post.query
    if status:
        query = query.filter_by(status=status)
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/posts_list.html', posts=posts, current_status=status)

@app.route('/admin/posts/add', methods=['GET', 'POST'])
@login_required
def admin_posts_add():
    if request.method == 'POST':
        import re
        title = request.form['title']
        slug = request.form.get('slug', '')
        if not slug:
            slug = re.sub(r'[^\w\u4e00-\u9fff-]', '-', title.lower())[:100]
            slug = re.sub(r'-+', '-', slug).strip('-')
        post = Post(
            title=title,
            slug=slug,
            content=request.form.get('content', ''),
            excerpt=request.form.get('excerpt', ''),
            cover=request.form.get('cover', ''),
            status=request.form.get('status', 'draft')
        )
        db.session.add(post)
        db.session.commit()
        flash('文章已创建', 'success')
        return redirect(url_for('admin_posts_list'))
    return render_template('admin/posts_form.html', post=None)

@app.route('/admin/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_posts_edit(id):
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form.get('content', '')
        post.excerpt = request.form.get('excerpt', '')
        post.cover = request.form.get('cover', '')
        post.status = request.form.get('status', 'draft')
        db.session.commit()
        flash('文章已更新', 'success')
        return redirect(url_for('admin_posts_list'))
    return render_template('admin/posts_form.html', post=post)

@app.route('/admin/posts/delete/<int:id>')
@login_required
def admin_posts_delete(id):
    Post.query.filter_by(id=id).delete()
    db.session.commit()
    flash('文章已删除', 'success')
    return redirect(url_for('admin_posts_list'))

# ==================== Article View ====================

@app.route('/post/<slug>')
def view_post(slug):
    post = Post.query.filter_by(slug=slug, status='published').first_or_404()
    post.view_count += 1
    db.session.commit()
    import markdown
    content_html = markdown.markdown(post.content, extensions=['fenced_code', 'codehilite'])
    return render_template('frontend/post.html', post=post, content_html=content_html)

# ==================== Init DB & Seed ====================

def init_db():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(username='admin', password=generate_password_hash('admin123'), role='admin')
        db.session.add(admin)
    if not Setting.query.filter_by(key='site_name').first():
        db.session.add(Setting(key='site_name', value='AI工具导航'))
        db.session.add(Setting(key='site_desc', value='2026最全AI工具合集'))
        db.session.add(Setting(key='beian', value=''))
    db.session.commit()

def seed_from_html():
    """Parse existing index.html toolsDB and import into database"""
    index_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if not os.path.exists(index_path):
        print("index.html not found, skipping seed")
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract toolsDB object
    match = re.search(r'const toolsDB\s*=\s*(\{.*?\});', content, re.DOTALL)
    if not match:
        print("Could not find toolsDB in index.html")
        return

    try:
        # Fix JS object to valid JSON
        js_obj = match.group(1)
        # Replace single quotes with double quotes
        js_obj = re.sub(r"'([^']*?)'", r'"\1"', js_obj)
        # Remove trailing commas
        js_obj = re.sub(r',\s*\}', '}', js_obj)
        js_obj = re.sub(r',\s*\]', ']', js_obj)
        tools_db = json.loads(js_obj)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        # Fall back to regex extraction
        tools_db = {}

    count = 0
    for category, tools in tools_db.items():
        cat_name = {'video': '🎬AI视频', 'writing': '✍️AI写作', 'design': '🎨AI设计', 'coding': '💻AI编程'}.get(category, category)
        for tool in tools:
            if isinstance(tool, dict) and 'name' in tool:
                existing = Tool.query.filter_by(name=tool['name']).first()
                if not existing:
                    t = Tool(
                        name=tool.get('name', ''),
                        icon=tool.get('icon', '🔧'),
                        description=tool.get('desc', tool.get('description', '')),
                        url=tool.get('link', tool.get('url', '#')),
                        category=cat_name,
                        tags=tool.get('tags', tool.get('tag', '')),
                        sort_order=tool.get('sort', tool.get('sort_order', 0)) or 0,
                        is_active=1
                    )
                    db.session.add(t)
                    count += 1

    db.session.commit()
    print(f"Imported {count} tools from index.html")

if __name__ == '__main__':
    with app.app_context():
        init_db()
        seed_from_html()
    app.run(host='0.0.0.0', port=5000, debug=True)
