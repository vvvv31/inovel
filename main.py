# main.py
from flask import Flask, render_template, request, redirect, session, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'iNovel_2025_flask_login_demo'

# ==================== 数据操作函数 ====================

def load_novels():
    with open('data/novels.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_users():
    with open('data/users.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open('data/users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_comments():
    with open('data/comments.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_comments(comments):
    with open('data/comments.json', 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

def get_novel_by_id(novel_id):
    novels = load_novels()
    return next((n for n in novels if n['id'] == novel_id), None)

# ==================== 路由定义 ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        users = load_users()
        if any(u['username'] == username for u in users):
            return render_template('register.html', error="用户名已存在！")

        new_id = max([u['id'] for u in users]) + 1 if users else 1
        users.append({
            'id': new_id,
            'username': username,
            'password': password,
            'favorites': [],
            'recent_read': []
        })
        save_users(users)
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        users = load_users()
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)

        if user:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']
            return redirect('/')
        else:
            error = "用户名或密码错误！"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/')
def index():
    novels = load_novels()
    query = request.args.get('q', '').strip()

    filtered_novels = novels
    if query:
        filtered_novels = [n for n in novels if query in n['title'] or query in n['author']]

    # 轮播图：取人气最高的3本
    carousel_books = sorted(filtered_novels, key=lambda x: x.get('views', 0), reverse=True)[:3]

    featured = sorted(filtered_novels, key=lambda x: x.get('votes', 0), reverse=True)[:6]
    new_books = sorted(filtered_novels, key=lambda x: x['id'], reverse=True)[:6]
    finished = [n for n in filtered_novels if n.get('status') == '完本'][:6]

    return render_template('index.html',
                           novels=filtered_novels,
                           carousel_books=carousel_books,
                           featured=featured,
                           new_books=new_books,
                           finished=finished,
                           query=query)

@app.route('/category')
def category():
    genres = ["玄幻", "仙侠", "武侠", "都市", "历史", "游戏", "科幻", "轻小说", "诸天无限"]
    return render_template('category.html', genres=genres)

@app.route('/category/<genre>')
def category_detail(genre):
    novels = load_novels()
    filtered = [n for n in novels if n['genre'] == genre]

    status = request.args.get('status', '全部')
    if status != '全部':
        filtered = [n for n in filtered if n.get('status') == status]

    sort_by = request.args.get('sort', '人气')
    if sort_by == '人气':
        filtered = sorted(filtered, key=lambda x: x['views'], reverse=True)
    elif sort_by == '更新':
        filtered = sorted(filtered, key=lambda x: x['updateTime'], reverse=True)
    elif sort_by == '收藏':
        filtered = sorted(filtered, key=lambda x: x['favorites'], reverse=True)
    elif sort_by == '月票':
        filtered = sorted(filtered, key=lambda x: x.get('votes', 0), reverse=True)

    return render_template('category_detail.html',
                           genre=genre,
                           novels=filtered,
                           status=status,
                           sort_by=sort_by)

@app.route('/ranking')
def ranking():
    novels = load_novels()

    # 三大榜单
    vote_rank = sorted(novels, key=lambda x: x.get('votes', 0), reverse=True)[:50]   # 月票榜
    fav_rank = sorted(novels, key=lambda x: x['favorites'], reverse=True)[:50]       # 收藏榜
    view_rank = sorted(novels, key=lambda x: x['views'], reverse=True)[:50]         # 阅读榜
    new_rank = sorted(novels, key=lambda x: x['id'], reverse=True)[:50]             # 新书榜

    return render_template('ranking.html',
                           vote_rank=vote_rank,
                           fav_rank=fav_rank,
                           view_rank=view_rank,
                           new_rank=new_rank)

@app.route('/detail/<int:novel_id>')
def detail(novel_id):
    novel = get_novel_by_id(novel_id)
    if not novel:
        return "<h1>小说未找到</h1><a href='/'>返回首页</a>", 404

    #更新阅读量
    novel['views'] = novel.get('views', 0) + 1

    user_favorites = []
    if session.get('logged_in'):
        users = load_users()
        user = next((u for u in users if u['id'] == session['user_id']), None)
        if user:
            user_favorites = user['favorites']

    comments = load_comments()
    novel_comments = [c for c in comments if c['novel_id'] == novel_id and c.get('chapter_id') is None]

    # 按时间倒序
    novel_comments.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('detail.html', novel=novel, user_favorites=user_favorites, comments=novel_comments)

@app.route('/read/<int:novel_id>/<int:chapter_id>')
def read(novel_id, chapter_id):
    if not session.get('logged_in'):
        return redirect('/login')

    novel = get_novel_by_id(novel_id)
    if not novel:
        return "<h1>小说未找到</h1><a href='/'>返回首页</a>", 404
    chapter = next((c for c in novel['chapters'] if c['id'] == chapter_id), None)
    if not chapter:
        return f"<h1>章节未找到</h1><a href='/detail/{novel_id}'>返回目录</a>", 404

    users = load_users()
    user = next(u for u in users if u['id'] == session['user_id'])
    if 'recent_read' not in user:
        user['recent_read'] = []
    if novel_id not in user['recent_read']:
        user['recent_read'].insert(0, novel_id)
    save_users(users)

    comments = load_comments()
    chapter_comments = [c for c in comments if c['novel_id'] == novel_id and c.get('chapter_id') == chapter_id]
    chapter_comments.sort(key=lambda x: x['timestamp'], reverse=True)

    return render_template('read.html', novel=novel, chapter=chapter, chapter_comments=chapter_comments)

@app.route('/profile')
def profile():
    if not session.get('logged_in'):
        return redirect('/login')

    users = load_users()
    user = next(u for u in users if u['id'] == session['user_id'])

    username = user['username']
    favorite_novels = [get_novel_by_id(nid) for nid in user.get('favorites', []) if get_novel_by_id(nid)]
    recent_novels = [get_novel_by_id(nid) for nid in user.get('recent_read', []) if get_novel_by_id(nid)]

    comments = load_comments()
    novels_map = {n['id']: n['title'] for n in load_novels()}
    user_comments = []
    for c in comments:
        if c['username'] == username:
            user_comments.append({
                'novel_id': c['novel_id'],
                'novel_title': novels_map.get(c['novel_id'], '未知'),
                'chapter_id': c.get('chapter_id'),
                'content': c['content'],
                'timestamp': c['timestamp']
            })

    return render_template('profile.html',
                           username=username,
                           favorite_novels=favorite_novels,
                           recent_novels=recent_novels,
                           user_comments=user_comments)

@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    if not session.get('logged_in'):
        return redirect('/login')

    novel_id = int(request.form['novel_id'])
    user_id = session['user_id']

    users = load_users()
    user = next(u for u in users if u['id'] == user_id)

    if novel_id in user['favorites']:
        user['favorites'].remove(novel_id)
    else:
        user['favorites'].append(novel_id)

    save_users(users)
    return redirect(f'/detail/{novel_id}')

#评论
@app.route('/add_comment', methods=['POST'])
def add_comment():
    if not session.get('logged_in'):
        return redirect('/login')

    novel_id = int(request.form['novel_id'])
    chapter_id = request.form.get('chapter_id')
    chapter_id = int(chapter_id) if chapter_id else None
    content = request.form['content'].strip()

    if not content:
        return "评论内容不能为空", 400

    users = load_users()
    user = next(u for u in users if u['id'] == session['user_id'])
    username = user['username']

    comments = load_comments()
    new_id = max([c['id'] for c in comments]) + 1 if comments else 1

    comments.append({
        'id': new_id,
        'novel_id': novel_id,
        'chapter_id': chapter_id,
        'username': username,
        'content': content,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_comments(comments)

    if chapter_id:
        return redirect(f'/read/{novel_id}/{chapter_id}')
    else:
        return redirect(f'/detail/{novel_id}')

# ==================== 启动检查与默认数据 ====================

if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 创建 data 目录")

    if not os.path.exists('data/novels.json'):
        # 使用上面提供的完整 novels.json 内容写入
        pass  # 你已有文件，跳过
    else:
        print("📖 已加载现有 novels.json")

    if not os.path.exists('data/users.json'):
        with open('data/users.json', 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print("👥 已创建空 users.json")

    print("✅ 项目启动成功！")
    print("👉 打开浏览器访问：http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)